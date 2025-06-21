from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional, Dict
from google.cloud import firestore

from schema import EnvironmentalDataRequest
from firebase_config import get_firestore_db

# Create router instance
router = APIRouter(
    tags=["sensors"],
    responses={404: {"description": "Not found"}},
)

# Get the Firestore DB client
db = get_firestore_db()

# --- Helper Functions ---
def convert_timestamps(data: dict) -> dict:
    """Convert Firestore timestamps to ISO strings"""
    for key, value in data.items():
        if hasattr(value, 'isoformat'):
            if hasattr(value, 'tzinfo') and value.tzinfo is not None:
                data[key] = value.isoformat()
            else:
                data[key] = value.isoformat() + 'Z'
    return data

# --- Environmental Data Endpoints ---
@router.get("/v1/logs/sensors", response_model=List[dict])
async def get_environmental_data(
    zoneId: Optional[str] = Query(None, description="Filter by specific zone ID"),
    latest: bool = Query(False, description="Get only the latest record"),
    limit: Optional[int] = Query(None, description="Maximum number of records to return (only applies when latest=false)"),
    startDate: Optional[datetime] = Query(None, description="Start date for filtering"),
    endDate: Optional[datetime] = Query(None, description="End date for filtering")
):
    """Get environmental data with filtering 
    
    Examples:
    - /v1/environmental-data?latest=true (latest for all zones)
    - /v1/environmental-data?zoneId=zone1&latest=true (latest for zone1)
    - /v1/environmental-data?zoneId=zone1&limit=100 (last 100 records for zone1)
    - /v1/environmental-data?startDate=2025-06-01T00:00:00Z (all zones since date)
    """
    try:
        if latest:
            # Get latest data per zone
            if zoneId:
                # Latest for specific zone
                query = db.collection("EnvironmentalData").where("zoneId", "==", zoneId).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
                docs = list(query.stream())
                return [convert_timestamps(doc.to_dict()) for doc in docs]
            else:
                # Latest for all zones
                # Get all unique zone IDs first
                zones_query = db.collection("ZoneInfo").stream()
                zone_ids = [doc.id for doc in zones_query]
                
                # Get latest document for each zone
                latest_data = []
                for zone_id in zone_ids:
                    query = db.collection("EnvironmentalData").where("zoneId", "==", zone_id).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
                    docs = list(query.stream())
                    if docs:
                        latest_data.append(convert_timestamps(docs[0].to_dict()))
                
                # Sort by timestamp descending
                latest_data.sort(key=lambda x: x["timestamp"], reverse=True)
                return latest_data

        else:
            query = db.collection("EnvironmentalData")
            
            if zoneId:
                query = query.where("zoneId", "==", zoneId)
            
            if startDate:
                query = query.where("timestamp", ">=", startDate)
            if endDate:
                query = query.where("timestamp", "<=", endDate)
            
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)
            
            # Apply limit, default to 100 if not specified
            if limit is not None:
                query = query.limit(limit)
            else:
                query = query.limit(100) 
            
            docs = query.stream()
            return [convert_timestamps(doc.to_dict()) for doc in docs]
        
    except Exception as e:
        print(f"Error fetching environmental data: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching environmental data: {e}")

@router.post("/v1/sensor-data", response_model=dict)
async def submit_environmental_data(environmentalRequest: EnvironmentalDataRequest):
    """Submit environmental sensor data"""
    try:
        # Create document ID
        envRecordId = f"env_{environmentalRequest.zoneId}_{environmentalRequest.timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Store the environmental data
        env_data = {
            "recordId": envRecordId,
            "zoneId": environmentalRequest.zoneId,
            "timestamp": environmentalRequest.timestamp,
            "zoneSensors": environmentalRequest.zoneSensors,
            "soilMoistureByPin": [pin_data.model_dump() for pin_data in environmentalRequest.soilMoistureByPin],
            "userId": environmentalRequest.userId
        }
        doc_ref = db.collection("EnvironmentalData").document(envRecordId)
        doc_ref.set(env_data)
        
        return {
            "message": f"Zone {environmentalRequest.zoneId} environmental data stored successfully",
            "recordId": envRecordId,
            "zoneId": environmentalRequest.zoneId,
            "timestamp": environmentalRequest.timestamp.isoformat() + 'Z'
        }
        
    except Exception as e:
        print(f"Error storing environmental data: {e}")
        raise HTTPException(status_code=500, detail=f"Error storing environmental data: {e}")
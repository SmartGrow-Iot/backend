from typing import List
from fastapi import APIRouter, HTTPException
from firebase_config import get_firestore_db
from datetime import datetime
from pydantic import BaseModel
from schema import VALID_MOISTURE_PINS, VALID_ZONES, PlantCreate, PlantListResponse, PlantOut, PlantStatus, PlantThresholds,PlantUpdate, ZoneCreate,ZoneInfoResponse
router = APIRouter()
db = get_firestore_db()  

@router.post("/v1/plants", response_model=PlantOut)
async def create_plant(plant: PlantCreate):
    """Create new plant with zone and pin validation"""
    try:
        # Check if pin is available in zone
        existing = db.collection("Plants") \
                    .where("zone", "==", plant.zone) \
                    .where("moisturePin", "==", plant.moisturePin) \
                    .limit(1).get()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Pin {plant.moisturePin} already in use in {plant.zone}"
            )

        plant_id = f"plant_{db.collection('Plants').document().id}"
        plant_data = plant.model_dump()
        
        # Set default sensor values
        defaults = {
            "plantId": plant_id,
            "status": PlantStatus.OPTIMAL,
            "waterLevel": 50.0,
            "lightLevel": 50.0,
            "temperature": 25.0,
            "humidity": 50.0,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        plant_data.update(defaults)
        
        db.collection("Plants").document(plant_id).set(plant_data)
        return plant_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating plant: {str(e)}"
        )
    
@router.get("/v1/plants/{plant_id}", response_model=PlantOut)
async def get_plant(plant_id: str):
    """Get complete plant data by ID"""
    try:
        doc = db.collection("Plants").document(plant_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Plant not found")
        return doc.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving plant: {str(e)}"
        )
    
@router.put("/v1/plants/{plant_id}/thresholds")
async def update_thresholds(plant_id: str, thresholds: PlantThresholds):
    """Update plant thresholds with validation"""
    try:
        doc_ref = db.collection("Plants").document(plant_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Plant not found")
            
        doc_ref.update({
            "thresholds": thresholds.model_dump(),
            "updatedAt": datetime.utcnow()
        })
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating thresholds: {str(e)}"
        )
    
@router.get("/v1/plants/user/{user_id}", response_model=PlantListResponse)
async def get_user_plants(user_id: str):
    """Get all plants for a user with zone info"""
    try:
        docs = db.collection("Plants").where("userId", "==", user_id).stream()
        plants = [doc.to_dict() for doc in docs]
        
        if not plants:
            raise HTTPException(
                status_code=404,
                detail=f"No plants found for user {user_id}"
            )
            
        return PlantListResponse(
            count=len(plants),
            plants=plants
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving plants: {str(e)}"
        )
    

@router.get("/v1/zones/{zone}/plants", response_model=PlantListResponse)
async def get_zone_plants(zone: str):
    """Get all plants in a specific zone"""
    try:
        if zone not in VALID_ZONES:
            raise HTTPException(status_code=400, detail="Invalid zone specified")
            
        docs = db.collection("Plants").where("zone", "==", zone).stream()
        plants = [doc.to_dict() for doc in docs]
        
        return PlantListResponse(
            count=len(plants),
            plants=plants
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving zone plants: {str(e)}"
        )

@router.get("/v1/users/{user_id}/zones", response_model=List[ZoneInfoResponse])
async def get_user_zones(user_id: str):
    """Get zone availability for a user"""
    try:
        zone_info = {}
        
        # Initialize all zones
        for zone in VALID_ZONES:
            zone_info[zone] = {
                "used_pins": [],
                "plant_count": 0
            }
        
        # Get user's plants
        plants = db.collection("Plants").where("userId", "==", user_id).stream()
        
        for plant in plants:
            data = plant.to_dict()
            zone = data["zone"]
            zone_info[zone]["used_pins"].append(data["moisturePin"])
            zone_info[zone]["plant_count"] += 1
        
        # Build response
        response = []
        for zone, info in zone_info.items():
            available_pins = [
                pin for pin in VALID_MOISTURE_PINS 
                if pin not in info["used_pins"]
            ]
            response.append(ZoneInfoResponse(
                zone=zone,
                plantCount=info["plant_count"],
                availablePins=available_pins
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user zones: {str(e)}"
        )

@router.post("/v1/zones")
async def initialize_zone(zone: ZoneCreate):
    """Initialize a new zone with default pins"""
    if db.collection("Zones").document(zone.zoneId).get().exists:
        raise HTTPException(400, "Zone already exists")
    
    zone_data = {
        "userId": zone.userId,
        "plantIds": [],
        "availablePins": [34, 35, 36, 39],
        "lastUpdated": datetime.utcnow()
    }
    
    db.collection("Zones").document(zone.zoneId).set(zone_data)
    return zone_data
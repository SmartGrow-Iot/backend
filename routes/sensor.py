from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional

from schema import (
    SensorCreateRequest, SensorResponse, 
    SensorLogCreateRequest, SensorLogResponse, SensorType,
    EnvironmentalDataRequest
)
from firebase_config import get_firestore_db

# Create router instance
router = APIRouter(
    tags=["sensors"],
    responses={404: {"description": "Not found"}},
)

# Get the Firestore DB client
db = get_firestore_db()

# --- Helper Functions ---
def generate_sensor_id() -> str:
    """Generate a unique sensor ID with 'sensor_' prefix using Firebase auto-generated ID"""
    firebase_id = db.collection("Sensor").document().id
    return f"sensor_{firebase_id}"

def generate_log_id() -> str:
    """Generate a unique log ID with 'sensorlog_' prefix using Firebase auto-generated ID"""
    firebase_id = db.collection("SensorLog").document().id
    return f"sensorlog_{firebase_id}"

def convert_timestamps(data: dict) -> dict:
    """Convert Firestore timestamps to ISO strings"""
    for key, value in data.items():
        if hasattr(value, 'isoformat'):
            if hasattr(value, 'tzinfo') and value.tzinfo is not None:
                data[key] = value.isoformat()
            else:
                data[key] = value.isoformat() + 'Z'
    return data

# --- Sensor Management Endpoints ---
@router.post("/v1/sensors", response_model=SensorResponse)
async def create_sensor(sensorRequest: SensorCreateRequest):
    """Create a new sensor"""
    try:
        # Generate sensor ID and timestamps
        sensorId = generate_sensor_id()
        now = datetime.utcnow()
        
        # Create complete sensor data
        sensor_data = sensorRequest.model_dump()
        sensor_data.update({
            "sensorId": sensorId,
            "createdAt": now,
            "lastUpdated": now
        })
        
        # Save to database
        doc_ref = db.collection("Sensor").document(sensorId)
        doc_ref.set(sensor_data)
        
        return SensorResponse(**sensor_data)
        
    except Exception as e:
        print(f"Error creating sensor: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating sensor: {e}")

@router.get("/v1/sensors", response_model=List[SensorResponse])
async def list_sensors(
    sensorType: Optional[SensorType] = Query(None),
    esp32Id: Optional[str] = Query(None),
    plantId: Optional[str] = Query(None)
):
    """Get all sensors with optional filtering"""
    try:
        query = db.collection("Sensor")
        
        # Apply filters
        if sensorType:
            query = query.where("type", "==", sensorType.value)
        if esp32Id:
            query = query.where("esp32Id", "==", esp32Id)
        if plantId:
            query = query.where("plantIds", "array_contains", plantId)
        
        docs = query.stream()
        sensors = []
        for doc in docs:
            sensor_data = doc.to_dict()
            sensor_data = convert_timestamps(sensor_data)
            sensors.append(SensorResponse(**sensor_data))
        
        return sensors
        
    except Exception as e:
        print(f"Error fetching sensors: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sensors: {e}")

@router.get("/v1/sensors/{sensorId}", response_model=SensorResponse)
async def get_sensor(sensorId: str):
    """Get a specific sensor by ID"""
    try:
        doc_ref = db.collection("Sensor").document(sensorId)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Sensor {sensorId} not found")
        
        sensor_data = doc.to_dict()
        sensor_data = convert_timestamps(sensor_data)
        return SensorResponse(**sensor_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching sensor {sensorId}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sensor: {e}")

@router.put("/v1/sensors/{sensorId}", response_model=SensorResponse)
async def update_sensor(sensorId: str, updateRequest: SensorCreateRequest):
    """Update sensor information"""
    try:
        doc_ref = db.collection("Sensor").document(sensorId)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Sensor {sensorId} not found")
        
        # Get current data
        current_data = doc.to_dict()
        
        # Update only provided fields
        update_data = updateRequest.model_dump(exclude_none=True)
        update_data["lastUpdated"] = datetime.utcnow()
        
        # Merge updates
        current_data.update(update_data)
        
        # Save updated data
        doc_ref.set(current_data)
        
        current_data = convert_timestamps(current_data)
        return SensorResponse(**current_data)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating sensor {sensorId}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating sensor: {e}")

@router.delete("/v1/sensors/{sensorId}")
async def delete_sensor(sensorId: str):
    """Delete a sensor"""
    try:
        doc_ref = db.collection("Sensor").document(sensorId)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Sensor {sensorId} not found")
        
        # Delete sensor
        doc_ref.delete()
        
        return {"message": f"Sensor {sensorId} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting sensor {sensorId}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting sensor: {e}")

# --- Sensor Log Endpoints ---
# --- Helper Function for Sensor Log Filtering ---
async def _get_filtered_sensor_logs(
    sensorId: Optional[str] = None,
    plantId: Optional[str] = None,
    zoneId: Optional[str] = None,
    sensorType: Optional[SensorType] = None,
    limit: int = 100,
    startDate: Optional[datetime] = None,
    endDate: Optional[datetime] = None
) -> List[SensorLogResponse]:
    """Internal helper function to get filtered sensor logs"""
    
    # Handle zone filtering first (get plant IDs)
    target_plant_ids = []
    if zoneId:
        plants_query = db.collection("Plants").where("zone", "==", zoneId)
        plants_docs = plants_query.stream()
        target_plant_ids = [plant_doc.to_dict().get("plantId") for plant_doc in plants_docs]
        
        if not target_plant_ids:
            return []
    elif plantId:
        target_plant_ids = [plantId]
    
    # Build query based on available filters
    if target_plant_ids:
        # Zone or plant filtering - need to query each plant separately due to Firestore limitations
        all_logs = []
        for plant_id in target_plant_ids:
            query = db.collection("SensorLog").where("plantId", "==", plant_id)
            
            # Add additional filters
            if sensorId:
                query = query.where("sensorId", "==", sensorId)
            if startDate:
                query = query.where("timestamp", ">=", startDate)
            if endDate:
                query = query.where("timestamp", "<=", endDate)
            
            # Get logs for this plant
            docs = query.stream()
            for doc in docs:
                log_data = doc.to_dict()
                log_data = convert_timestamps(log_data)
                all_logs.append(log_data)
        
        # Sort all logs by timestamp
        all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Apply limit after sorting
        all_logs = all_logs[:limit]
    else:
        # Direct sensor log query (no plant/zone filtering)
        query = db.collection("SensorLog")
        
        # Apply filters
        if sensorId:
            query = query.where("sensorId", "==", sensorId)
        if startDate:
            query = query.where("timestamp", ">=", startDate)
        if endDate:
            query = query.where("timestamp", "<=", endDate)
        
        # Order and limit
        query = query.order_by("timestamp", direction="DESCENDING").limit(limit)
        
        docs = query.stream()
        all_logs = []
        for doc in docs:
            log_data = doc.to_dict()
            log_data = convert_timestamps(log_data)
            all_logs.append(log_data)
    
    # Apply sensor type filtering (requires sensor lookup)
    filtered_logs = []
    for log_data in all_logs:
        if sensorType:
            sensor_doc = db.collection("Sensor").document(log_data["sensorId"]).get()
            if sensor_doc.exists:
                sensor_data = sensor_doc.to_dict()
                if sensor_data.get("type") != sensorType.value:
                    continue
            else:
                continue
        
        filtered_logs.append(SensorLogResponse(**log_data))
    
    return filtered_logs

@router.get("/v1/logs/sensors", response_model=List[SensorLogResponse])
async def get_sensor_logs(
    sensorId: Optional[str] = Query(None, description="Filter by specific sensor ID"),
    plantId: Optional[str] = Query(None, description="Filter by specific plant ID"),
    zoneId: Optional[str] = Query(None, description="Filter by specific zone ID"),
    sensorType: Optional[SensorType] = Query(None, description="Filter by sensor type"),
    limit: int = Query(100, le=1000, description="Maximum number of logs to return"),
    startDate: Optional[datetime] = Query(None, description="Start date for filtering (ISO format)"),
    endDate: Optional[datetime] = Query(None, description="End date for filtering (ISO format)")
):
    """Get sensor logs with comprehensive filtering options
    
    This unified endpoint supports filtering by:
    - sensorId: Get logs for a specific sensor
    - plantId: Get logs for all sensors of a specific plant
    - zoneId: Get logs for all sensors in a specific zone
    - sensorType: Filter by sensor type (temperature, humidity, etc.)
    - Date range: Filter by timestamp range
    - Limit: Control number of results returned
    
    Examples:
    - /v1/sensor-logs?plantId=plant_001&sensorType=temperature
    - /v1/sensor-logs?zoneId=zone_A&startDate=2025-06-01T00:00:00Z
    - /v1/sensor-logs?sensorId=sensor_123&limit=50
    """
    try:
        # Validate mutually exclusive filters
        filter_count = sum([bool(sensorId), bool(plantId), bool(zoneId)])
        if filter_count > 1:
            raise HTTPException(
                status_code=400, 
                detail="Cannot filter by multiple scope parameters (sensorId, plantId, zoneId) simultaneously"
            )
        
        return await _get_filtered_sensor_logs(
            sensorId=sensorId,
            plantId=plantId,
            zoneId=zoneId,
            sensorType=sensorType,
            limit=limit,
            startDate=startDate,
            endDate=endDate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_context = "all sensors"
        if sensorId:
            error_context = f"sensor {sensorId}"
        elif plantId:
            error_context = f"plant {plantId}"
        elif zoneId:
            error_context = f"zone {zoneId}"
            
        print(f"Error fetching sensor logs for {error_context}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sensor logs: {e}")

@router.post("/v1/sensor-data", response_model=dict)
async def submit_environmental_data(environmentalRequest: EnvironmentalDataRequest):
    """Submit environmental sensor data - requires pre-registered sensors"""
    try:
        # Get all sensors for this plant
        plant_sensors = db.collection("Sensor").where("plantIds", "array_contains", environmentalRequest.plantId).stream()
        
        sensor_map = {}
        for sensor_doc in plant_sensors:
            sensor_data = sensor_doc.to_dict()
            sensor_map[sensor_data["type"]] = sensor_data["sensorId"]
        
        created_logs = []
        missing_sensors = []
        skipped_readings = []
        
        # Map sensor readings to sensor types
        sensor_mappings = {
            "soilMoisture": (SensorType.SOIL_MOISTURE.value, environmentalRequest.sensors.soilMoisture),
            "light": (SensorType.LIGHT.value, environmentalRequest.sensors.light),
            "temp": (SensorType.TEMPERATURE.value, environmentalRequest.sensors.temp),
            "humidity": (SensorType.HUMIDITY.value, environmentalRequest.sensors.humidity),
            "airQuality": (SensorType.AIR_QUALITY.value, environmentalRequest.sensors.airQuality)
        }
        
        # Create log entries for registered sensors only
        for reading_key, (sensor_type, sensor_value) in sensor_mappings.items():
            if sensor_type in sensor_map:
                # Create log entry
                logId = generate_log_id()
                log_data = {
                    "logId": logId,
                    "sensorId": sensor_map[sensor_type],
                    "plantId": environmentalRequest.plantId,
                    "value": sensor_value,
                    "timestamp": environmentalRequest.lastUpdated
                }
                
                doc_ref = db.collection("SensorLog").document(logId)
                doc_ref.set(log_data)
                
                created_logs.append({
                    "logId": logId,
                    "sensorId": sensor_map[sensor_type],
                    "sensorType": sensor_type,
                    "value": sensor_value
                })
            else:
                missing_sensors.append(sensor_type)
                skipped_readings.append({
                    "sensorType": sensor_type,
                    "value": sensor_value,
                    "reason": f"No {sensor_type} sensor registered for plant {environmentalRequest.plantId}"
                })
                print(f"Warning: No {sensor_type} sensor registered for plant {environmentalRequest.plantId}")
        
        # Store environmental record for reference
        envRecordId = f"env_{environmentalRequest.sensorRecordId.strftime('%Y%m%d_%H%M%S')}_{environmentalRequest.plantId}"
        env_ref = db.collection("EnvironmentalSensorData").document(envRecordId)
        env_ref.set({
            **environmentalRequest.model_dump(),
            "recordId": envRecordId,
            "processedAt": datetime.utcnow(),
            "createdLogs": len(created_logs),
            "skippedReadings": len(skipped_readings)
        })
        
        # Build response message
        if created_logs and missing_sensors:
            message = f"Partially processed data: {len(created_logs)} sensor readings saved, {len(missing_sensors)} readings skipped due to missing sensors"
        elif created_logs:
            message = f"Successfully processed {len(created_logs)} sensor readings"
        else:
            message = f"No data saved - all {len(missing_sensors)} sensor types are missing for plant {environmentalRequest.plantId}"
        
        return {
            "message": message,
            "recordId": envRecordId,
            "plantId": environmentalRequest.plantId,
            "createdLogs": created_logs,
            "missingSensors": missing_sensors,
            "skippedReadings": skipped_readings,
            "summary": {
                "totalReadings": len(sensor_mappings),
                "savedReadings": len(created_logs),
                "skippedReadings": len(skipped_readings)
            },
            "timestamp": environmentalRequest.lastUpdated.isoformat() + 'Z'
        }
        
    except Exception as e:
        print(f"Error processing environmental sensor data: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing sensor data: {e}")
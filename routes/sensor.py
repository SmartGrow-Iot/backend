# sensor_router.py
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional

from schema import SensorCreate, Sensor, SensorLog, SensorType,EnvironmentalSensorDataIn
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
            # Check if it's already a timezone-aware datetime
            if hasattr(value, 'tzinfo') and value.tzinfo is not None:
                data[key] = value.isoformat()  # Don't add Z if timezone is already present
            else:
                data[key] = value.isoformat() + 'Z'  # Add Z only for naive datetimes
    return data


def get_or_create_sensor(plant_id: str, sensor_type: str, user_id: str) -> str:
    """Get existing sensor or create new one for the plant and sensor type"""
    try:
        # Try to find existing sensor for this plant and type
        query = (db.collection("Sensor")
                .where("plantId", "==", plant_id)
                .where("type", "==", sensor_type)
                .limit(1))
        
        docs = list(query.stream())
        
        if docs:
            # Return existing sensor ID
            return docs[0].to_dict()["sensorId"]
        else:
            # Create new sensor
            sensor_id = generate_sensor_id()
            sensor_data = {
                "sensorId": sensor_id,
                "plantId": plant_id,
                "userId": user_id,
                "sensorModel": f"{sensor_type}",
                "type": sensor_type,
                "description": f"Auto-created {sensor_type} sensor for plant {plant_id}",
                "createdAt": datetime.utcnow()
            }
            
            doc_ref = db.collection("Sensor").document(sensor_id)
            doc_ref.set(sensor_data)
            
            return sensor_id
            
    except Exception as e:
        print(f"Error getting/creating sensor: {e}")
        raise HTTPException(status_code=500, detail=f"Error managing sensor: {e}")

# --- Sensor Management Endpoints ---
@router.post("/v1/sensors", response_model=Sensor)
async def create_sensor(sensor_data: SensorCreate):
    """Create a new sensor"""
    try:
        sensor_id = generate_sensor_id()
        sensor_dict = sensor_data.model_dump()
        sensor_dict["sensorId"] = sensor_id
        
        doc_ref = db.collection("Sensor").document(sensor_id)
        doc_ref.set(sensor_dict)
        
        return Sensor(**sensor_dict)
    except Exception as e:
        print(f"Error creating sensor: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating sensor: {e}")

@router.get("/v1/sensors", response_model=List[Sensor])
async def get_all_sensors(sensor_type: Optional[SensorType] = Query(None)):
    """Get all sensors, optionally filtered by type"""
    try:
        query = db.collection("Sensor")
        if sensor_type:
            query = query.where("type", "==", sensor_type.value)
        
        docs = query.stream()
        sensors = []
        for doc in docs:
            sensor_data = doc.to_dict()
            sensors.append(Sensor(**sensor_data))
        
        return sensors
    except Exception as e:
        print(f"Error fetching sensors: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sensors: {e}")

@router.get("/v1/sensors/{sensor_id}", response_model=Sensor)
async def get_sensor(sensor_id: str):
    """Get a specific sensor by ID"""
    try:
        doc_ref = db.collection("Sensor").document(sensor_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")
        
        sensor_data = doc.to_dict()
        return Sensor(**sensor_data)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching sensor {sensor_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sensor: {e}")


# --- Sensor Log Endpoints ---

@router.post("/v1/sensor-data")
async def submit_environmental_sensor_data(payload: EnvironmentalSensorDataIn):
    """Submit environmental sensor data - creates individual log entries for each sensor reading"""
    try:
        timestamp = payload.lastUpdated
        created_logs = []
        
        # Map sensor readings to sensor types
        sensor_mappings = {
            "soilMoisture": ("soil_moisture", payload.sensors.soilMoisture),
            "light": ("light", payload.sensors.light),
            "temp": ("temperature", payload.sensors.temp),
            "humidity": ("humidity", payload.sensors.humidity),
            "airQuality": ("air_quality", payload.sensors.airQuality)
        }
        
        # Create individual log entries for each sensor reading
        for reading_key, (sensor_type, sensor_value) in sensor_mappings.items():
            if sensor_value is not None:  # Only create log if value exists
                # Get or create sensor for this type
                sensor_id = get_or_create_sensor(payload.plantId, sensor_type, payload.userId)
                
                # Create log entry
                log_id = generate_log_id()
                log_data = {
                    "logId": log_id,
                    "sensorId": sensor_id,
                    "plantId": payload.plantId,
                    "value": sensor_value,
                    "timestamp": timestamp
                }
                
                doc_ref = db.collection("SensorLog").document(log_id)
                doc_ref.set(log_data)
                
                created_logs.append({
                    "logId": log_id,
                    "sensorId": sensor_id,
                    "sensorType": sensor_type,
                    "value": sensor_value
                })
        
        # Store the full environmental sensor record for reference
        env_record_id = f"env_{payload.sensorRecordId.strftime('%Y%m%d_%H%M%S')}_{payload.plantId}"
        env_ref = db.collection("EnvironmentalSensorData").document(env_record_id)
        env_ref.set({
            **payload.model_dump(),
            "recordId": env_record_id,
            "processedAt": datetime.utcnow(),
            "createdLogs": len(created_logs)
        })
        
        return {
            "message": f"Successfully processed {len(created_logs)} sensor readings",
            "recordId": env_record_id,
            "plantId": payload.plantId,
            "createdLogs": created_logs,
            "timestamp": payload.lastUpdated.isoformat() + 'Z'
        }
        
    except Exception as e:
        print(f"Error processing environmental sensor data: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing sensor data: {e}")
    
@router.get("/v1/logs/sensor-data/{plant_id}", response_model=List[SensorLog])
async def get_sensor_logs_by_plant(
    plant_id: str,
    sensor_id: Optional[str] = Query(None),
    sensor_type: Optional[SensorType] = Query(None),
    limit: int = Query(100, le=1000),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get sensor logs for a specific plant with various filters"""
    try:
        # Start with plant filter
        query = db.collection("SensorLog").where("plantId", "==", plant_id)
        
        # Add sensor-specific filter if provided
        if sensor_id:
            query = query.where("sensorId", "==", sensor_id)
        
        # Add date filters if provided
        if start_date:
            query = query.where("timestamp", ">=", start_date)
        
        if end_date:
            query = query.where("timestamp", "<=", end_date)
        
        # Order by timestamp descending and limit results
        query = query.order_by("timestamp", direction="DESCENDING").limit(limit)
        
        docs = query.stream()
        logs = []
        
        for doc in docs:
            log_data = doc.to_dict()
            log_data = convert_timestamps(log_data)
            
            # If filtering by sensor type, we need to check the sensor type
            if sensor_type:
                # Get sensor info to check type
                sensor_doc = db.collection("Sensor").document(log_data["sensorId"]).get()
                if sensor_doc.exists:
                    sensor_data = sensor_doc.to_dict()
                    if sensor_data.get("type") != sensor_type.value:
                        continue  # Skip this log if sensor type doesn't match
                else:
                    continue  # Skip if sensor doesn't exist
            
            logs.append(SensorLog(**log_data))
        
        return logs
    except Exception as e:
        print(f"Error fetching sensor logs for plant {plant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sensor logs: {e}")
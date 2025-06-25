from typing import List
from fastapi import APIRouter, HTTPException
from firebase_config import get_firestore_db
from datetime import datetime
from pydantic import BaseModel
from schema import VALID_MOISTURE_PINS, VALID_ZONES, PlantCreate, PlantListResponse, PlantOut, PlantStatus, \
    PlantThresholds, PlantUpdate, ZoneActuators, ZoneConfig, ZoneCreate, ZoneInfoResponse, ZoneSensors, SystemThresholds
from google.cloud import firestore
import time
from async_lru import alru_cache


router = APIRouter(
    tags=["plants"]
)
db = get_firestore_db()

CACHE_TTL_SECONDS = 60

@alru_cache(maxsize=256)
async def _fetch_plant_from_firestore_cached(plant_id: str, _ttl_hash: int):
    """
    This is the internal, cached function that actually queries Firestore for a single plant.
    The ttl_hash parameter is used to implement a time-based cache expiration.
    """
    print(f"CACHE MISS: Querying Firestore for plant_id: {plant_id}")

    doc = db.collection("Plants").document(plant_id).get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Plant not found")

    return doc.to_dict()

@router.post("/v1/plants")
async def create_plant(plant: PlantCreate):
    """Create new plant with zone and pin validation"""
    try:
        # Get hardware configuration from ZoneInfo
        zone_info_ref = db.collection("ZoneInfo").document(plant.zone)
        zone_info = zone_info_ref.get().to_dict()
        if not zone_info:
            raise HTTPException(400, detail=f"Zone {plant.zone} hardware not configured")

        # Get availability data from Zones
        zone_availability_ref = db.collection("Zones").document(plant.zone)
        zone_availability = zone_availability_ref.get().to_dict()
        if not zone_availability:
            raise HTTPException(400, detail=f"Zone {plant.zone} availability not configured")

        # Verify pin availability
        if plant.moisturePin not in zone_availability.get("availablePins", []):
            raise HTTPException(400, detail={
                "message": "Pin not available",
                "availablePins": zone_availability.get("availablePins", [])
            })

        plant_id = f"plant_{db.collection('Plants').document().id}"
        plant_data = plant.model_dump()

        # Add sensor/actuator references from ZoneInfo
        plant_data.update({
            "plantId": plant_id,
            "zoneHardware": {
                "sensors": {
                    "light": zone_info["sensors"]["lightSensor"],
                    "temperature": zone_info["sensors"]["tempSensor"],
                    "humidity": zone_info["sensors"]["humiditySensor"],
                    "airQuality": zone_info["sensors"]["gasSensor"],
                    "moisture": zone_info["sensors"]["moistureSensor"][str(plant.moisturePin)]
                },
                "actuators": zone_info["actuators"]
            },
            "status": PlantStatus.OPTIMAL,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        })

        # Define the transaction function
        @firestore.transactional
        def update_in_transaction(transaction):
            zone_snap = zone_availability_ref.get(transaction=transaction)
            if len(zone_snap.to_dict().get("plantIds", [])) >= 4:
                raise HTTPException(400, "Zone has maximum plants (4)")

            transaction.update(zone_availability_ref, {
                "plantIds": firestore.ArrayUnion([plant_id]),
                "availablePins": firestore.ArrayRemove([plant.moisturePin]),
                "lastUpdated": datetime.utcnow()
            })

        # Run the transaction
        transaction = db.transaction()
        update_in_transaction(transaction)

        # Get system thresholds
        doc_ref = db.collection("Threshold").document("threshold")
        if not doc_ref.get().exists:
            # Default values if system thresholds has not been set
            thresholds_data = {
                "thresholds": {
                    "airQuality": {
                        "max": 300,
                        "min": 0
                    },
                    "light": {
                        "max": 400,
                        "min": 10
                    },
                    "temperature": {
                        "max": 27,
                        "min": 24
                    }
                }
            }
        else:
            thresholds_doc = doc_ref.get()
            thresholds_data = thresholds_doc.to_dict()

        current_thresholds = plant_data.get("thresholds")
        current_thresholds.update(thresholds_data["thresholds"])
        plant_data["thresholds"] = current_thresholds

        # Create the plant document
        db.collection("Plants").document(plant_id).set(plant_data)

        return plant_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=f"Error creating plant: {str(e)}")
    
@router.get("/v1/plants/{plant_id}")
async def get_plant(plant_id: str):
    """Get complete plant data by ID"""
    try:
        # Call the cache function
        ttl_hash = round(time.time() / CACHE_TTL_SECONDS)
        plant_data = await _fetch_plant_from_firestore_cached(
            plant_id=plant_id,
            _ttl_hash=ttl_hash
        )
        return plant_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving plant: {str(e)}"
        )
    
@router.put("/v1/plants/{plant_id}/thresholds")
async def update_thresholds(plant_id: str, thresholds: PlantThresholds):
    """Update plant moisture thresholds with validation"""
    try:
        doc_ref = db.collection("Plants").document(plant_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Plant not found")
        doc_ref.update({
            "thresholds": thresholds.model_dump(),
            "updatedAt": datetime.utcnow()
        })
        plant_doc = doc_ref.get()
        plant_data = plant_doc.to_dict()

        thresholds_ref = db.collection("Threshold").document("threshold")
        if not thresholds_ref.get().exists:
            # Default values if system thresholds has not been set
            thresholds_data = {
                "thresholds": {
                    "airQuality": {
                        "max": 300,
                        "min": 0
                    },
                    "light": {
                        "max": 400,
                        "min": 10
                    },
                    "temperature": {
                        "max": 27,
                        "min": 24
                    }
                }
            }
        else:
            thresholds_doc = thresholds_ref.get()
            thresholds_data = thresholds_doc.to_dict()

        current_thresholds = plant_data.get("thresholds")
        current_thresholds.update(thresholds_data["thresholds"])
        plant_data["thresholds"] = current_thresholds

        doc_ref.update({
            "thresholds": plant_data["thresholds"],
            "updatedAt": datetime.utcnow()
        })

        return {
            "success": True,
            "updatedThresholds": plant_data["thresholds"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating thresholds: {str(e)}"
        )

@router.post("/v1/system/thresholds")
async def initialize_system_thresholds(thresholds: SystemThresholds):
    """Initialize system-wide thresholds"""
    try:
        thresholds_data = thresholds.model_dump()
        threshold_doc = {}
        threshold_doc.update({
            "thresholds": thresholds_data,
            "lastUpdated": datetime.utcnow()
        })
        db.collection("Threshold").document("threshold").set(threshold_doc)

        system_thresholds = {
            "thresholds": thresholds_data
        }

        # Initialize a WriteBatch
        batch = db.batch()

        # Get a reference to the 'Plants' collection and stream its documents
        plants_ref = db.collection("Plants")
        docs = plants_ref.stream()

        # Loop through each document and add an update operation to the batch
        update_counter = 0
        for doc in docs:
            # Use set() with merge=True to update the nested fields without overwriting 'moisture'
            batch.set(doc.reference, system_thresholds, merge=True)
            update_counter += 1

        # Commit the batch to execute all the updates at once
        if update_counter > 0:
            batch.commit()
            print(f"\nSuccessfully committed batch update for {update_counter} plants.")
        else:
            print("\nNo plants found to update.")

        return thresholds_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error initializing system thresholds: {str(e)}"
        )


@router.put("/v1/system/thresholds")
async def update_system_thresholds(thresholds: SystemThresholds):
    """Update system-wide thresholds"""
    try:
        thresholds_data = thresholds.model_dump()
        doc_ref = db.collection("Threshold").document("threshold")
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="System thresholds not found")

        doc_ref.update({
            "thresholds": thresholds_data,
            "lastUpdated": datetime.utcnow()
        })

        system_thresholds = {
            "thresholds": thresholds_data
        }

        # Initialize a WriteBatch
        batch = db.batch()

        # Get a reference to the 'Plants' collection and stream its documents
        plants_ref = db.collection("Plants")
        docs = plants_ref.stream()

        # Loop through each document and add an update operation to the batch
        update_counter = 0
        for doc in docs:
            # Use set() with merge=True to update the nested fields without overwriting 'moisture'
            batch.set(doc.reference, system_thresholds, merge=True)
            update_counter += 1

        # Commit the batch to execute all the updates at once
        if update_counter > 0:
            batch.commit()
            print(f"\nSuccessfully committed batch update for {update_counter} plants.")
        else:
            print("\nNo plants found to update.")

        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating system thresholds: {str(e)}"
        )

@router.get("/v1/system/thresholds")
async def get_system_thresholds():
    """Get system-wide thresholds"""
    try:
        doc_ref = db.collection("Threshold").document("threshold")
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="System thresholds not found")
        thresholds_doc = doc_ref.get()
        thresholds_data = thresholds_doc.to_dict()
        return thresholds_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving system thresholds: {str(e)}"
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
    

@router.get("/v1/zones/{zone}/plants")
async def get_zone_plants(zone: str):
    """Get all plants in a specific zone"""
    try:
        if zone not in VALID_ZONES:
            raise HTTPException(status_code=400, detail="Invalid zone specified")
            
        docs = db.collection("Plants").where("zone", "==", zone).stream()
        plants = [doc.to_dict() for doc in docs]
        
        return {
            "success": True,
            "count": len(plants),
            "plants": plants
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving zone plants: {str(e)}"
        )

@router.get("/v1/users/{user_id}/zones", response_model=List[ZoneInfoResponse])
async def get_user_zones(user_id: str):
    """Get zone availability for a user with plant counts"""
    try:
        zones_info = []
        
        # Get all plants for this user to calculate plant counts per zone
        plants = db.collection("Plants").where("userId", "==", user_id).stream()
        user_plants = [plant.to_dict() for plant in plants]
        
        for zone_id in VALID_ZONES:
            zone_doc = db.collection("ZoneInfo").document(zone_id).get()
            if not zone_doc.exists:
                continue
                
            zone_data = zone_doc.to_dict()
            
            # Calculate plant count for this user in the zone
            plant_count = sum(1 for plant in user_plants 
                            if plant["zone"].lower() == zone_id)
            
            zones_info.append(ZoneInfoResponse(
                zone=zone_id,
                plantCount=plant_count,
                availablePins=zone_data.get("availablePins", [])
            ))
        
        return zones_info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user zones: {str(e)}"
        )

@router.get("/v1/zones/{zone_id}", response_model=ZoneConfig)
async def get_zone_info(zone_id: str):
    """Get complete zone configuration including hardware references"""
    try:
        if zone_id.lower() not in VALID_ZONES:
            raise HTTPException(status_code=400, detail="Invalid zone specified")
            
        # Get hardware config from ZoneInfo
        zone_info = db.collection("ZoneInfo").document(zone_id.lower()).get()
        if not zone_info.exists:
            raise HTTPException(status_code=404, detail="Zone hardware config not found")
            
        # Get availability data from Zones
        zone_availability = db.collection("Zones").document(zone_id.lower()).get()
        if not zone_availability.exists:
            raise HTTPException(status_code=404, detail="Zone availability data not found")
            
        zone_info_data = zone_info.to_dict()
        zone_availability_data = zone_availability.to_dict()
        
        # Convert moisture sensor keys to integers if needed
        if "moistureSensor" in zone_info_data.get("sensors", {}):
            moisture_sensors = {
                int(pin): sensor_id 
                for pin, sensor_id in zone_info_data["sensors"]["moistureSensor"].items()
            }
            zone_info_data["sensors"]["moistureSensor"] = moisture_sensors
        
        return ZoneConfig(
            zone=zone_id.lower(),
            sensors=ZoneSensors(**zone_info_data["sensors"]),
            actuators=ZoneActuators(**zone_info_data["actuators"]),
            availablePins=zone_availability_data.get("availablePins", []),
            plantIds=zone_availability_data.get("plantIds", [])
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving zone config: {str(e)}"
        )
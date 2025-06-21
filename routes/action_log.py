from fastapi import APIRouter, HTTPException, Query
from schema import ActionLogIn
from firebase_config import get_firestore_db
from datetime import datetime

from services.mqtt_service import mqtt_client

router = APIRouter()

# Map each endpoint to allowed actions
ALLOWED_ACTIONS = {
    "water": {"water_on", "water_off"},
    "light": {"light_on", "light_off"},
    "fan": {"fan_on", "fan_off"}
}

# Shared handler logic
def create_action_log(data: ActionLogIn, category: str):
    allowed = ALLOWED_ACTIONS.get(category)
    if allowed is None:
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if data.action not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action for this endpoint. Allowed: {', '.join(allowed)}"
        )

    db = get_firestore_db()
    data_dict = data.model_dump()

    generated_id = db.collection("ActionLog").document().id
    doc_id = f"action_{generated_id}"

    db.collection("ActionLog").document(doc_id).set(data_dict)

    actuator_id = data_dict.get("actuatorId")
    try:
        doc_ref = db.collection("Actuator").document(actuator_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in Actuator collection.")
        actuator_details = doc.to_dict()
        actuator_zone = actuator_details.get('zone')
        # Publish to MQTT
        mqtt_client.publish_actuator_status(
            zone=actuator_zone,
            action=data.action
        )
    except Exception as e:
        print(f"Error getting Actuator: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving Actuator {doc_id}: {e}")

    return {"id": doc_id, **data_dict}

@router.post("/v1/logs/action/water")
async def log_water_action(data: ActionLogIn):
    """
    Creates a new ActionLog document for watering actions.
    """
    return create_action_log(data, "water")

@router.post("/v1/logs/action/light")
async def log_light_action(data: ActionLogIn):
    """
    Creates a new ActionLog document for light actions.
    """
    return create_action_log(data, "light")

@router.post("/v1/logs/action/fan")
async def log_fan_action(data: ActionLogIn):
    """
    Creates a new ActionLog document for fan actions.
    """
    return create_action_log(data, "fan")

@router.get("/v1/logs/action/{doc_id}")
async def get_action_log(doc_id: str):
    """
    Retrieves a document by its ID from the 'ActionLog' collection.
    """
    db = get_firestore_db()
    try:
        doc_ref = db.collection("ActionLog").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in ActionLog collection.")
        
        # Convert Firestore Timestamps to ISO 8601 strings for JSON serialization
        data = doc.to_dict()
        if 'timestamp' in data and hasattr(data['timestamp'], 'isoformat'):
            data['timestamp'] = data['timestamp'].isoformat() + 'Z'

        return data
    except Exception as e:
        print(f"Error getting ActionLog: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving ActionLog {doc_id}: {e}")
    
@router.get("/v1/logs/actions")
async def get_all_action_logs():
    """
    Retrieves all documents from the 'ActionLog' collection.
    """
    db = get_firestore_db()
    try:
        docs = db.collection("ActionLog").stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            # Convert Firestore Timestamps to ISO 8601 strings for JSON serialization
            if 'timestamp' in data and hasattr(data['timestamp'], 'isoformat'):
                data['timestamp'] = data['timestamp'].isoformat() + 'Z'
            data['id'] = doc.id
            results.append(data)
        return results
    except Exception as e:
        print(f"Error fetching all ActionLogs: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving all ActionLogs: {e}")

@router.get("/v1/logs/action/plant/{plantId}")
async def get_action_logs_by_plant(
    plantId: str,
    sortBy: str = Query("latest", description='Sort order: "latest" (default) or "oldest"')
):
    """
    Fetch action logs for a given plant ID, sorted by timestamp.
    sortBy: "latest" (default, descending) or "oldest" (ascending)
    """
    db = get_firestore_db()
    try:
        query = db.collection("ActionLog").where("plantId", "==", plantId)
        
        if sortBy == "latest":
            query = query.order_by("timestamp", direction="DESCENDING")
        elif sortBy == "oldest":
            query = query.order_by("timestamp", direction="ASCENDING")
        else:
            raise HTTPException(status_code=400, detail='Invalid sortBy value. Use "latest" or "oldest".')

        docs = query.stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            # Convert Firestore Timestamps to ISO 8601 strings for JSON serialization
            if 'timestamp' in data and hasattr(data['timestamp'], 'isoformat'):
                data['timestamp'] = data['timestamp'].isoformat() + 'Z'
            data['id'] = doc.id
            results.append(data)

        return results
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching action logs by plant: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving action logs for plant {plantId}: {e}")
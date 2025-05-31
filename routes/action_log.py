from fastapi import APIRouter, HTTPException
from schema import ActionLogIn
from firebase_config import get_firestore_db
from datetime import datetime

router = APIRouter()

# Map each endpoint to allowed actions
ALLOWED_ACTIONS = {
    "water": {"watering"},
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

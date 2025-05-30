from fastapi import APIRouter, HTTPException
from schema import ActionLogIn
from firebase_config import get_firestore_db
from datetime import datetime

router = APIRouter()

# --- API Endpoints for ActionLog ---
@router.post("/action-log")
async def add_action_log(data: ActionLogIn):
    """
    Creates a new document in the 'ActionLog' collection.
    """
    db = get_firestore_db()
    try:
        data_dict = data.model_dump()
        
        # Convert ID strings to Firestore document references
        # Below is commented out as it requires actual Firestore document references
        # data_dict["plantId"] = db.document(data_dict["plantId"])
        # data_dict["actuatorId"] = db.document(data_dict["actuatorId"])

        # if data_dict["triggerBy"] != "SYSTEM":
        #     data_dict["triggerBy"] = db.document(data_dict["triggerBy"])
            
        # Create a readable and unique action ID
        generated_id = db.collection("ActionLog").document().id
        doc_id = f"action_{generated_id}"

        # Save to Firestore
        db.collection("ActionLog").document(doc_id).set(data_dict)

        return {"id": doc_id, **data_dict}
    
    except HTTPException:
        raise  # Allow manual HTTP errors to propagate

    except Exception as e:
        print(f"Error adding ActionLog: {e}")
        raise HTTPException(status_code=500, detail="Error saving ActionLog")

@router.get("/action-log/{doc_id}")
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

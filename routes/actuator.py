from fastapi import APIRouter, HTTPException
from schema import ActuatorIn
from firebase_config import get_firestore_db

router = APIRouter()

@router.post("/v1/actuator")
async def add_actuator(data: ActuatorIn):
    """
    Creates a new document in the 'Actuator' collection.
    """
    db = get_firestore_db()
    try:
        data_dict = data.model_dump()
        # Generate a readable, unique document ID
        generated_id = db.collection("Actuator").document().id
        doc_id = f"actuator_{generated_id}"

        # Save to Firestore
        db.collection("Actuator").document(doc_id).set(data_dict)

        return {"id": doc_id, **data_dict}
    except Exception as e:
        print(f"Error adding Actuator: {e}")
        raise HTTPException(status_code=500, detail="Error saving Actuator")

@router.get("/v1/actuator/{doc_id}")
async def get_actuator(doc_id: str):
    """
    Retrieves a document by its ID from the 'Actuator' collection.
    """
    db = get_firestore_db()
    try:
        doc_ref = db.collection("Actuator").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in Actuator collection.")
        return doc.to_dict()
    except Exception as e:
        print(f"Error getting Actuator: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving Actuator {doc_id}: {e}")
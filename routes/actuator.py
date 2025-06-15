from fastapi import APIRouter, HTTPException, Query
from schema import VALID_ACTUATOR_TYPES, VALID_ZONES, ActuatorIn
from firebase_config import get_firestore_db
from services.mqtt_service import publish_actuator_command

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
        data_dict["actuatorId"] = doc_id

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

@router.get("/v1/actuators")
async def get_all_actuators():
    """
    Retrieves all actuator documents from the 'Actuator' collection.
    """
    db = get_firestore_db()
    try:
        docs = db.collection("Actuator").stream()
        actuators = [doc.to_dict() for doc in docs]
        return {"count": len(actuators), "actuators": actuators}
    except Exception as e:
        print(f"Error retrieving all actuators: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving all actuators")

@router.get("/v1/actuators/zone/{zone}")
async def get_actuators_by_zone(zone: str, type: str = Query(None, description="Optional actuator type: watering, light, or fan")):
    """
    Get all actuators in a specific zone, optionally filtered by type 'watering', 'light' or 'fan'.
    """
    db = get_firestore_db()
    try:
        if zone not in VALID_ZONES:
            raise HTTPException(status_code=400, detail="Invalid zone specified")
        
        query = db.collection("Actuator").where("zone", "==", zone)

        if type:
            if type not in VALID_ACTUATOR_TYPES:
                raise HTTPException(status_code=400, detail="Invalid actuator type specified")
            query = query.where("type", "==", type)

        docs = query.stream()
        actuators = [doc.to_dict() for doc in docs]

        return {"count": len(actuators), "actuators": actuators}
    except Exception as e:
        print(f"Error retrieving actuators by zone: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving actuators: {str(e)}")

""""
ONLY FOR TESTING PURPOSE, actual logic will change
"""
@router.post("/v1/actuator/{doc_id}/trigger")
async def trigger_actuator(doc_id: str, command: str = "on"):
    """
    Triggers actuator and records the command to Firestore.
    """
    db = get_firestore_db()
    try:
        doc_ref = db.collection("Actuator").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Actuator not found")
        actuator = doc.to_dict()

        # Publish to MQTT
        publish_actuator_command(
            zone=actuator["zone"],
            action=command
        )

        return {"message": f"Actuator '{doc_id}' triggered with command '{command}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
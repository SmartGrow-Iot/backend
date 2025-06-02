from fastapi import APIRouter, HTTPException
from firebase_config import get_firestore_db
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()
db = get_firestore_db()  

@router.post("/v1/plants")
async def create_plant(plant: PlantIn):
    """Creates a new plant document"""
    try:
        plant_id = f"plant_{db.collection('Plants').document().id}"
        plant_data = plant.model_dump()
        plant_data.update({
            "plantId": plant_id,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        })
        
        db.collection("Plants").document(plant_id).set(plant_data)
        return plant_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating plant: {str(e)}")
    
@router.get("/v1/plants/{plant_id}")
async def get_plant(plant_id: str):
    """Retrieves a plant by ID"""
    try:
        doc = db.collection("Plants").document(plant_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Plant not found")
            
        data = doc.to_dict()
        # Convert timestamps to ISO format (like ActionLog does)
        for field in ['createdAt', 'updatedAt']:
            if field in data and hasattr(data[field], 'isoformat'):
                data[field] = data[field].isoformat() + 'Z'
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving plant: {str(e)}")
    
@router.put("/v1/plants/{plant_id}/thresholds")
async def update_thresholds(plant_id: str, thresholds: dict):
    """Updates plant thresholds (partial update)"""
    try:
        doc_ref = db.collection("Plants").document(plant_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Plant not found")
            
        doc_ref.update({
            "thresholds": thresholds,
            "updatedAt": datetime.utcnow()
        })
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating thresholds: {str(e)}")
from fastapi import APIRouter, HTTPException
from firebase_config import get_firestore_db
from datetime import datetime
from pydantic import BaseModel
from schema import PlantCreate
router = APIRouter()
db = get_firestore_db()  

@router.post("/v1/plants")
async def create_plant(plant: PlantCreate):
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
    
@router.get("/v1/plants/user/{user_id}")
async def get_all_plants(user_id: str):
    """
    Retrieve all plants for a specific user
    - Returns: List of plants with pagination info
    """
    try:
        # Query plants by userId
        plants_ref = db.collection("Plants").where("userId", "==", user_id)
        docs = plants_ref.stream()
        
        plants = []
        for doc in docs:
            plant_data = doc.to_dict()
            # Convert Firestore timestamps
            for field in ['createdAt', 'updatedAt']:
                if field in plant_data:
                    plant_data[field] = plant_data[field].isoformat() + 'Z'
            plants.append(plant_data)
        
        if not plants:
            raise HTTPException(
                status_code=404,
                detail=f"No plants found for user {user_id}"
            )
            
        return PlantListResponse(
            count=len(plants),
            plants=plants
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving plants: {str(e)}"
        )
from fastapi import FastAPI, HTTPException
from datetime import datetime        
from dotenv import load_dotenv
from schema import EnvironmentalSensorDataIn, Automation, Sensors, Profile
from routes.actuator import router as actuator_router
from routes.action_log import router as action_log_router

# Import Firebase initialization from firebase_config.py
from firebase_config import initialize_firebase_admin, get_firestore_db
from google.cloud.firestore_v1.base_document import DocumentSnapshot

# Load environment variables from .env file
load_dotenv()

# Initialize Firebase Admin SDK using your modular firebase_config.py
initialize_firebase_admin()

# Get the initialized Firestore DB client
db = get_firestore_db()

app = FastAPI()

# --- API Endpoints ---
# These are sample endpoints to test retrieving and sending enviromental sensor data

@app.get("/")
async def read_root():
    return {"message": "Welcome to FastAPI with Firestore!"}

@app.get("/environmental_data/{document_id}")
async def get_environmental_data(document_id: str):
    """
    Retrieves a document by its ID from the 'EnvironmentalSensorData' collection.
    """
    try:
        doc_ref = db.collection("EnvironmentalSensorData").document(document_id)
        doc: DocumentSnapshot = doc_ref.get()
        if doc.exists:
            # Convert Firestore Timestamps to ISO 8601 strings for JSON serialization
            data = doc.to_dict()
            # Add 'Z' to indicate UTC timezone
            if 'lastUpdated' in data and hasattr(data['lastUpdated'], 'isoformat'):
                data['lastUpdated'] = data['lastUpdated'].isoformat() + 'Z'
            if 'sensorRecordId' in data and hasattr(data['sensorRecordId'], 'isoformat'):
                data['sensorRecordId'] = data['sensorRecordId'].isoformat() + 'Z'
            return data
        else:
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found in EnvironmentalSensorData collection.")
    except Exception as e:
        print(f"Error fetching document /environmental_data/{document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/environmental_data")
async def create_environmental_data(data: EnvironmentalSensorDataIn):
    """
    Creates a new document in the 'EnvironmentalSensorData' collection.
    If 'lastUpdated' or 'sensorRecordId' are not provided, they will be set to UTC now.
    """
    try:
        data_dict = data.model_dump()

        doc_ref = db.collection("EnvironmentalSensorData").add(data_dict)

        new_doc_id = doc_ref[1].id

        if 'lastUpdated' in data_dict and isinstance(data_dict['lastUpdated'], datetime):
            data_dict['lastUpdated'] = data_dict['lastUpdated'].isoformat() + 'Z'
        if 'sensorRecordId' in data_dict and isinstance(data_dict['sensorRecordId'], datetime):
            data_dict['sensorRecordId'] = data_dict['sensorRecordId'].isoformat() + 'Z'

        return {"id": new_doc_id, **data_dict}
    except Exception as e:
        print(f"Error creating environmental data: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating document: {e}")

# Include the routers for actuator and action log    
app.include_router(actuator_router)
app.include_router(action_log_router)
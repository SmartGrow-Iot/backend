from fastapi import FastAPI
from datetime import datetime        
from dotenv import load_dotenv
from schema import EnvironmentalSensorDataIn, Automation, Sensors, Profile

# Import Firebase initialization from firebase_config.py
from firebase_config import initialize_firebase_admin, get_firestore_db

# Initialize Firebase Admin SDK using your modular firebase_config.py
initialize_firebase_admin()

# Get the initialized Firestore DB client
db = get_firestore_db()

app = FastAPI(title="SmartGrow API", version="1.0.0")

# Include the sensor router
from routes.user import router as user_router
from routes.sensor import router as sensor_router
from routes.actuator import router as actuator_router
from routes.action_log import router as action_log_router
from routes.plants import router as plant_router 



# --- Root Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to SmartGrow API!"}

app.include_router(user_router, prefix='/api')
app.include_router(actuator_router, prefix='/api')
app.include_router(action_log_router, prefix='/api')
app.include_router(sensor_router, prefix='/api')
app.include_router(plant_router, prefix='/api')
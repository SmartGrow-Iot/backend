from contextlib import asynccontextmanager

from fastapi import FastAPI
from datetime import datetime        
from dotenv import load_dotenv
from services.mqtt_service import mqtt_client
import asyncio
from services.garbage_collector_service import run_garbage_collector
from services.ping_service import run_ping
from fastapi.middleware.cors import CORSMiddleware


# Import Firebase initialization from firebase_config.py
from firebase_config import initialize_firebase_admin, get_firestore_db

# Initialize Firebase Admin SDK using your modular firebase_config.py
initialize_firebase_admin()

# Get the initialized Firestore DB client
db = get_firestore_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Code to run on application startup ---
    mqtt_client.connect()
    mqtt_client.subscribe_actuator_feedback()
    gc_task = asyncio.create_task(run_garbage_collector())
    ping_task = asyncio.create_task(run_ping())
    app.state.gc_task = gc_task
    app.state.ping_task = ping_task
    yield
    # --- Code to run on application shutdown ---
    app.state.gc_task.cancel()
    app.state.ping_task.cancel()
    mqtt_client.disconnect()

app = FastAPI(title="SmartGrow API", version="2.0.0", lifespan=lifespan)

origins = [
    "https://smartgrow-kappa.vercel.app",  # monitoring dashboard
    "http://localhost:5173",         # local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Include the sensor router
from routes.user import router as user_router
from routes.sensor import router as sensor_router
from routes.actuator import router as actuator_router
from routes.action_log import router as action_log_router
#from routes.device_control import router as device_control_router
from routes.plants import router as plant_router



# --- Root Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to SmartGrow API!"}

app.include_router(user_router, prefix='/api')
app.include_router(actuator_router, prefix='/api')
app.include_router(action_log_router, prefix='/api')
app.include_router(sensor_router, prefix='/api')
#app.include_router(device_control_router, prefix='/api')
app.include_router(plant_router, prefix='/api')


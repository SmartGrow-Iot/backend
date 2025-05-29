from pydantic import BaseModel, Field
from datetime import datetime

# --- Pydantic Models for Data Validation ---

class Automation(BaseModel):
    fanOn: bool = False
    lightOn: bool = False
    waterOn: bool = False

class Sensors(BaseModel):
    humidity: str
    light: str
    soilMoisture: str
    temp: str

class Profile(BaseModel):
    humidityMax: str
    humidityMin: str
    lightMax: str
    lightMin: str
    moistureMax: str
    moistureMin: str
    tempMax: str
    tempMin: str

class EnvironmentalSensorDataIn(BaseModel):
    """
    Pydantic model for incoming EnvironmentalSensorData for POST requests.
    Using 'In' suffix to denote it's for input validation.
    """
    automation: Automation
    lastUpdated: datetime = Field(default_factory=datetime.utcnow) # Automatically set UTC time
    plantId: str
    profile: Profile
    sensorRecordId: datetime = Field(default_factory=datetime.utcnow) # Automatically set UTC time
    sensors: Sensors
    userId: str
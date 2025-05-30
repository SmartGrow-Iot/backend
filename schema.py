from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from enum import Enum

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

class TriggerType(str, Enum):
    manual = "manual"
    auto = "auto"

class ActionLogIn(BaseModel):
    """
    Pydantic model for incoming ActionLog for POST requests.
    """
    action: str # 'action' is used to denote the type of action performed, 'watering', 'increase_light', etc.
    actuatorId: str
    plantId: str
    trigger: TriggerType # 'trigger' is used to denote the type of action 'manual' or 'auto'
    triggerBy: Optional[str] = None # 'triggerBy' is used to denote who triggered the action, {userId} or 'system'
    timestamp: datetime = Field(default_factory=datetime.utcnow) 
    
    # Validation to ensure plantId and actuatorId are provided
    @field_validator('plantId')
    def check_plantId(cls, v):
        if not v:
            raise ValueError("Missing 'plantId'. Please provide a valid plant ID.")
        return v

    @field_validator('actuatorId')
    def check_actuatorId(cls, v):
        if not v:
            raise ValueError("Missing 'actuatorId'. Please provide a valid actuator ID.")
        return v
    
    # Validation to ensure triggerBy is set correctly based on trigger type
    @model_validator(mode='after')
    def validate_trigger_logic(cls, values):
        trigger = values.trigger
        triggerBy = values.triggerBy

        # If trigger is 'manual', triggerBy (userId) must be provided
        if trigger == TriggerType.manual and not triggerBy:
            raise ValueError("triggerBy is required when trigger is 'manual'")

        # If trigger is 'auto', triggerBy should be set to "SYSTEM"
        if trigger == TriggerType.auto:
            values['triggerBy'] = "SYSTEM"

        return values
    
class ActuatorIn(BaseModel):
    """
    Pydantic model for incoming Actuator data for POST requests.
    """
    actuatorModel : str
    description : str
    type : str
    createdAt: datetime = Field(default_factory=datetime.utcnow)  # Automatically set UTC time
    
    @field_validator('actuatorModel')
    def check_actuatorModel(cls, v):
        if not v:
            raise ValueError("Missing 'actuatorModel'. Please provide an actuatorModel value.")
        return v
    
    @field_validator('description')
    def check_description(cls, v):
        if not v:
            raise ValueError("Missing 'description'. Please provide a description value.")
        return v
    
    @field_validator('type')
    def check_type(cls, v):
        if not v:
            raise ValueError("Missing 'type'. Please provide a type value.")
        return v

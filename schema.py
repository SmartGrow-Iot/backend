from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum

# --- Sensor-specific Enums ---
class SensorType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity" 
    LIGHT = "light"
    SOIL_MOISTURE = "soil_moisture"

class SensorCreate(BaseModel):
    """Model for creating a new sensor"""
    sensorModel: str
    type: SensorType
    description: Optional[str] = None

class Sensor(BaseModel):
    """Model representing a sensor entity"""
    sensorId: str
    sensorModel: str
    type: SensorType
    description: Optional[str] = None

class SensorLogCreate(BaseModel):
    """Model for creating sensor log entries"""
    plantId: str
    sensorId: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SensorLog(BaseModel):
    """Model representing a sensor log entry"""
    logId: str
    plantId: str
    sensorId: str
    value: float
    timestamp: datetime
    
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

class ActionType(str, Enum):
    watering = "watering"
    light_on = "light_on"
    light_off = "light_off"
    fan_on = "fan_on"
    fan_off = "fan_off"

class ActionLogIn(BaseModel):
    """
    Pydantic model for incoming ActionLog for POST requests.
    """
    action: ActionType
    actuatorId: str
    plantId: str
    amount: Optional[float] = None  # Used only for 'watering' actions
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
    def validate_trigger_logic(self) -> 'ActionLogIn':
        if self.trigger == TriggerType.manual and not self.triggerBy:
            raise ValueError("triggerBy is required when trigger is 'manual'")

        if self.trigger == TriggerType.auto:
            self.triggerBy = "SYSTEM"
            
        # Validate amount for 'watering'
        if self.action == "watering":
            if self.amount is None:
                raise ValueError("amount is required for watering actions.")
            if self.amount <= 0:
                raise ValueError("amount must be a positive number.")
        return self
    
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

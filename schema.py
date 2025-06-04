from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum

# --- User Profile Enums ---
class UserProfile(BaseModel):
    display_name: str = None
    email: str = None
    # phone_number: str = None

class UserRegistration(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None
    
    @field_validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


# --- Sensor-specific Enums ---
class SensorType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity" 
    LIGHT = "light"
    SOIL_MOISTURE = "soil_moisture"
    AIR_QUALITY = "air_quality"

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
    humidity: float
    light: float
    soilMoisture: float
    temp: float
    airQuality: float

class Profile(BaseModel):
    humidityMax: float
    humidityMin: float
    lightMax: float
    lightMin: float
    moistureMax: float
    moistureMin: float
    tempMax: float
    tempMin: float

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
        if self.action == ActionType.watering:
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
    
    # ---- Plant Management Models ----
class ThresholdRange(BaseModel):
    """Nested model for min/max threshold values"""
    min: float
    max: float

    @model_validator(mode='after')
    def validate_range(self) -> 'ThresholdRange':
        if self.min >= self.max:
            raise ValueError("min must be less than max")
        return self

class PlantThresholds(BaseModel):
    """Container for all plant thresholds"""
    moisture: ThresholdRange
    temperature: ThresholdRange
    light: ThresholdRange

class PlantCreate(BaseModel):
    """Model for creating a new plant"""
    name: str
    userId: str
    thresholds: PlantThresholds
    description: Optional[str] = None

    @field_validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Plant name cannot be empty")
        return v.strip()

class PlantUpdate(BaseModel):
    """Model for updating plant details (partial updates allowed)"""
    name: Optional[str] = None
    thresholds: Optional[PlantThresholds] = None
    description: Optional[str] = None

    @model_validator(mode='after')
    def validate_at_least_one_field(cls, values):
        if not any([values.name, values.thresholds, values.description]):
            raise ValueError("At least one field must be provided for update")
        return values

class PlantOut(PlantCreate):
    plantId: str
    createdAt: datetime
    updatedAt: datetime

class PlantListResponse(BaseModel):
    success: bool = True
    count: int
    plants: List[PlantOut]
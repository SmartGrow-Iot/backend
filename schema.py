from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum

# --- User Profile Enums ---
class UserProfile(BaseModel):
    display_name: str = Field(None, example="John Doe")
    email: str = Field(None, example="johndoe@example.com")
    # phone_number: str = None

class UserRegistration(BaseModel):
    email: str = Field(..., example="newuser@example.com")
    password: str = Field(..., example="Pass123$")
    display_name: Optional[str] = Field(None, example="Jane Smith")
    
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
    sensorModel: str = Field(..., example="DHT22")
    type: SensorType = Field(..., example=SensorType.TEMPERATURE)
    description: Optional[str] = Field(None, example="Temperature sensor for greenhouse monitoring")

class Sensor(BaseModel):
    """Model representing a sensor entity"""
    sensorId: str = Field(..., example="sensor_12345")
    sensorModel: str = Field(..., example="DHT22")
    type: SensorType = Field(..., example=SensorType.TEMPERATURE)
    description: Optional[str] = Field(None, example="Temperature sensor for greenhouse monitoring")

class SensorLogCreate(BaseModel):
    """Model for creating sensor log entries"""
    plantId: str = Field(..., example="plant_001")
    sensorId: str = Field(..., example="sensor_12345")
    value: float = Field(..., example=23.5)
    timestamp: datetime = Field(default_factory=datetime.utcnow, example=datetime.utcnow().isoformat() + "Z")

class SensorLog(BaseModel):
    """Model representing a sensor log entry"""
    logId: str = Field(..., example="log_67890")
    plantId: str = Field(..., example="plant_001")
    sensorId: str = Field(..., example="sensor_12345")
    value: float = Field(..., example=23.5)
    timestamp: datetime = Field(..., example=datetime.utcnow().isoformat() + "Z")

class Automation(BaseModel):
    fanOn: bool = Field(False, example=True)
    lightOn: bool = Field(False, example=False)
    waterOn: bool = Field(False, example=True)

class Sensors(BaseModel):
    humidity: float = Field(..., example=65.2)
    light: float = Field(..., example=1200.0)
    soilMoisture: float = Field(..., example=45.8)
    temp: float = Field(..., example=24.3)
    airQuality: float = Field(..., example=85.5)

class Profile(BaseModel):
    humidityMax: float = Field(..., example=70.0)
    humidityMin: float = Field(..., example=40.0)
    lightMax: float = Field(..., example=1500.0)
    lightMin: float = Field(..., example=800.0)
    moistureMax: float = Field(..., example=60.0)
    moistureMin: float = Field(..., example=30.0)
    tempMax: float = Field(..., example=28.0)
    tempMin: float = Field(..., example=18.0)

class EnvironmentalSensorDataIn(BaseModel):
    """
    Pydantic model for incoming EnvironmentalSensorData for POST requests.
    Using 'In' suffix to denote it's for input validation.
    """
    automation: Automation = Field(..., example={
        "fanOn": True,
        "lightOn": False,
        "waterOn": True
    })
    lastUpdated: datetime = Field(
        default_factory=datetime.utcnow, 
        example=datetime.utcnow().isoformat() + "Z"
    )
    plantId: str = Field(..., example="plant_greenhouse_001")
    profile: Profile = Field(..., example={
        "humidityMax": 70.0,
        "humidityMin": 40.0,
        "lightMax": 1500.0,
        "lightMin": 800.0,
        "moistureMax": 60.0,
        "moistureMin": 30.0,
        "tempMax": 28.0,
        "tempMin": 18.0
    })
    sensorRecordId: datetime = Field(
        default_factory=datetime.utcnow, 
        example=datetime.utcnow().isoformat() + "Z"
    )
    sensors: Sensors = Field(..., example={
        "humidity": 65.2,
        "light": 1200.0,
        "soilMoisture": 45.8,
        "temp": 24.3,
        "airQuality": 85.5
    })
    userId: str = Field(..., example="user_12345")


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
    """Complete plant model with system-generated fields"""
    plantId: str
    createdAt: datetime
    updatedAt: datetime
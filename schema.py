from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional
from enum import Enum

# --- User Profile Enums ---
class UserProfile(BaseModel):
    display_name: str = Field(None, example="John Doe")
    email: str = Field(None, example="johndoe@example.com")
    group: Optional[int] = Field(None, example=5, description="User group number (1-16)")
    # phone_number: str = None
    

class UserRegistration(BaseModel):
    email: str = Field(..., example="newuser@example.com")
    password: str = Field(..., example="Pass123$")
    display_name: Optional[str] = Field(None, example="Jane Smith")
    group: int = Field(..., example=5, description="User group number (1-16)")
    
    @field_validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v
    
    @field_validator('group')
    def validate_group(cls, v):
        if v < 1 or v > 16:
            raise ValueError('Group must be between 1 and 16')
        return v

# -- sensor data --
class PinSoilMoisture(BaseModel):
    pin: int = Field(..., example=34, description="GPIO pin number")
    soilMoisture: float = Field(..., example=45.8)

class EnvironmentalDataRequest(BaseModel):
    """Store zone environmental data directly as received"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    zoneId: str = Field(..., example="zone1")
    zoneSensors: dict[str, float] = Field(..., example={
        "humidity": 83,
        "light": 48,
        "temp": 29.4,
        "airQuality": 89
    })
    soilMoistureByPin: List[PinSoilMoisture] = Field(..., example=[
        {"pin": 34, "soilMoisture": 23},
        {"pin": 35, "soilMoisture": 42},
        {"pin": 36, "soilMoisture": 53},
        {"pin": 39, "soilMoisture": 27}
    ])
    userId: Optional[str] = Field(None, example="user123")


class TriggerType(str, Enum):
    manual = "manual"
    auto = "auto"

class ActionType(str, Enum):
    water_on = "water_on"
    water_off = "water_off"
    light_on = "light_on"
    light_off = "light_off"
    fan_on = "fan_on"
    fan_off = "fan_off"

VALID_ACTUATOR_TYPES = ["watering", "light", "fan"]

class ActionLogIn(BaseModel):
    """
    Pydantic model for incoming ActionLog for POST requests.
    """
    action: ActionType = Field(
        ...,
        title="Action Type",
        description="The type of action performed by the actuator.",
        examples=["water_on"]
    )
    actuatorId: str = Field(
        ...,
        title="Actuator ID",
        description="The unique identifier of the actuator that performed the action.",
        examples=["actuator-123"]
    )
    plantId: str = Field(
        ...,
        title="Plant ID",
        description="The identifier of the plant associated with the action.",
        examples=["plant-456"]
    )

    trigger: TriggerType = Field(
        ...,
        title="Trigger Type",
        description="Indicates whether the action was triggered manually or automatically.",
        examples=["manual"]
    )
    triggerBy: Optional[str] = Field(
        None,
        title="Triggered By",
        description="Identifier of the user that triggered the action. Will be set to 'SYSTEM' for automatic triggers.",
        examples=["user-789"]
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        title="Timestamp",
        description="The date and time when the action occurred.",
        examples=["2025-06-05T14:30:00Z"]
    )
    
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
    
        return self
    
class ActuatorIn(BaseModel):
    """
    Pydantic model for incoming Actuator data for POST requests.
    """
    actuatorModel: str = Field(
        ...,
        title="Actuator Model",
        description="The model of the actuator being used",
        examples=["SG-WP-1000"],
    )   
    description: str = Field(
        ...,
        title="Description",
        description="A brief description of the actuator's function or features.",
        examples=["High-pressure water pump for irrigation"]
    )
    type: Literal["watering", "light", "fan"] = Field(
        ...,
        title="Actuator Type",
        description="The type of the actuator. Can only be 'watering', 'light', or 'fan'.",
        examples=["watering"]
    )
    zone: Literal["zone1", "zone2", "zone3", "zone4"] = Field(
        ...,
        title="Zone",
        description="The zone where the actuator is installed.",
        examples=["zone1"]
    )
    createdAt: datetime = Field(
        default_factory=datetime.utcnow,
        title="Creation Timestamp",
        description="Timestamp indicating when the actuator was created.",
        examples=["2025-06-05T10:00:00Z"]
    )  # Automatically set UTC time
    
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
    # ---- Enums ----
class PlantStatus(str, Enum):
    OPTIMAL = "optimal"
    CRITICAL = "critical"

VALID_ZONES = ["zone1", "zone2", "zone3", "zone4"]
VALID_MOISTURE_PINS = [34, 35, 36, 39]

class PlantType(str, Enum):
    VEGETABLE = "vegetable"
    HERB = "herb"
    FRUIT = "fruit"
    FLOWER = "flower"
    SUCCULENT = "succulent"
    
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
    airQuality: ThresholdRange 

    @model_validator(mode='after')
    def validate_air_quality(cls, values):
        if values.airQuality.max > 1000:  
            raise ValueError("Air quality maximum should not exceed 1000")
        return values

class PlantCreate(BaseModel):
    name: str
    userId: str
    zone: Literal["zone1", "zone2", "zone3", "zone4"]
    moisturePin: Literal[34, 35, 36, 39]
    thresholds: PlantThresholds
    type: PlantType
    description: Optional[str] = None
    image: Optional[str] = None
    growthTime: Optional[int] = 30

    @field_validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Plant name cannot be empty")
        return v.strip()

class PlantUpdate(BaseModel):
    name: Optional[str] = None
    thresholds: Optional[PlantThresholds] = None
    description: Optional[str] = None
    moisturePin: Optional[Literal[34, 35, 36, 39]] = None
    status: Optional[PlantStatus] = None
    waterLevel: Optional[float] = None
    lightLevel: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    airQualityLevel: Optional[float] = None  

    @model_validator(mode='after')
    def validate_at_least_one_field(cls, self):
        if not any([self.name, self.thresholds, self.description, 
                   self.moisturePin, self.status, self.waterLevel,
                   self.lightLevel, self.temperature, self.humidity,
                   self.airQualityLevel]): 
            raise ValueError("At least one field must be provided for update")
        return self

class PlantOut(PlantCreate):
    plantId: str
    status: PlantStatus = PlantStatus.OPTIMAL
    waterLevel: float = 50.0
    lightLevel: float = 50.0
    temperature: float = 25.0
    humidity: float = 50.0
    airQualityLevel: float = 100.0
    createdAt: datetime
    updatedAt: datetime

class PlantListResponse(BaseModel):
    success: bool = True
    count: int
    plants: List[PlantOut]

class ZoneInfoResponse(BaseModel):
    zone: str
    plantCount: int
    availablePins: List[int]

class ZoneBase(BaseModel):
    zoneId: Literal["zone1", "zone2", "zone3", "zone4"]
    userId: str
    plantIds: List[str] = Field(max_items=4)
    availablePins: List[Literal[34, 35, 36, 39]]
    lastUpdated: datetime

class ZoneCreate(BaseModel):
    zoneId: Literal["zone1", "zone2", "zone3", "zone4"]
    userId: str

class ZoneSensors(BaseModel):
    lightSensor: str
    tempSensor: str
    humiditySensor: str
    gasSensor: str
    moistureSensor: Dict[int, str] 

class ZoneActuators(BaseModel):
    fanActuator: str
    lightActuator: str
    waterActuator: str

class ZoneConfig(BaseModel):
    zone: str  
    sensors: ZoneSensors
    actuators: ZoneActuators
    availablePins: List[int]  
    plantIds: List[str] = Field(default_factory=list, max_items=4)
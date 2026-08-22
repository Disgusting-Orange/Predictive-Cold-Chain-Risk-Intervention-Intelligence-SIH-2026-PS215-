from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TelemetryCreate(BaseModel):
    shipmentId: str = Field(..., description="Canonical shipment code, e.g. SHP-1042")
    deviceId: Optional[str] = Field("BOX-01", description="IoT edge node identifier")
    timestamp: Optional[datetime] = None
    temperature: float = Field(..., description="Cargo temperature in Celsius")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Ambient humidity percentage")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    speed: Optional[float] = Field(0.0, ge=0.0, description="Speed in km/h")
    doorOpen: bool = Field(False, description="True if cargo container door is open")
    coolingPower: Optional[int] = Field(70, ge=0, le=100, description="Reefer cooling power %")
    gasValue: Optional[float] = Field(None, description="Spoilage gas sensor reading (MQ series/VOC)")
    battery: Optional[float] = Field(90.0, ge=0.0, le=100.0, description="Battery level %")


class TelemetryResponse(BaseModel):
    id: str
    shipmentId: str
    deviceId: Optional[str]
    timestamp: datetime
    temperature: float
    humidity: float
    latitude: Optional[float]
    longitude: Optional[float]
    speed: float
    doorOpen: bool
    coolingPower: int
    battery: float

    class Config:
        from_attributes = True

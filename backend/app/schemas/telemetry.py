from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any
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

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize shipment ID
            if "shipmentId" not in data:
                for k in ("shipment_id", "shipmentCode", "shipment_code", "shipment", "shp_id", "id"):
                    if k in data and data[k]:
                        data["shipmentId"] = str(data[k])
                        break

            # Normalize device ID
            if "deviceId" not in data:
                for k in ("device_id", "deviceId", "device", "node_id", "nodeId"):
                    if k in data and data[k]:
                        data["deviceId"] = str(data[k])
                        break

            # Normalize temperature
            if "temperature" not in data:
                for k in ("temp", "temp_c", "temperature_c", "t"):
                    if k in data and data[k] is not None:
                        data["temperature"] = float(data[k])
                        break

            # Normalize humidity
            if "humidity" not in data:
                for k in ("hum", "humidity_pct", "rh", "h"):
                    if k in data and data[k] is not None:
                        data["humidity"] = float(data[k])
                        break

            # Normalize latitude / longitude
            if "latitude" not in data and "lat" in data:
                data["latitude"] = float(data["lat"]) if data["lat"] is not None else None
            if "longitude" not in data:
                for k in ("lng", "lon", "long"):
                    if k in data and data[k] is not None:
                        data["longitude"] = float(data[k])
                        break

            # Normalize door state
            if "doorOpen" not in data:
                for k in ("door_open", "door", "doorState", "door_state"):
                    if k in data and data[k] is not None:
                        val = data[k]
                        data["doorOpen"] = bool(val == 1 or val is True or str(val).lower() == "open" or str(val).lower() == "true")
                        break

            # Normalize cooling power
            if "coolingPower" not in data:
                for k in ("cooling_power", "cooling", "reefer_power", "cooling_power_percent"):
                    if k in data and data[k] is not None:
                        data["coolingPower"] = int(data[k])
                        break

            # Normalize battery
            if "battery" not in data:
                for k in ("battery_level", "batteryLevel", "batt", "battery_pct"):
                    if k in data and data[k] is not None:
                        data["battery"] = float(data[k])
                        break

            # Normalize gas / VOC
            if "gasValue" not in data:
                for k in ("gas_value", "gas", "voc", "voc_level", "vocLevel", "mq_value"):
                    if k in data and data[k] is not None:
                        data["gasValue"] = float(data[k])
                        break

        return data


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

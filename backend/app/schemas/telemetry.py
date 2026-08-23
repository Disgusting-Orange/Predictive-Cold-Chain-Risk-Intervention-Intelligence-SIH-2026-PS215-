from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Dict, Any
from datetime import datetime


class TelemetryCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shipmentId: str = Field(..., description="Canonical shipment code, e.g. SHP-1042")
    deviceId: Optional[str] = Field("BOX-01", description="IoT edge node identifier")
    timestamp: Optional[datetime] = None
    temperature: Optional[float] = Field(None, description="Cargo temperature in Celsius")
    humidity: Optional[float] = Field(50.0, ge=0.0, le=100.0, description="Ambient humidity percentage")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    speed: Optional[float] = Field(0.0, ge=0.0, description="Speed in km/h")
    doorOpen: bool = Field(False, description="True if cargo container door is open")
    coolingPower: Optional[int] = Field(70, ge=0, le=100, description="Reefer cooling power %")
    gasValue: Optional[float] = Field(None, description="Spoilage gas sensor reading (MQ series/VOC)")
    battery: Optional[float] = Field(90.0, ge=0.0, le=100.0, description="Battery level %")
    probes: Optional[Dict[str, Optional[float]]] = Field(None, description="Optional raw 9-probe mesh temperature map")

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. shipmentId
            if "shipmentId" not in data:
                for k in ["shipment_id", "shipmentCode", "shipment_code", "shipment"]:
                    if k in data and data[k] is not None:
                        data["shipmentId"] = str(data[k])
                        break
            
            # 2. deviceId
            if "deviceId" not in data:
                for k in ["device_id", "deviceCode", "device"]:
                    if k in data and data[k] is not None:
                        data["deviceId"] = str(data[k])
                        break

            # 3. temperature
            if "temperature" not in data:
                for k in ["temp", "temp_c", "t"]:
                    if k in data and data[k] is not None:
                        try:
                            data["temperature"] = float(data[k])
                        except (ValueError, TypeError):
                            pass
                        break

            # 4. humidity
            if "humidity" not in data:
                for k in ["hum", "humidity_pct", "rh"]:
                    if k in data and data[k] is not None:
                        try:
                            data["humidity"] = float(data[k])
                        except (ValueError, TypeError):
                            pass
                        break

            # 5. doorOpen
            if "doorOpen" not in data:
                for k in ["door_open", "door"]:
                    if k in data and data[k] is not None:
                        val = data[k]
                        if isinstance(val, bool):
                            data["doorOpen"] = val
                        elif isinstance(val, (int, float)):
                            data["doorOpen"] = val != 0
                        elif isinstance(val, str):
                            data["doorOpen"] = val.lower() in ("true", "1", "yes", "t", "y")
                        break

            # 6. latitude
            if "latitude" not in data:
                for k in ["lat"]:
                    if k in data and data[k] is not None:
                        try:
                            data["latitude"] = float(data[k])
                        except (ValueError, TypeError):
                            pass
                        break

            # 7. longitude
            if "longitude" not in data:
                for k in ["lng", "lon"]:
                    if k in data and data[k] is not None:
                        try:
                            data["longitude"] = float(data[k])
                        except (ValueError, TypeError):
                            pass
                        break

            # 8. coolingPower
            if "coolingPower" not in data:
                for k in ["cooling_power", "cooling"]:
                    if k in data and data[k] is not None:
                        try:
                            data["coolingPower"] = int(float(data[k]))
                        except (ValueError, TypeError):
                            pass
                        break

            # 9. battery
            if "battery" not in data:
                for k in ["battery_level", "batt"]:
                    if k in data and data[k] is not None:
                        try:
                            data["battery"] = float(data[k])
                        except (ValueError, TypeError):
                            pass
                        break

            # 10. gasValue
            if "gasValue" not in data:
                for k in ["gas_value", "voc", "voc_level"]:
                    if k in data and data[k] is not None:
                        try:
                            data["gasValue"] = float(data[k])
                        except (ValueError, TypeError):
                            pass
                        break

        return data


class TelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

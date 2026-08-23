"""
FrostLink Raw Telemetry Schema -- Phase 14
==========================================
Defines typed Pydantic models and data structures for raw sensor packets received from
hardware gateways (ESP32/telematics) and the offline physical simulator.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any
from datetime import datetime
import math

class RawTelemetryPacket(BaseModel):
    shipment_id: str = Field(..., min_length=1, description="Unique shipment or journey identifier", example="SHIP_0492_A")
    timestamp: str = Field(..., description="ISO-8601 observation timestamp", example="2026-08-23T14:30:00Z")
    probes: Dict[str, Optional[float]] = Field(
        ...,
        description="Dictionary of spatial temperature probe measurements in °C (e.g., Front_Top, Rear_Bottom, etc.)",
        example={
            "Front_Top": 2.4,
            "Front_Middle": 2.1,
            "Front_Bottom": 1.9,
            "Middle_Top": 2.8,
            "Middle_Middle": 2.3,
            "Middle_Bottom": 2.0,
            "Rear_Top": 3.2,
            "Rear_Middle": 2.5,
            "Rear_Bottom": 2.2
        }
    )
    sconf: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Telemetry confidence score [0, 1]")
    coverage_time: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Packet temporal completeness score [0, 1]")
    
    # Optional auxiliary fields (future hardware / telemetry)
    ambient_temp: Optional[float] = Field(None, description="External ambient temperature in °C")
    door_open: Optional[bool] = Field(None, description="Container door open/close status")
    speed_kmh: Optional[float] = Field(None, description="Vehicle ground speed in km/h")
    battery_voltage: Optional[float] = Field(None, description="Auxiliary battery voltage")

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO-8601 timestamp: '{v}'. Error: {e}")
        return v

    @field_validator("probes")
    @classmethod
    def validate_probe_measurements(cls, v: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
        if not isinstance(v, dict) or len(v) == 0:
            raise ValueError("Raw telemetry packet must contain at least one probe reading.")
        
        cleaned = {}
        for probe_name, val in v.items():
            if val is None:
                cleaned[probe_name] = None
                continue
            try:
                val_f = float(val)
                if math.isinf(val_f) or math.isnan(val_f):
                    cleaned[probe_name] = None
                elif val_f < -50.0 or val_f > 80.0:
                    # Physically implausible cold-chain sensor value -> mark null
                    cleaned[probe_name] = None
                else:
                    cleaned[probe_name] = val_f
            except (ValueError, TypeError):
                cleaned[probe_name] = None
        return cleaned

class RawTelemetryHistory(BaseModel):
    shipment_id: str = Field(..., description="Shipment ID")
    packets: List[RawTelemetryPacket] = Field(..., min_length=1, description="Chronological sequence of raw telemetry packets")

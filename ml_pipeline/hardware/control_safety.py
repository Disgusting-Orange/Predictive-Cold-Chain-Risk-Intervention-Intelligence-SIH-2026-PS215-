"""
FrostLink Refrigeration Control Safety State Machine -- Phase 21
================================================================
Software abstraction for refrigeration protective action requests.

IMPORTANT SAFETY NOTICE:
Direct closed-loop compressor or HVAC manipulation is NOT performed by this module
unless an actual certified physical refrigeration controller interface is present.
This module emits structured PROTECTIVE_ACTION_REQUEST advisories.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class ControlStateEnum(str, Enum):
    NORMAL = "NORMAL"
    COOLING_REQUIRED = "COOLING_REQUIRED"
    PROTECTIVE_ACTION_REQUESTED = "PROTECTIVE_ACTION_REQUESTED"
    RECOVERY = "RECOVERY"
    FAULT = "FAULT"

class ProtectiveActionRequest(BaseModel):
    state: ControlStateEnum
    requested_action: str
    target_temperature_c: Optional[float] = 4.0
    cooling_power_level: Optional[int] = 70
    reasons: List[str] = Field(default_factory=list)
    issued_at: str
    is_hardware_controller_connected: bool = False
    disclaimer: str = (
        "Advisory software protective action request. Direct closed-loop compressor actuation "
        "requires certified hardware controller interface."
    )

class ControlSafetyEngine:
    def __init__(self):
        self._shipment_states: Dict[str, ControlStateEnum] = {}
        self._state_timestamps: Dict[str, datetime] = {}

    def evaluate_control_state(
        self,
        shipment_id: str,
        fused_state: str,
        risk_probability: Optional[float],
        risk_level: Optional[str],
        observed_events: List[Dict[str, Any]],
        current_temp: Optional[float] = None,
        temp_trend: Optional[float] = None
    ) -> ProtectiveActionRequest:
        """
        Determines the appropriate protective action state based on unified fused risk assessment.
        """
        now = datetime.utcnow()
        now_str = now.isoformat() + "Z"
        prev_state = self._shipment_states.get(shipment_id, ControlStateEnum.NORMAL)
        
        has_primary_alarm = any(e.get("event_type") in ["DOOR_OPEN", "RAPID_WARMING", "SENSOR_DISAGREEMENT"] for e in observed_events)
        is_high_ml_risk = bool(risk_probability is not None and risk_probability >= 0.5750)
        is_critical_ml = bool(risk_probability is not None and risk_probability >= 0.75)
        
        reasons = []
        new_state = prev_state

        if fused_state in ["ERROR", "DEGRADED"]:
            new_state = ControlStateEnum.FAULT
            reasons.append(f"Sensor or telemetry integrity issue detected (State: {fused_state}).")
            action = "INSPECT_SENSOR_MESH"
            power = 65

        elif fused_state == "EVENT_AND_PREDICTED_RISK" or is_critical_ml:
            new_state = ControlStateEnum.PROTECTIVE_ACTION_REQUESTED
            if is_critical_ml:
                reasons.append(f"Critical ML excursion risk forecasted (P = {risk_probability:.4f} >= 0.75).")
            if has_primary_alarm:
                reasons.append("Fast sensor anomaly active (Door open / Rapid thermal rise).")
            action = "MAXIMUM_PROTECTIVE_COOLING_AND_INTERVENTION"
            power = 100

        elif fused_state in ["PREDICTED_RISK", "OBSERVED_EVENT"] or is_high_ml_risk:
            new_state = ControlStateEnum.COOLING_REQUIRED
            if is_high_ml_risk:
                reasons.append(f"Predicted risk elevated above operating threshold (P = {risk_probability:.4f} >= 0.5750).")
            if has_primary_alarm:
                reasons.append("Thermal rate-of-rise exceeded threshold.")
            action = "BOOST_COOLING_POWER"
            power = 85

        elif prev_state in [ControlStateEnum.PROTECTIVE_ACTION_REQUESTED, ControlStateEnum.COOLING_REQUIRED]:
            # Hysteresis check: if conditions normalized, transition to RECOVERY first
            new_state = ControlStateEnum.RECOVERY
            reasons.append("Temperature stabilized within safe corridor following prior excursion risk.")
            action = "MAINTAIN_NOMINAL_COOLING_MONITOR_CORRIDOR"
            power = 70

        else:
            new_state = ControlStateEnum.NORMAL
            reasons.append("Thermal environment stable within optimal cold-chain corridor.")
            action = "MAINTAIN_NOMINAL_OPERATION"
            power = 65

        self._shipment_states[shipment_id] = new_state
        self._state_timestamps[shipment_id] = now

        return ProtectiveActionRequest(
            state=new_state,
            requested_action=action,
            target_temperature_c=4.0,
            cooling_power_level=power,
            reasons=reasons,
            issued_at=now_str,
            is_hardware_controller_connected=False
        )

    def get_current_state(self, shipment_id: str) -> ControlStateEnum:
        return self._shipment_states.get(shipment_id, ControlStateEnum.NORMAL)

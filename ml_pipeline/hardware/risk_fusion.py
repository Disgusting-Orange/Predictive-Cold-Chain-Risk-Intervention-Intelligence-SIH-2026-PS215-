"""
FrostLink Risk Fusion Layer -- Phase 18
========================================
Combines fast observable sensor events with temporal XGBoost v2 predictive risk.

Architecture Hierarchy:
- SENSOR_DROPOUT ───────► DEGRADED
- STALE_TELEMETRY ──────► ERROR / DEGRADED
- DOOR_OPEN ────────────► OBSERVED_EVENT
- RAPID_WARMING ────────► OBSERVED_EVENT
- CORRELATED_WARMING ───► DO NOT ALERT ALONE (Supporting evidence only)
- XGBoost v2 (P >= 0.575) ► PREDICTED_RISK
- Both Event + ML Risk ─► EVENT_AND_PREDICTED_RISK
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from event_detector import ObservedEvent

PRIMARY_ALERT_EVENTS = {"DOOR_OPEN", "RAPID_WARMING", "SENSOR_DISAGREEMENT"}
DEGRADED_EVENTS = {"SENSOR_DROPOUT", "STALE_TELEMETRY"}
SUPPORTING_ONLY_EVENTS = {"CORRELATED_WARMING"}

class MLPredictionSummary(BaseModel):
    model_version: str = "frostlink_xgb_v2"
    risk_probability: float
    threshold: float = 0.5750
    risk_level: str
    prediction_horizon_minutes: int = 60
    is_excursion_predicted: bool
    explanation: Optional[Dict[str, Any]] = None

class FusedRiskAssessment(BaseModel):
    shipment_id: str
    timestamp: str
    fused_state: str = Field(..., description="High-level unified risk state (SAFE, OBSERVED_EVENT, PREDICTED_RISK, EVENT_AND_PREDICTED_RISK, DEGRADED, COLD_START, ERROR)")
    has_observed_events: bool
    has_primary_alarm: bool
    observed_events: List[ObservedEvent] = Field(default_factory=list)
    has_ml_prediction: bool
    ml_prediction: Optional[MLPredictionSummary] = None
    cold_start_status: str
    sensor_health: str
    active_probes_count: int
    door_monitoring_available: bool

class RiskFusionEngine:
    def __init__(self, ml_threshold: float = 0.5750):
        self.ml_threshold = ml_threshold

    def fuse(
        self,
        shipment_id: str,
        timestamp: str,
        observed_events: List[ObservedEvent],
        sensor_meta: Dict[str, Any],
        cold_start_status: str,
        ml_prob: Optional[float] = None,
        ml_level: Optional[str] = None,
        ml_threshold: Optional[float] = None,
        shap_explanation: Optional[Dict[str, Any]] = None
    ) -> FusedRiskAssessment:
        """
        Synthesizes observed events and XGBoost prediction into a structured assessment.
        - Primary events (DOOR_OPEN, RAPID_WARMING) trigger OBSERVED_EVENT.
        - CORRELATED_WARMING acts as supporting evidence only and does NOT alert alone.
        - SENSOR_DROPOUT / STALE_TELEMETRY trigger DEGRADED / ERROR.
        """
        threshold = ml_threshold if ml_threshold is not None else self.ml_threshold
        has_events = len(observed_events) > 0
        has_ml = ml_prob is not None
        sensor_health = sensor_meta.get("sensor_health", "HEALTHY")
        active_count = sensor_meta.get("active_probes_count", 0)
        door_available = sensor_meta.get("door_monitoring_available", False)

        # Categorize events
        primary_events = [e for e in observed_events if e.event_type in PRIMARY_ALERT_EVENTS]
        degraded_events = [e for e in observed_events if e.event_type in DEGRADED_EVENTS]
        has_primary_alarm = len(primary_events) > 0
        has_degraded_alarm = len(degraded_events) > 0

        ml_summary = None
        is_ml_high_risk = False
        if has_ml:
            is_ml_high_risk = bool(ml_prob >= threshold)
            ml_summary = MLPredictionSummary(
                risk_probability=ml_prob,
                threshold=threshold,
                risk_level=ml_level or ("WARNING" if is_ml_high_risk else "SAFE"),
                is_excursion_predicted=is_ml_high_risk,
                explanation=shap_explanation
            )

        # -------------------------------------------------------------
        # Determine Fused Risk State
        # -------------------------------------------------------------
        if sensor_health == "ERROR_ALL_PROBES_MISSING" or cold_start_status == "ERROR":
            fused_state = "ERROR"
        elif has_primary_alarm and is_ml_high_risk:
            fused_state = "EVENT_AND_PREDICTED_RISK"
        elif has_primary_alarm:
            fused_state = "OBSERVED_EVENT"
        elif is_ml_high_risk:
            # XGBoost forecast risk (CORRELATED_WARMING attached as supporting evidence)
            fused_state = "PREDICTED_RISK"
        elif has_degraded_alarm or sensor_health == "DEGRADED":
            fused_state = "DEGRADED"
        elif cold_start_status == "COLD_START":
            fused_state = "COLD_START"
        else:
            # If only CORRELATED_WARMING is present and ML risk < threshold -> SAFE
            fused_state = "SAFE"

        return FusedRiskAssessment(
            shipment_id=shipment_id,
            timestamp=timestamp,
            fused_state=fused_state,
            has_observed_events=has_events,
            has_primary_alarm=has_primary_alarm,
            observed_events=observed_events,
            has_ml_prediction=has_ml,
            ml_prediction=ml_summary,
            cold_start_status=cold_start_status,
            sensor_health=sensor_health,
            active_probes_count=active_count,
            door_monitoring_available=door_available
        )

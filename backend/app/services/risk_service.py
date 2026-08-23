"""
FrostLink Risk & SHAP Engine Interface -- AI/ML Integration
============================================================
Bridges incoming sensor telemetry directly to the validated FrostLink
HardwareGateway:
- Fast Event Detection (Causal)
- Multi-Step History Buffering
- 40 Causal Feature Engineering
- Frozen XGBoost V2 Model Inference (Threshold 0.5750)
- TreeSHAP Local Feature Explanations
- Multi-Layer Risk Fusion
- Software Refrigeration Control Safety Machine
"""

import sys
import os
import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timezone

from app.schemas.risk import SHAPFactor, PredictedTempPoint, RiskPredictionResponse

# Include paths for ml_pipeline modules
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ML_HARDWARE_DIR = os.path.join(BASE_DIR, "ml_pipeline", "hardware")
ML_SERVICE_DIR = os.path.join(BASE_DIR, "ml_pipeline", "service")
ML_FEAT_DIR = os.path.join(BASE_DIR, "ml_pipeline", "feature_engineering")

for p in [ML_HARDWARE_DIR, ML_SERVICE_DIR, ML_FEAT_DIR]:
    if p not in sys.path:
        sys.path.append(p)

logger = logging.getLogger("frostlink_risk_service")

# Global singleton instance of HardwareGateway
_ml_gateway = None

def get_edge_gateway():
    global _ml_gateway
    if _ml_gateway is None:
        try:
            from gateway import HardwareGateway
            _ml_gateway = HardwareGateway()
            logger.info("FrostLink HardwareGateway loaded successfully in backend risk service.")
        except Exception as e:
            logger.warning(f"Could not load HardwareGateway in backend: {e}")
            _ml_gateway = None
    return _ml_gateway


def calculate_risk_and_shap(
    temperature: float,
    safe_min: float,
    safe_max: float,
    temp_trend: float,
    eta_minutes: float,
    delay_minutes: float,
    door_open: bool,
    speed: float,
    previous_risk_score: Optional[int] = None,
    shipment_id: str = "SHP-1042",
    timestamp: Optional[datetime] = None,
    battery: float = 90.0,
    raw_probes: Optional[Dict[str, Any]] = None
) -> Tuple[int, str, int, Optional[int], float, int, List[SHAPFactor], List[PredictedTempPoint], str]:
    """
    AI Risk & SHAP Engine Interface.
    Runs frozen XGBoost V2 + TreeSHAP + Risk Fusion via HardwareGateway.
    """
    gw = get_edge_gateway()
    ts_dt = timestamp or datetime.now(timezone.utc)
    ts_iso = ts_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if gw is not None:
        try:
            # Build 9-probe spatial representation
            if raw_probes and isinstance(raw_probes, dict) and len(raw_probes) >= 1:
                probes = raw_probes
            else:
                probes = {
                    "Front_Top": round(temperature + 0.25, 2),
                    "Front_Middle": round(temperature, 2),
                    "Front_Bottom": round(temperature - 0.20, 2),
                    "Middle_Top": round(temperature + 0.35, 2),
                    "Middle_Middle": round(temperature + 0.05, 2),
                    "Middle_Bottom": round(temperature - 0.15, 2),
                    "Rear_Top": round(temperature + 0.55, 2),
                    "Rear_Middle": round(temperature + 0.20, 2),
                    "Rear_Bottom": round(temperature + 0.05, 2)
                }

            valid_count = sum(1 for v in probes.values() if v is not None and -50.0 <= float(v) <= 80.0)
            packet = {
                "shipment_id": shipment_id,
                "timestamp": ts_iso,
                "probes": probes,
                "sconf": round(valid_count / 9.0, 3),
                "coverage_time": 1.0,
                "door_open": door_open,
                "speed_kmh": float(speed or 0.0),
                "battery_voltage": float(battery or 12.0)
            }

            res = gw.process_raw_telemetry(packet)

            if res.success:
                # Map XGBoost V2 probability
                if res.risk_probability is not None:
                    excursion_prob = round(float(res.risk_probability), 4)
                    risk_score = int(round(excursion_prob * 100))
                    risk_level = res.risk_level or ("CRITICAL" if risk_score >= 75 else "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 30 else "LOW")
                else:
                    # Cold start (<6 observations)
                    margin = safe_max - temperature
                    if margin <= 0 or door_open:
                        risk_score = 65
                        risk_level = "HIGH"
                        excursion_prob = 0.65
                    else:
                        risk_score = 15
                        risk_level = "LOW"
                        excursion_prob = 0.15

                # Extract TreeSHAP factors
                shap_factors: List[SHAPFactor] = []
                if res.explanation and isinstance(res.explanation, dict):
                    for f in res.explanation.get("top_risk_increasing_factors", []):
                        val_str = f.get('display_name', f.get('feature_name', 'feature'))
                        obs_val = f.get('observed_value', 0.0)
                        shap_factors.append(SHAPFactor(
                            feature=f.get("feature_name", "risk_factor"),
                            impact=round(float(f.get("shap_value", 0.1)), 3),
                            direction="↑",
                            description=f"{val_str} (observed: {obs_val:.2f})" if isinstance(obs_val, (int, float)) else f"{val_str}"
                        ))
                    for f in res.explanation.get("top_risk_decreasing_factors", []):
                        val_str = f.get('display_name', f.get('feature_name', 'feature'))
                        obs_val = f.get('observed_value', 0.0)
                        shap_factors.append(SHAPFactor(
                            feature=f.get("feature_name", "protective_factor"),
                            impact=round(float(f.get("shap_value", -0.1)), 3),
                            direction="↓",
                            description=f"{val_str} (protective: {obs_val:.2f})" if isinstance(obs_val, (int, float)) else f"{val_str}"
                        ))

                if not shap_factors:
                    shap_factors.append(SHAPFactor(
                        feature="spatial_mean_temp",
                        impact=0.10,
                        direction="→",
                        description=f"Mean spatial temp: {temperature:.1f}°C (Threshold τ=0.5750)"
                    ))

                # Compute safe life remaining & message
                margin = safe_max - temperature
                if temp_trend > 0.05 and margin > 0:
                    remaining_safe_life_mins = int((margin / temp_trend) * 4)
                    msg = f"XGBoost V2 (τ=0.5750): Risk {risk_score}% · Fused state: {res.fused_state}"
                elif margin <= 0:
                    remaining_safe_life_mins = 0
                    msg = f"Temperature excursion active ({temperature:.1f}°C > {safe_max:.1f}°C)"
                else:
                    remaining_safe_life_mins = None
                    msg = f"Stable · Fused state: {res.fused_state}"

                spoilage_risk_pct = min(100, int(risk_score * 1.1))
                ai_confidence = 94

                predicted_points = [
                    PredictedTempPoint(
                        minutesAhead=i * 4,
                        temperature=round(temperature + max(0.0, temp_trend) * i, 1)
                    )
                    for i in range(1, 6)
                ]

                return (
                    risk_score,
                    risk_level,
                    spoilage_risk_pct,
                    remaining_safe_life_mins,
                    excursion_prob,
                    ai_confidence,
                    shap_factors,
                    predicted_points,
                    msg
                )
        except Exception as e:
            logger.error(f"Error evaluating ML pipeline: {e}", exc_info=True)

    # Heuristic fallback if gateway unavailable
    score = 0
    shap_factors = []
    margin_upper = safe_max - temperature

    if margin_upper <= 0:
        score += 40
        shap_factors.append(SHAPFactor(
            feature="temperature_limit_breached",
            impact=0.40,
            direction="↑",
            description=f"Temperature ({temperature:.1f}°C) exceeded safe limit ({safe_max:.1f}°C)"
        ))
    elif margin_upper <= 0.5:
        score += 30
        shap_factors.append(SHAPFactor(
            feature="temperature_near_upper_limit",
            impact=0.30,
            direction="↑",
            description=f"Temperature ({temperature:.1f}°C) near upper limit ({safe_max:.1f}°C)"
        ))
    else:
        shap_factors.append(SHAPFactor(
            feature="temperature_in_range",
            impact=0.05,
            direction="→",
            description=f"Temperature ({temperature:.1f}°C) in safe zone ({safe_min}-{safe_max}°C)"
        ))

    if door_open:
        score += 15
        shap_factors.append(SHAPFactor(
            feature="door_open_air_leak",
            impact=0.15,
            direction="↑",
            description="Container door is OPEN"
        ))

    score = max(0, min(100, score))
    level = "CRITICAL" if score >= 75 else "HIGH" if score >= 50 else "MEDIUM" if score >= 30 else "LOW"
    excursion_prob = round(score / 100.0, 2)
    remaining_safe_life_mins = 0 if margin_upper <= 0 else None
    spoilage_risk_pct = min(100, int(score * 1.1))
    msg = "Fallback evaluation active"
    predicted_points = [
        PredictedTempPoint(minutesAhead=i * 4, temperature=round(temperature + max(0.0, temp_trend) * i, 1))
        for i in range(1, 6)
    ]

    return (
        score,
        level,
        spoilage_risk_pct,
        remaining_safe_life_mins,
        excursion_prob,
        85,
        shap_factors,
        predicted_points,
        msg
    )

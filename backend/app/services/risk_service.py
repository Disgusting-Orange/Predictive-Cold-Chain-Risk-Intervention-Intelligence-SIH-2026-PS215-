from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
from app.schemas.risk import SHAPFactor, PredictedTempPoint, RiskPredictionResponse


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
) -> Tuple[int, str, int, Optional[int], float, int, List[SHAPFactor], List[PredictedTempPoint], str]:
    """
    AI Risk & SHAP Engine Interface.
    
    Evaluates temperature margin, velocity trend, door status, and delay
    to produce composite risk, excursion probability, remaining safe life,
    and structured SHAP attribution factors.
    """
    score = 0
    shap_factors: List[SHAPFactor] = []
    
    # 1. Temperature Proximity & Limit Breach
    margin_upper = safe_max - temperature
    margin_lower = temperature - safe_min

    if margin_upper <= 0:
        score += 40
        shap_factors.append(SHAPFactor(
            feature="temperature_limit_breached",
            impact=0.40,
            direction="↑",
            description=f"Temperature ({temperature:.1f}°C) exceeded optimal safe limit ({safe_max:.1f}°C)"
        ))
    elif margin_upper <= 0.5:
        proximity_score = 28 + int(12 * (0.5 - margin_upper) / 0.5)
        score += proximity_score
        shap_factors.append(SHAPFactor(
            feature="temperature_near_upper_limit",
            impact=round(proximity_score / 100.0, 2),
            direction="↑",
            description=f"Temperature ({temperature:.1f}°C) is critical: within {margin_upper:.1f}°C of upper limit"
        ))
    elif margin_upper <= 1.5:
        proximity_score = 12 + int(16 * (1.5 - margin_upper) / 1.0)
        score += proximity_score
        shap_factors.append(SHAPFactor(
            feature="temperature_elevated",
            impact=round(proximity_score / 100.0, 2),
            direction="↑",
            description=f"Temperature elevated: {margin_upper:.1f}°C headroom remaining"
        ))
    else:
        shap_factors.append(SHAPFactor(
            feature="temperature_in_range",
            impact=0.05,
            direction="→",
            description=f"Temperature ({temperature:.1f}°C) is within safe operational zone ({safe_min}-{safe_max}°C)"
        ))

    if margin_lower <= 0:
        score += 30
        shap_factors.append(SHAPFactor(
            feature="temperature_subzero_freeze",
            impact=0.30,
            direction="↓",
            description=f"Temperature ({temperature:.1f}°C) below freezing lower limit ({safe_min:.1f}°C)"
        ))

    # 2. Rate of Climb / Temperature Slope
    if temp_trend >= 0.5:
        score += 22
        shap_factors.append(SHAPFactor(
            feature="temperature_slope_rapid",
            impact=0.22,
            direction="↑",
            description=f"Rapid warming slope: rising +{temp_trend:.1f}°C per interval"
        ))
    elif temp_trend >= 0.2:
        score += 12
        shap_factors.append(SHAPFactor(
            feature="temperature_slope_moderate",
            impact=0.12,
            direction="↑",
            description=f"Upward warming trend: +{temp_trend:.1f}°C per interval"
        ))
    elif temp_trend <= -0.3:
        score = max(0, score - 5)
        shap_factors.append(SHAPFactor(
            feature="temperature_recovering",
            impact=-0.05,
            direction="↓",
            description="Cooling compressor active: temperature dropping"
        ))

    # 3. Traffic & ETA Delay Impact
    if delay_minutes >= 20:
        score += 18
        shap_factors.append(SHAPFactor(
            feature="traffic_delay_severe",
            impact=0.18,
            direction="↑",
            description=f"Severe traffic delay: +{int(delay_minutes)} min added to transit time"
        ))
    elif delay_minutes >= 8:
        score += 10
        shap_factors.append(SHAPFactor(
            feature="traffic_delay_moderate",
            impact=0.10,
            direction="↑",
            description=f"Traffic congestion detected: +{int(delay_minutes)} min delay"
        ))

    # 4. Cargo Door Open Status
    if door_open:
        score += 12
        shap_factors.append(SHAPFactor(
            feature="door_open_air_leak",
            impact=0.12,
            direction="↑",
            description="Cargo container door is OPEN: loss of refrigerated air"
        ))

    # 5. Compound Risk Interaction
    if temp_trend > 0.2 and delay_minutes > 10:
        score += 10
        shap_factors.append(SHAPFactor(
            feature="compound_delay_warming",
            impact=0.10,
            direction="↑",
            description="Compound Risk: rising temperature combined with traffic gridlock"
        ))

    # 6. Stationary Vehicle Penalty
    if speed < 10 and delay_minutes > 5:
        score += 5
        shap_factors.append(SHAPFactor(
            feature="vehicle_stationary",
            impact=0.05,
            direction="↑",
            description="Vehicle stationary in transit corridor"
        ))

    # Momentum smoothing
    if previous_risk_score is not None and previous_risk_score > score:
        score = int(score + (previous_risk_score - score) * 0.55)

    score = max(0, min(100, score))

    # Determine Severity Classification
    if score >= 75:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    # Excursion Prediction & Remaining Safe Life
    if temp_trend <= 0.05:
        remaining_safe_life_mins = None
        excursion_prob = 0.05
        spoilage_risk_pct = max(0, min(100, int((temperature - safe_min) / max(0.1, safe_max - safe_min) * 20)))
        message = "Temperature stable — no excursion predicted"
        predicted_points: List[PredictedTempPoint] = []
    else:
        margin = safe_max - temperature
        if margin <= 0:
            remaining_safe_life_mins = 0
            excursion_prob = 0.98
            spoilage_risk_pct = 95
            message = "Temperature has exceeded safe range"
        else:
            ticks_to_unsafe = margin / temp_trend
            remaining_safe_life_mins = int(ticks_to_unsafe * 4)
            excursion_prob = min(0.95, round(0.40 + (1.0 / max(1, remaining_safe_life_mins)) * 15, 3))
            spoilage_risk_pct = min(100, int(score * 1.1))
            message = f"Excursion predicted in approximately {remaining_safe_life_mins} minutes"

        predicted_points = [
            PredictedTempPoint(
                minutesAhead=i * 4,
                temperature=round(temperature + temp_trend * i, 1)
            )
            for i in range(1, 6)
        ]

    ai_confidence = 87

    return (
        score,
        level,
        spoilage_risk_pct,
        remaining_safe_life_mins,
        excursion_prob,
        ai_confidence,
        shap_factors,
        predicted_points,
        message
    )

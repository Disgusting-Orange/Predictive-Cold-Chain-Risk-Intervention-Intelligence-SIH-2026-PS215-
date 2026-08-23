"""
Prototype Rule-Based Risk Engine
================================
Explainable, rule-based risk scoring for cold-chain shipments.
Evaluates telemetry factors to produce a composite risk score (0-100)
with contributing factor explanations.

NOTE: This is a prototype implementation. In production, this module
would be replaced or augmented with a trained ML model while
preserving the same interface.
"""

from typing import List, Tuple, Dict, Optional


def calculate_risk(
    temperature: float,
    safe_min: float,
    safe_max: float,
    temp_trend: float,
    eta_minutes: float,
    delay_minutes: float,
    door_open: bool,
    speed: float,
    previous_risk_score: Optional[int] = None,
) -> Tuple[int, str, List[Dict[str, str]]]:
    """
    Calculate risk score based on current telemetry.

    Returns:
        Tuple of (risk_score: 0-100, risk_level: str, contributing_factors: list)
    """
    score = 0
    factors = []

    # --- Factor 1: Temperature proximity to safe limit ---
    margin_upper = safe_max - temperature
    margin_lower = temperature - safe_min

    if margin_upper <= 0:
        score += 40
        factors.append({
            "direction": "↑",
            "description": "Temperature exceeds safe range"
        })
    elif margin_upper <= 0.5:
        proximity_score = 28 + int(12 * (0.5 - margin_upper) / 0.5)
        score += proximity_score
        factors.append({
            "direction": "↑",
            "description": "Approaching safe-temperature limit"
        })
    elif margin_upper <= 1.5:
        proximity_score = 12 + int(16 * (1.5 - margin_upper) / 1.0)
        score += proximity_score
        factors.append({
            "direction": "↑",
            "description": "Temperature elevated within range"
        })
    elif margin_upper <= 3.0:
        proximity_score = int(12 * (3.0 - margin_upper) / 1.5)
        score += proximity_score
        if proximity_score > 3:
            factors.append({
                "direction": "→",
                "description": "Temperature within normal range"
            })

    if margin_lower <= 0:
        score += 30
        factors.append({
            "direction": "↓",
            "description": "Temperature below safe range"
        })
    elif margin_lower <= 0.5:
        score += 10
        factors.append({
            "direction": "↓",
            "description": "Temperature near lower limit"
        })

    # --- Factor 2: Temperature trend ---
    if temp_trend >= 0.5:
        score += 22
        factors.append({
            "direction": "↑",
            "description": "Rapid temperature increase"
        })
    elif temp_trend >= 0.2:
        score += 12
        factors.append({
            "direction": "↑",
            "description": "Temperature gradually increasing"
        })
    elif temp_trend <= -0.3:
        score = max(0, score - 5)
        factors.append({
            "direction": "↓",
            "description": "Temperature decreasing (recovering)"
        })
    else:
        factors.append({
            "direction": "→",
            "description": "Temperature stable"
        })

    # --- Factor 3: Delay impact ---
    if delay_minutes >= 20:
        score += 18
        factors.append({
            "direction": "↑",
            "description": f"{int(delay_minutes)}-minute traffic delay"
        })
    elif delay_minutes >= 10:
        score += 10
        factors.append({
            "direction": "↑",
            "description": f"{int(delay_minutes)}-minute delay detected"
        })
    elif delay_minutes >= 5:
        score += 5
        factors.append({
            "direction": "↑",
            "description": f"{int(delay_minutes)}-minute minor delay"
        })

    # --- Factor 4: Door status ---
    if door_open:
        score += 12
        factors.append({
            "direction": "↑",
            "description": "Cargo door open — loss of cold air"
        })
    else:
        factors.append({
            "direction": "→",
            "description": "Door currently closed"
        })

    # --- Factor 5: Compound risk ---
    if temp_trend > 0.2 and delay_minutes > 10:
        score += 10
        factors.append({
            "direction": "↑",
            "description": "Compound risk: rising temperature with significant delay"
        })

    # --- Factor 6: Vehicle speed ---
    if speed < 10 and delay_minutes > 5:
        score += 5
        factors.append({
            "direction": "↑",
            "description": "Vehicle nearly stationary"
        })

    # --- Risk momentum (gradual decay for realistic behaviour) ---
    if previous_risk_score is not None and previous_risk_score > score:
        decay_factor = 0.55
        score = int(score + (previous_risk_score - score) * decay_factor)

    # Clamp to 0-100
    score = max(0, min(100, score))

    # Determine risk level
    if score >= 75:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score, level, factors


def predict_excursion(
    current_temp: float,
    temp_trend: float,
    safe_max: float,
    safe_min: float,
) -> Dict:
    """
    Predict temperature excursion based on current trend.
    Uses simple linear extrapolation — prototype predictive analytics.
    """
    if temp_trend <= 0.05:
        return {
            "excursionRisk": max(0, min(100, int(
                (current_temp - safe_min) / (safe_max - safe_min) * 30
            ))),
            "timeToUnsafe": None,
            "temperatureTrend": round(temp_trend, 2),
            "message": "Temperature stable — no excursion predicted",
            "predictedTemperatures": [],
        }

    # Estimate time to threshold crossing
    margin = safe_max - current_temp
    if margin <= 0:
        time_to_unsafe = 0
    else:
        # temp_trend is per tick (~4 simulated minutes per tick)
        ticks_to_unsafe = margin / temp_trend
        time_to_unsafe = int(ticks_to_unsafe * 4)

    # Calculate excursion risk percentage
    if time_to_unsafe == 0:
        excursion_risk = 95
    elif time_to_unsafe <= 10:
        excursion_risk = 90
    elif time_to_unsafe <= 20:
        excursion_risk = 82
    elif time_to_unsafe <= 32:
        excursion_risk = 72
    elif time_to_unsafe <= 45:
        excursion_risk = 55
    else:
        excursion_risk = 35

    # Generate predicted future temperatures (for chart overlay)
    predicted = []
    for i in range(1, 6):
        future_temp = current_temp + temp_trend * i
        predicted.append({
            "minutesAhead": i * 4,
            "temperature": round(future_temp, 1),
        })

    if time_to_unsafe is not None and time_to_unsafe > 0:
        message = (
            f"Temperature excursion predicted in approximately "
            f"{time_to_unsafe} minutes"
        )
    elif time_to_unsafe == 0:
        message = "Temperature has exceeded safe range"
    else:
        message = "Temperature trend being monitored"

    return {
        "excursionRisk": excursion_risk,
        "timeToUnsafe": time_to_unsafe,
        "temperatureTrend": round(temp_trend, 2),
        "message": message,
        "predictedTemperatures": predicted,
    }

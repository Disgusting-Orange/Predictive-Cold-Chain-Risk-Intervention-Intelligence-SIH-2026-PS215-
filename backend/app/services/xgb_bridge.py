"""Optional FrostLink XGBoost bridge for the main telemetry pipeline.

The device sends raw readings. This adapter derives the 40 features required by
the packaged model from the shipment's recent telemetry window. It intentionally
keeps the heuristic scorer available as a fallback while the model is validated.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.schemas.risk import PredictedTempPoint, SHAPFactor


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = ROOT / "ml_pipeline" / "model_artifacts" / "frostlink_xgb_v2"
SCHEMA_PATH = ARTIFACT_DIR / "feature_schema.json"
MODEL_PATH = ARTIFACT_DIR / "model.json"
THRESHOLD_PATH = ARTIFACT_DIR / "threshold.json"
METADATA_PATH = ARTIFACT_DIR / "model_metadata.json"


@dataclass
class XGBoostRiskResult:
    risk_score: int
    risk_level: str
    spoilage_risk_pct: int
    remaining_safe_life: int | None
    excursion_prob: float
    ai_confidence: int
    shap_factors: list[SHAPFactor]
    predicted_points: list[PredictedTempPoint]
    message: str
    model_version: str


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _minutes_between(first: Any, last: Any) -> float:
    if not first or not last:
        return 1.0
    if getattr(first, "tzinfo", None) is None:
        first = first.replace(tzinfo=timezone.utc)
    if getattr(last, "tzinfo", None) is None:
        last = last.replace(tzinfo=timezone.utc)
    return max(1.0, (last - first).total_seconds() / 60.0)


def build_feature_vector(readings: Iterable[Any], current_temperature: float, safe_min: float, safe_max: float) -> dict[str, float]:
    """Build the ordered FrostLink feature dictionary from raw telemetry.

    A single ESP32 probe has no spatial distribution. Spatial features therefore
    use zero spread and a one-probe coverage ratio until multi-probe hardware is
    available. This is explicit and deterministic, not a fabricated measurement.
    """
    rows = list(readings)
    rows.append(type("CurrentReading", (), {"temperature": current_temperature, "timestamp": datetime.now(timezone.utc)})())
    rows.sort(key=lambda row: getattr(row, "timestamp", datetime.now(timezone.utc)))
    temperatures = [_number(getattr(row, "temperature", current_temperature), current_temperature) for row in rows]
    now = rows[-1]
    now_temp = temperatures[-1]

    def window(minutes: float) -> list[tuple[Any, float]]:
        result = []
        for row, temp in zip(rows, temperatures):
            if _minutes_between(getattr(row, "timestamp", None), getattr(now, "timestamp", None)) <= minutes:
                result.append((row, temp))
        return result or [(now, now_temp)]

    w60 = window(60.0)
    w10 = window(10.0)
    w60_temps = [temp for _, temp in w60]
    first_row, first_temp = w60[0]
    last_row, last_temp = w60[-1]
    w60_minutes = _minutes_between(getattr(first_row, "timestamp", None), getattr(last_row, "timestamp", None))
    delta = last_temp - first_temp
    slope = delta / w60_minutes
    short_delta = w10[-1][1] - w10[0][1]
    short_minutes = _minutes_between(getattr(w10[0][0], "timestamp", None), getattr(w10[-1][0], "timestamp", None))
    short_slope = short_delta / short_minutes
    median = sorted(w60_temps)[len(w60_temps) // 2]
    sorted_temps = sorted(w60_temps)
    q1 = sorted_temps[max(0, int((len(sorted_temps) - 1) * 0.25))]
    q3 = sorted_temps[min(len(sorted_temps) - 1, int((len(sorted_temps) - 1) * 0.75))]
    hot = [1.0 if temp > safe_max else 0.0 for temp in w60_temps]
    cold = [1.0 if temp < safe_min else 0.0 for temp in w60_temps]
    over = [max(0.0, temp - safe_max) for temp in w60_temps]
    under = [max(0.0, safe_min - temp) for temp in w60_temps]
    interval = w60_minutes / max(1, len(w60_temps) - 1)
    over_auc = sum(over) * interval
    under_auc = sum(under) * interval
    max_step = max((abs(b - a) for a, b in zip(w60_temps, w60_temps[1:])), default=0.0)
    long_slope = slope
    acceleration = (short_slope - long_slope) / max(1.0, w60_minutes)

    features = {
        "T_mean_t": now_temp, "spatial_range_t": 0.0, "spatial_std_t": 0.0,
        "hot_ratio_t": hot[-1], "cold_ratio_t": cold[-1], "mask_ratio_t": 1.0,
        "W60_T_mean": sum(w60_temps) / len(w60_temps),
        "W60_T_std": math.sqrt(sum((temp - sum(w60_temps) / len(w60_temps)) ** 2 for temp in w60_temps) / len(w60_temps)),
        "W60_T_min": min(w60_temps), "W60_T_max": max(w60_temps), "W60_T_range": max(w60_temps) - min(w60_temps),
        "W60_delta": delta, "W60_slope": slope, "W60_spatial_range_mean": 0.0, "W60_spatial_range_max": 0.0,
        "W60_spatial_std_mean": 0.0, "W60_hot_ratio_mean": sum(hot) / len(hot), "W60_hot_ratio_max": max(hot),
        "W60_over_auc_mean": over_auc / len(w60_temps), "W60_over_auc_max": over_auc,
        "W60_under_auc_mean": under_auc / len(w60_temps), "W60_under_auc_max": under_auc,
        "W60_over_dur_mean": sum(1 for value in over if value > 0) * interval / len(w60_temps),
        "W60_under_dur_mean": sum(1 for value in under if value > 0) * interval / len(w60_temps),
        "v4_slope_short_t": short_slope, "v4_slope_long_t": long_slope, "v4_accel_t": acceleration,
        "v4_shock_t": max_step, "v4_median_t": median, "v4_iqr_t": q3 - q1,
        "v4_p90_t": sorted_temps[min(len(sorted_temps) - 1, int((len(sorted_temps) - 1) * 0.90))],
        "v4_p95_t": sorted_temps[min(len(sorted_temps) - 1, int((len(sorted_temps) - 1) * 0.95))],
        "v4_over_auc_t": max(0.0, now_temp - safe_max), "v4_under_auc_t": max(0.0, safe_min - now_temp),
        "v4_over_max_t": max(over), "v4_under_max_t": max(under),
        "sconf": 1.0, "coverage_points": float(len(w60_temps)), "coverage_time": w60_minutes, "N_valid": float(len(w60_temps)),
    }
    return features


class FrostLinkXGBoost:
    _instance: "FrostLinkXGBoost | None" = None

    def __init__(self):
        import xgboost as xgb

        self.xgb = xgb
        self.feature_names = [item["feature_name"] for item in sorted(json.loads(SCHEMA_PATH.read_text())["features"], key=lambda item: item["feature_order"])]
        self.threshold = float(json.loads(THRESHOLD_PATH.read_text()).get("operating_threshold", 0.575))
        self.model_version = json.loads(METADATA_PATH.read_text()).get("model_version", "frostlink_xgb_v2")
        self.model = xgb.XGBClassifier()
        self.model.load_model(str(MODEL_PATH))

    @classmethod
    def instance(cls) -> "FrostLinkXGBoost":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def predict(self, features: dict[str, float], temperature: float, temp_trend: float, safe_max: float) -> XGBoostRiskResult:
        vector = [[features[name] for name in self.feature_names]]
        matrix = self.xgb.DMatrix(vector, feature_names=self.feature_names)
        probability = float(self.model.get_booster().predict(matrix)[0])
        contributions = self.model.get_booster().predict(matrix, pred_contribs=True)[0][:-1]
        if probability >= 0.75:
            level = "CRITICAL"
        elif probability >= self.threshold:
            level = "HIGH"
        elif probability >= 0.20:
            level = "MEDIUM"
        else:
            level = "LOW"
        factors = [
            SHAPFactor(feature=name, impact=round(float(value), 4), direction="↑" if value > 0 else "↓", description=f"{name} contribution from FrostLink XGBoost")
            for name, value in sorted(zip(self.feature_names, contributions), key=lambda item: abs(item[1]), reverse=True)[:6]
        ]
        remaining = int((safe_max - temperature) / temp_trend) if temp_trend > 0 and temperature < safe_max else (0 if temperature >= safe_max else None)
        return XGBoostRiskResult(
            risk_score=round(probability * 100), risk_level=level, spoilage_risk_pct=round(probability * 100),
            remaining_safe_life=remaining, excursion_prob=probability, ai_confidence=round(max(probability, 1 - probability) * 100),
            shap_factors=factors, predicted_points=[], message="FrostLink XGBoost prediction generated", model_version=self.model_version,
        )

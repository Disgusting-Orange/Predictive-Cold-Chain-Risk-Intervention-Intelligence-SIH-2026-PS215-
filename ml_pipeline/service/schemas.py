"""
FrostLink ML Inference Service -- Data Schemas
==============================================
Pydantic v2 data models for API request, response, error handling, and SHAP explainability.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import math

class RiskLevelEnum(str, Enum):
    SAFE = "SAFE"
    ELEVATED = "ELEVATED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class ExplanationFactor(BaseModel):
    feature_name: str = Field(..., description="Machine-readable feature key")
    display_name: str = Field(..., description="Human-readable feature name")
    observed_value: Optional[float] = Field(None, description="Observed input value (null if missing/NaN)")
    unit: str = Field("", description="Physical measurement unit")
    shap_value: float = Field(..., description="Exact SHAP impact on model log-odds margin")
    feature_group: str = Field("thermal", description="Functional feature category")

class SHAPExplanation(BaseModel):
    top_risk_increasing_factors: List[ExplanationFactor] = Field(default_factory=list, description="Top factors pushing risk higher")
    top_risk_reducing_factors: List[ExplanationFactor] = Field(default_factory=list, description="Top factors mitigating risk")

class PredictionRequest(BaseModel):
    shipment_id: str = Field(..., min_length=1, description="Unique journey or shipment identifier", example="SHIP_0492_A")
    timestamp: str = Field(..., description="ISO-8601 observation timestamp", example="2026-08-23T14:30:00Z")
    features: Dict[str, Any] = Field(..., description="Dictionary containing the 40 schema-defined features")

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            # Handle ISO datetime with or without Z
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO-8601 timestamp format: '{v}'. Error: {e}")
        return v

    @field_validator("features")
    @classmethod
    def validate_feature_values(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("Features payload must be a JSON object / dictionary.")
        
        cleaned_features = {}
        for key, val in v.items():
            if val is None:
                cleaned_features[key] = None
                continue
            try:
                val_float = float(val)
                if math.isinf(val_float):
                    raise ValueError(f"Feature '{key}' contains infinite value, which is not permitted.")
                cleaned_features[key] = val_float
            except (ValueError, TypeError) as e:
                raise ValueError(f"Feature '{key}' must be numeric (float64) or null. Received: '{val}'")
        return cleaned_features

class PredictionResponse(BaseModel):
    model_version: str = Field(..., example="1.0.0")
    risk_probability: float = Field(..., ge=0.0, le=1.0, description="Continuous estimated excursion probability in next 60m", example=0.482)
    risk_level: RiskLevelEnum = Field(..., description="Business risk category", example=RiskLevelEnum.WARNING)
    threshold: float = Field(..., description="Data-driven alert threshold applied", example=0.461)
    prediction_horizon_minutes: int = Field(60, description="Forward early-warning lookahead horizon in minutes", example=60)
    explanation: SHAPExplanation

class HealthResponse(BaseModel):
    status: str = Field("HEALTHY", example="HEALTHY")
    service_name: str = Field(..., example="FrostLink ML Inference Service")
    service_version: str = Field(..., example="1.0.0")
    model_version: str = Field(..., example="1.0.0")
    feature_schema_version: str = Field(..., example="1.0.0")
    artifact_integrity_verified: bool = Field(..., example=True)
    uptime_seconds: float = Field(..., example=124.5)

class ErrorResponse(BaseModel):
    error: str = Field(..., example="Validation Error")
    detail: str = Field(..., example="Missing required features: ['T_mean_t']")
    error_code: str = Field(..., example="INVALID_INPUT")

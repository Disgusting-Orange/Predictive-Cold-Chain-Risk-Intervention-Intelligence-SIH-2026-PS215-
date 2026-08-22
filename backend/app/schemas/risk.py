from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SHAPFactor(BaseModel):
    feature: str
    impact: float
    direction: str  # "↑", "↓", "→"
    description: str


class PredictedTempPoint(BaseModel):
    minutesAhead: int
    temperature: float


class RiskPredictionResponse(BaseModel):
    shipmentId: str
    timestamp: datetime
    riskScore: int  # 0-100
    riskLevel: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    spoilageRiskPercent: int
    remainingSafeLifeMinutes: Optional[int]
    excursionProbability: Optional[float]
    aiConfidencePercent: int
    temperatureTrend: float
    message: str
    shapFactors: List[SHAPFactor]
    predictedTemperatures: List[PredictedTempPoint]
    modelVersion: str = "xgb_v1.0"

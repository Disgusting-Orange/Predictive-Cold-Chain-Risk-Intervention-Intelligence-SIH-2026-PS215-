from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class WhatIfScenario(BaseModel):
    id: str
    scenarioName: str
    action: str
    destination: str
    etaMinutes: int
    predictedRisk: int
    projectedLoss: float
    remainingSafeLife: str
    isRecommended: bool


class WhatIfSimulationResponse(BaseModel):
    shipmentId: str
    scenarios: List[WhatIfScenario]
    estimatedLossWithoutIntervention: float
    estimatedLossWithIntervention: float
    potentialLossAvoided: float
    recommendedAction: str


class InterventionApproveRequest(BaseModel):
    action: Optional[str] = None


class InterventionOverrideRequest(BaseModel):
    overrideReason: str


class HandoffRequest(BaseModel):
    handoffPhotoUrl: Optional[str] = None
    notes: Optional[str] = None
    facilityId: Optional[str] = None


class InterventionResponse(BaseModel):
    id: UUID
    shipmentId: str
    recommendedAction: str
    targetFacilityName: Optional[str]
    riskBefore: int
    riskAfter: int
    etaBefore: int
    etaAfter: int
    potentialLossAvoided: float
    status: str
    reason: str
    createdAt: datetime

    class Config:
        from_attributes = True

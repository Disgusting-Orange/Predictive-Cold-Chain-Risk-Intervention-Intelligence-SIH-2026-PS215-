from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertResponse(BaseModel):
    id: str
    shipmentId: str
    severity: str  # "INFO", "MEDIUM", "HIGH", "CRITICAL"
    alertType: str
    message: str
    isResolved: bool
    createdAt: datetime
    resolvedAt: Optional[datetime] = None

    class Config:
        from_attributes = True

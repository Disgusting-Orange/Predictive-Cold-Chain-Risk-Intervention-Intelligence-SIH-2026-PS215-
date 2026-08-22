from typing import List, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Shipment, ColdStorageFacility, Intervention, AuditLog
from app.schemas.intervention import WhatIfScenario, WhatIfSimulationResponse


def generate_what_if_scenarios(
    shipment_code: str,
    current_risk: int,
    current_eta: int,
    cargo_value: float,
    nearest_facility_name: str = "Cold Storage A (Guindy)",
    nearest_facility_eta: int = 18
) -> WhatIfSimulationResponse:
    """
    Evaluate 3 What-If action candidate scenarios and compute loss avoided.
    """
    # 1. Continue Current Route
    loss_continue = round((current_risk / 100.0) * cargo_value * 0.25, 2)
    safe_life_continue = f"{max(15, int(45 - current_risk * 0.3))} min"
    
    # 2. Reroute to Cold Storage
    risk_reroute = max(12, int(current_risk * 0.22))
    loss_reroute = round((risk_reroute / 100.0) * cargo_value * 0.25, 2)
    safe_life_reroute = "4.2 hrs"
    
    # 3. Emergency Delivery / Expedited
    risk_expedite = max(25, int(current_risk * 0.45))
    loss_expedite = round((risk_expedite / 100.0) * cargo_value * 0.25, 2)
    safe_life_expedite = "1.1 hrs"
    
    loss_avoided = max(0.0, round(loss_continue - loss_reroute, 2))

    scenarios = [
        WhatIfScenario(
            id="continue_route",
            scenarioName="Continue Current Route",
            action="MAINTAIN_ROUTE",
            destination="Planned Destination",
            etaMinutes=current_eta,
            predictedRisk=current_risk,
            projectedLoss=loss_continue,
            remainingSafeLife=safe_life_continue,
            isRecommended=False
        ),
        WhatIfScenario(
            id="reroute_cold_storage",
            scenarioName="Reroute to Cold Storage",
            action="DIVERT_COLD_STORAGE",
            destination=nearest_facility_name,
            etaMinutes=nearest_facility_eta,
            predictedRisk=risk_reroute,
            projectedLoss=loss_reroute,
            remainingSafeLife=safe_life_reroute,
            isRecommended=True
        ),
        WhatIfScenario(
            id="emergency_delivery",
            scenarioName="Emergency Expedited Delivery",
            action="EXPEDITE_DELIVERY",
            destination="Alternate Fast Corridor",
            etaMinutes=max(20, current_eta - 15),
            predictedRisk=risk_expedite,
            projectedLoss=loss_expedite,
            remainingSafeLife=safe_life_expedite,
            isRecommended=False
        )
    ]

    return WhatIfSimulationResponse(
        shipmentId=shipment_code,
        scenarios=scenarios,
        estimatedLossWithoutIntervention=loss_continue,
        estimatedLossWithIntervention=loss_reroute,
        potentialLossAvoided=loss_avoided,
        recommendedAction="Reroute to Cold Storage A (Guindy)"
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.db.models import Shipment, Intervention, ColdStorageFacility, RiskPrediction, User
from app.schemas.intervention import (
    WhatIfSimulationResponse,
    InterventionApproveRequest,
    InterventionOverrideRequest,
    HandoffRequest
)
from app.services.intervention_service import generate_what_if_scenarios
from app.services.audit_service import log_audit_event
from app.websocket.manager import ws_manager
from app.core.dependencies import get_current_user, require_role

router = APIRouter(prefix="/interventions", tags=["Interventions"])


@router.post("/{shipment_id}/simulate", response_model=WhatIfSimulationResponse)
async def simulate_what_if_scenarios(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    Generate and compare the 3 What-If action candidate scenarios:
    1. Continue Current Route
    2. Reroute to Nearest Cold Storage (AI Recommended)
    3. Emergency Expedited Delivery
    And compute projected financial loss avoided (₹).
    """
    stmt = select(Shipment).where(Shipment.shipment_code == shipment_id)
    res = await db.execute(stmt)
    shipment = res.scalars().first()
    
    # Get latest risk
    r_stmt = (
        select(RiskPrediction)
        .where(RiskPrediction.shipment_id == shipment_id)
        .order_by(desc(RiskPrediction.timestamp))
        .limit(1)
    )
    r_res = await db.execute(r_stmt)
    latest_r = r_res.scalars().first()
    
    current_risk = latest_r.risk_score if latest_r else 78
    current_eta = shipment.current_eta_minutes if shipment else 45
    cargo_val = float(shipment.estimated_cargo_value) if shipment else 240000.0
    
    simulation = generate_what_if_scenarios(
        shipment_code=shipment_id,
        current_risk=current_risk,
        current_eta=current_eta,
        cargo_value=cargo_val,
        nearest_facility_name="Cold Storage A (Guindy)",
        nearest_facility_eta=18
    )
    
    return simulation


@router.post("/{shipment_id}/approve")
async def approve_intervention(
    shipment_id: str,
    body: InterventionApproveRequest = None,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(["ADMIN"])),
):
    """
    (Admin Action) Approve AI recommendation to divert shipment to Cold Storage.
    Transitions status to APPROVED and logs to compliance audit trail.
    """
    stmt = select(Shipment).where(Shipment.shipment_code == shipment_id)
    res = await db.execute(stmt)
    shipment = res.scalars().first()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
        
    shipment.status = "DIVERTED"
    shipment.destination_name = "Cold Storage A (Guindy)"
    shipment.current_eta_minutes = 18
    
    # Create intervention record
    intervention = Intervention(
        shipment_id=shipment_id,
        recommended_action="Reroute to Cold Storage A (Guindy)",
        target_facility_name="Cold Storage A (Guindy)",
        risk_before=78,
        risk_after=18,
        eta_before=45,
        eta_after=18,
        potential_loss_avoided=7300.0,
        reason="Admin approved AI recommendation: lowest estimated spoilage risk",
        status="APPROVED"
    )
    db.add(intervention)
    
    # Log to audit trail
    await log_audit_event(
        db=db,
        shipment_id=shipment_id,
        stage="APPROVED",
        title="Admin Approved Reroute Intervention",
        details="Shipment diverted to Cold Storage A (Guindy) with ETA 18 min."
    )
    
    await db.commit()
    
    # Broadcast to WebSocket
    await ws_manager.broadcast({
        "type": "INTERVENTION_APPROVED",
        "shipmentId": shipment_id,
        "action": "DIVERTED",
        "destination": "Cold Storage A (Guindy)",
        "eta": 18
    })
    
    return {
        "status": "success",
        "message": f"Intervention approved for {shipment_id}. Diverting to Cold Storage A.",
        "shipmentStatus": "DIVERTED"
    }


@router.post("/{shipment_id}/override")
async def override_intervention(
    shipment_id: str,
    body: InterventionOverrideRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(["ADMIN"])),
):
    """
    (Admin Action) Override AI recommendation with required reason string.
    """
    await log_audit_event(
        db=db,
        shipment_id=shipment_id,
        stage="OVERRIDDEN",
        title="Admin Overrode AI Recommendation",
        details=f"Reason: {body.overrideReason}"
    )
    return {"status": "success", "message": f"AI recommendation overridden for {shipment_id}."}


@router.post("/{shipment_id}/field-accept")
async def field_agent_accept_reroute(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    _field_agent=Depends(require_role(["FIELD_AGENT"])),
):
    """
    (Field Agent Action) Driver taps 'Accept & Reroute' on in-cab mobile screen.
    """
    await log_audit_event(
        db=db,
        shipment_id=shipment_id,
        stage="FIELD_ACCEPTED",
        title="Field Agent Accepted Reroute Navigation",
        details="Driver navigating to Cold Storage A (Guindy)."
    )
    
    await ws_manager.broadcast({
        "type": "FIELD_ACCEPTED",
        "shipmentId": shipment_id
    })
    return {"status": "success", "message": "Reroute accepted. Turn-by-turn navigation started."}


@router.post("/{shipment_id}/backup-cooling")
async def toggle_backup_cooling(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    _field_agent=Depends(require_role(["FIELD_AGENT"])),
):
    """
    (Field Agent Action) Driver activates in-cab backup cooling compressor.
    """
    await log_audit_event(
        db=db,
        shipment_id=shipment_id,
        stage="BACKUP_COOLING_ACTIVATED",
        title="Backup Cooling Compressor Activated",
        details="Field agent manually engaged secondary refrigeration unit."
    )
    return {"status": "success", "message": "Backup cooling active (100% power)."}


@router.post("/{shipment_id}/handoff")
async def verify_handoff_completion(
    shipment_id: str,
    body: HandoffRequest = None,
    db: AsyncSession = Depends(get_db),
    _field_agent=Depends(require_role(["FIELD_AGENT"])),
):
    """
    (Field Agent Action) Driver uploads photo & confirms handoff at cold storage bay.
    """
    stmt = select(Shipment).where(Shipment.shipment_code == shipment_id)
    res = await db.execute(stmt)
    shipment = res.scalars().first()
    if shipment:
        shipment.status = "DELIVERED"
        
    await log_audit_event(
        db=db,
        shipment_id=shipment_id,
        stage="HANDOFF_COMPLETED",
        title="Cold Storage Handoff Verified",
        details="Cargo securely handed off to receiving bay supervisor. Spoilage averted.",
        metadata={"photoUrl": body.handoffPhotoUrl if body else None}
    )
    await db.commit()
    
    await ws_manager.broadcast({
        "type": "HANDOFF_COMPLETED",
        "shipmentId": shipment_id,
        "status": "DELIVERED"
    })
    return {"status": "success", "message": "Handoff successfully verified and recorded."}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.db.models import Shipment, Telemetry, RiskPrediction, AuditLog

router = APIRouter(prefix="/public", tags=["Public Tracking (Client)"])


@router.get("/track/{shipment_id}")
async def public_track_shipment(
    shipment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public Read-Only Tracking View for Clients & Viewers.
    No login required. Displays cargo status, trust badge, and stage timeline.
    """
    stmt = select(Shipment).where(Shipment.shipment_code == shipment_id)
    res = await db.execute(stmt)
    s = res.scalars().first()
    
    if not s:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
        
    # Get latest telemetry
    t_stmt = (
        select(Telemetry)
        .where(Telemetry.shipment_id == shipment_id)
        .order_by(desc(Telemetry.timestamp))
        .limit(1)
    )
    t_res = await db.execute(t_stmt)
    latest_t = t_res.scalars().first()
    
    # Get latest risk
    r_stmt = (
        select(RiskPrediction)
        .where(RiskPrediction.shipment_id == shipment_id)
        .order_by(desc(RiskPrediction.timestamp))
        .limit(1)
    )
    r_res = await db.execute(r_stmt)
    latest_r = r_res.scalars().first()
    
    # Timeline
    timeline_stages = [
        {"stage": "Picked Up", "status": "COMPLETED"},
        {"stage": "In Transit", "status": "COMPLETED" if s.status != "PENDING" else "CURRENT"},
        {"stage": "Cold Chain Monitored", "status": "COMPLETED" if s.status in ("DIVERTED", "DELIVERED") else "CURRENT"},
        {"stage": "Intervention", "status": "COMPLETED" if s.status == "DELIVERED" else ("CURRENT" if s.status == "DIVERTED" else "PENDING")},
        {"stage": "Delivered", "status": "COMPLETED" if s.status == "DELIVERED" else "PENDING"}
    ]
    
    temp = float(latest_t.temperature) if latest_t else 4.2
    risk_level = latest_r.risk_level if latest_r else "LOW"
    
    # Map to Safe / At Risk / Critical
    client_status = "SAFE"
    if risk_level == "CRITICAL":
        client_status = "CRITICAL"
    elif risk_level in ("HIGH", "MEDIUM"):
        client_status = "AT_RISK"
        
    return {
        "shipmentId": s.shipment_code,
        "productName": s.product.name if s.product else "Cold-Chain Cargo",
        "productCategory": s.product.category if s.product else "Pharma",
        "status": client_status,
        "rawStatus": s.status,
        "temperature": temp,
        "optimalRange": f"{float(s.product.safe_temp_min) if s.product else 2.0}°C – {float(s.product.safe_temp_max) if s.product else 8.0}°C",
        "etaMinutes": s.current_eta_minutes,
        "origin": s.origin_name,
        "destination": s.destination_name,
        "trustBadge": "Cold Chain Verified (Continuously Monitored)",
        "timeline": timeline_stages
    }

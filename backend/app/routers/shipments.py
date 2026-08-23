from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.db.database import get_db
from app.db.models import Shipment, Product, Telemetry, RiskPrediction
from app.schemas.shipment import ShipmentResponse, ShipmentCreate

router = APIRouter(prefix="/shipments", tags=["Shipments"])


@router.get("")
async def list_active_shipments(db: AsyncSession = Depends(get_db)):
    """Retrieve all active shipments with latest telemetry and risk scores."""
    stmt = select(Shipment)
    result = await db.execute(stmt)
    shipments = result.scalars().all()
    
    response = []
    for s in shipments:
        # Get latest telemetry
        t_stmt = (
            select(Telemetry)
            .where(Telemetry.shipment_id == s.shipment_code)
            .order_by(desc(Telemetry.timestamp))
            .limit(1)
        )
        t_res = await db.execute(t_stmt)
        latest_t = t_res.scalars().first()
        
        # Get latest risk
        r_stmt = (
            select(RiskPrediction)
            .where(RiskPrediction.shipment_id == s.shipment_code)
            .order_by(desc(RiskPrediction.timestamp))
            .limit(1)
        )
        r_res = await db.execute(r_stmt)
        latest_r = r_res.scalars().first()
        
        temp = float(latest_t.temperature) if latest_t else (float(s.product.safe_temp_min + 2.0) if s.product else 4.0)
        humidity = float(latest_t.humidity) if latest_t else 45.0
        speed = float(latest_t.speed or 40.0) if latest_t else 40.0
        door_open = latest_t.door_open if latest_t else False
        cooling_power = latest_t.cooling_power if latest_t else 70
        battery = float(latest_t.battery_level or 90.0) if latest_t else 90.0
        
        risk_score = latest_r.risk_score if latest_r else 15
        risk_level = latest_r.risk_level if latest_r else "LOW"
        safe_life = latest_r.remaining_safe_life_minutes if latest_r else None
        
        safe_min = float(s.product.safe_temp_min) if s.product else 2.0
        safe_max = float(s.product.safe_temp_max) if s.product else 8.0
        prod_name = s.product.name if s.product else "Cold-Chain Cargo"
        prod_cat = s.product.category if s.product else "Pharma"
        
        response.append({
            "id": str(s.id),
            "shipmentId": s.shipment_code,
            "productName": prod_name,
            "productType": prod_cat,
            "vehicleId": s.vehicle_number,
            "origin": {
                "name": s.origin_name,
                "latitude": float(s.origin_lat),
                "longitude": float(s.origin_lng),
                "type": "origin"
            },
            "destination": {
                "name": s.destination_name,
                "latitude": float(s.destination_lat),
                "longitude": float(s.destination_lng),
                "type": "destination"
            },
            "latitude": float(s.current_lat or s.origin_lat),
            "longitude": float(s.current_lng or s.origin_lng),
            "temperature": temp,
            "humidity": humidity,
            "speed": speed,
            "doorOpen": door_open,
            "coolingPower": cooling_power,
            "battery": battery,
            "status": s.status,
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "plannedEtaMinutes": s.planned_eta_minutes,
            "etaMinutes": s.current_eta_minutes,
            "delayMinutes": s.delay_minutes,
            "estimatedCargoValue": float(s.estimated_cargo_value),
            "safeMinTemp": safe_min,
            "safeMaxTemp": safe_max,
            "remainingSafeLifeMinutes": safe_life
        })
        
    return {"shipments": response}


@router.get("/{shipment_id}")
async def get_shipment_by_code(shipment_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve detailed state for a single shipment."""
    stmt = select(Shipment).where(Shipment.shipment_code == shipment_id)
    res = await db.execute(stmt)
    s = res.scalars().first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shipment {shipment_id} not found")
        
    # Query latest telemetry
    t_stmt = (
        select(Telemetry)
        .where(Telemetry.shipment_id == shipment_id)
        .order_by(desc(Telemetry.timestamp))
        .limit(1)
    )
    t_res = await db.execute(t_stmt)
    latest_t = t_res.scalars().first()
    
    # Query latest risk prediction
    r_stmt = (
        select(RiskPrediction)
        .where(RiskPrediction.shipment_id == shipment_id)
        .order_by(desc(RiskPrediction.timestamp))
        .limit(1)
    )
    r_res = await db.execute(r_stmt)
    latest_r = r_res.scalars().first()
    
    return {
        "shipment": s,
        "latestTelemetry": latest_t,
        "latestRisk": latest_r
    }

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.db.database import get_db
from app.db.models import Telemetry
from app.schemas.telemetry import TelemetryCreate, TelemetryResponse
from app.services.telemetry_service import process_telemetry_ingestion
from app.websocket.manager import ws_manager

router = APIRouter(tags=["Telemetry"])


@router.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def ingest_telemetry(
    payload: TelemetryCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Canonical Telemetry Ingestion Endpoint.
    Receives sensor readings from ESP32 hardware or Simulator,
    validates ranges, updates DB, executes AI risk engine,
    and broadcasts updates via WebSocket.
    """
    result = await process_telemetry_ingestion(payload, db)
    
    # Broadcast to connected WebSocket dashboards
    await ws_manager.broadcast({
        "type": "TELEMETRY_UPDATE",
        "data": result
    })
    
    return result


@router.get("/shipments/{shipment_id}/telemetry")
async def get_shipment_telemetry_history(
    shipment_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical telemetry time-series for charts."""
    stmt = (
        select(Telemetry)
        .where(Telemetry.shipment_id == shipment_id)
        .order_by(desc(Telemetry.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    # Return chronologically ascending for charts
    history = [
        {
            "id": str(r.id),
            "timestamp": r.timestamp.isoformat() if r.timestamp else "",
            "temperature": float(r.temperature),
            "humidity": float(r.humidity),
            "speed": float(r.speed or 0),
            "doorOpen": r.door_open,
            "coolingPower": r.cooling_power,
            "battery": float(r.battery_level or 90)
        }
        for r in reversed(records)
    ]
    return {"shipmentId": shipment_id, "history": history}

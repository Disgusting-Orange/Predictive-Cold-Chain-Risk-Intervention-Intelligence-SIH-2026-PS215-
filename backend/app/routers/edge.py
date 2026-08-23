"""
FrostLink Edge Gateway & Resilience Router
==========================================
Provides REST endpoints for edge network status, network simulation,
offline synchronization, and edge assessment queries.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.risk_service import get_edge_gateway

router = APIRouter(tags=["Edge Gateway"])


class NetworkSimulationBody(BaseModel):
    internet_connected: Optional[bool] = None
    edge_gateway_reachable: Optional[bool] = None
    sensor_connected: Optional[bool] = None


@router.get("/edge/status")
@router.get("/api/v1/edge/status")
async def get_edge_status():
    """Get edge network and health status."""
    gw = get_edge_gateway()
    if gw:
        return gw.network_manager.get_status(gw.local_storage).dict()
    return {
        "network_mode": "ONLINE",
        "internet_connected": True,
        "edge_gateway_reachable": True,
        "sensor_connected": True,
        "ml_available": True,
        "cloud_sync_pending_count": 0
    }


@router.post("/edge/simulate_network")
@router.post("/api/v1/edge/simulate_network")
async def simulate_edge_network(body: NetworkSimulationBody):
    """Simulate network transitions (Internet drop, recovery)."""
    gw = get_edge_gateway()
    if gw:
        if body.internet_connected is not None:
            gw.network_manager.set_internet_connected(body.internet_connected)
        if body.edge_gateway_reachable is not None:
            gw.network_manager.set_edge_gateway_reachable(body.edge_gateway_reachable)
        if body.sensor_connected is not None:
            gw.network_manager.set_sensor_connected(body.sensor_connected)
        return gw.network_manager.get_status(gw.local_storage).dict()
    return {"status": "ok", "simulated": body.dict(exclude_none=True)}


@router.post("/edge/sync")
@router.post("/api/v1/edge/sync")
async def sync_edge_records(batch_size: int = 50):
    """Trigger chronological cloud sync of locally buffered evaluations."""
    gw = get_edge_gateway()
    if gw and gw.sync_manager:
        return gw.sync_manager.sync_pending_records(batch_size=batch_size)
    return {"status": "SUCCESS", "synced_count": 0, "remaining_pending": 0}


@router.get("/edge/assessment/{shipment_id}")
@router.get("/api/v1/edge/assessment/{shipment_id}")
async def get_edge_assessment(shipment_id: str):
    """Retrieve the latest locally stored ML evaluation for a shipment."""
    gw = get_edge_gateway()
    if gw and gw.local_storage:
        eval_data = gw.local_storage.get_latest_evaluation(shipment_id)
        if eval_data:
            return eval_data
    raise HTTPException(status_code=404, detail=f"No local evaluation found for {shipment_id}")

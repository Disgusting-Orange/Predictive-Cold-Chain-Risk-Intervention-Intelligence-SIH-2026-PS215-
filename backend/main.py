"""
AI Cold Chain Optimisation Platform — Backend API
==================================================
FastAPI backend with WebSocket real-time telemetry push
and REST endpoints for scenario control and intervention.
"""

import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from simulator import ColdChainSimulator

app = FastAPI(
    title="AI Cold Chain Optimisation Platform",
    description="SIH Prototype — Simulated cold-chain monitoring backend",
    version="1.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global simulator instance (single-user demo)
simulator = ColdChainSimulator()

# Connected WebSocket clients
connected_clients: list[WebSocket] = []

# Tick interval in seconds
TICK_INTERVAL = 2.0


# ==================== PYDANTIC MODELS ====================

class ShipmentControlBody(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[int] = None
    speed: Optional[int] = None
    doorOpen: Optional[bool] = None
    battery: Optional[float] = None
    coolingPower: Optional[int] = None

class WarehouseControlBody(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[int] = None
    capacity: Optional[int] = None
    coolingStatus: Optional[str] = None
    powerStatus: Optional[str] = None
    tempSetpoint: Optional[float] = None
    activeBays: Optional[int] = None


# ==================== BROADCAST ====================

async def broadcast_state():
    """Send current state to all connected WebSocket clients."""
    state = simulator.get_state()
    data = json.dumps(state)
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_text(data)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)


async def simulation_loop():
    """Background task — ticks the simulator every TICK_INTERVAL seconds."""
    while True:
        await asyncio.sleep(TICK_INTERVAL)
        simulator.advance_tick()
        await broadcast_state()


@app.on_event("startup")
async def startup():
    """Start the simulation loop on app startup."""
    asyncio.create_task(simulation_loop())


# ==================== REST ENDPOINTS ====================

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "cold-chain-api"}


@app.get("/api/state")
async def get_state():
    """Get current dashboard state (for initial load / polling fallback)."""
    return simulator.get_state()


@app.post("/api/scenario/{scenario}")
async def set_scenario(scenario: str):
    """
    Change the active demo scenario.
    Valid: normal, temp_failure, traffic_delay, combined, reset
    """
    valid = ["normal", "temp_failure", "traffic_delay", "combined", "reset"]
    if scenario not in valid:
        return {"error": f"Invalid scenario. Must be one of: {valid}"}

    simulator.set_scenario(scenario)
    await broadcast_state()
    return {"status": "ok", "scenario": scenario}


@app.post("/api/intervene/{shipment_id}")
async def apply_intervention(shipment_id: str):
    """Apply the recommended intervention to a shipment."""
    simulator.apply_intervention(shipment_id)
    await broadcast_state()
    return {"status": "ok", "shipmentId": shipment_id}


@app.post("/api/select/{shipment_id}")
async def select_shipment(shipment_id: str):
    """Select a shipment for the detail view."""
    simulator.selected_shipment_id = shipment_id
    await broadcast_state()
    return {"status": "ok", "selectedShipmentId": shipment_id}


# ==================== CONTROL ENDPOINTS ====================

@app.post("/api/control/{shipment_id}")
async def control_shipment(shipment_id: str, body: ShipmentControlBody):
    """Apply manual control overrides to a shipment's parameters."""
    overrides = body.model_dump(exclude_none=True)
    if not overrides:
        return {"error": "No control parameters provided"}

    success = simulator.apply_shipment_control(shipment_id, overrides)
    if not success:
        return {"error": f"Shipment {shipment_id} not found"}

    await broadcast_state()
    return {"status": "ok", "shipmentId": shipment_id, "applied": overrides}


@app.post("/api/warehouse/{warehouse_id}/control")
async def control_warehouse(warehouse_id: str, body: WarehouseControlBody):
    """Apply manual control overrides to a warehouse's parameters."""
    overrides = body.model_dump(exclude_none=True)
    if not overrides:
        return {"error": "No control parameters provided"}

    success = simulator.apply_warehouse_control(warehouse_id, overrides)
    if not success:
        return {"error": f"Warehouse {warehouse_id} not found"}

    await broadcast_state()
    return {"status": "ok", "warehouseId": warehouse_id, "applied": overrides}


@app.get("/api/warehouses")
async def get_warehouses():
    """Get current warehouse states."""
    state = simulator.get_state()
    return {"warehouses": state.get("warehouses", [])}


# ==================== WEBSOCKET ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time state push."""
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        # Send initial state immediately
        state = simulator.get_state()
        await websocket.send_text(json.dumps(state))

        # Listen for client messages (e.g., shipment selection, controls)
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "select":
                    simulator.selected_shipment_id = msg.get("shipmentId")
                    await broadcast_state()

                elif msg_type == "control":
                    sid = msg.get("shipmentId")
                    params = msg.get("params", {})
                    if sid and params:
                        simulator.apply_shipment_control(sid, params)
                        await broadcast_state()

                elif msg_type == "warehouse_control":
                    wid = msg.get("warehouseId")
                    params = msg.get("params", {})
                    if wid and params:
                        simulator.apply_warehouse_control(wid, params)
                        await broadcast_state()

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

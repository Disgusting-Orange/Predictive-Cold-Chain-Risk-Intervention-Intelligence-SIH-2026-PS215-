"""In-process demo telemetry so dashboards have live data without ESP32 hardware."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, Literal

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Shipment
from app.schemas.telemetry import TelemetryCreate
from app.services.telemetry_service import process_telemetry_ingestion
from app.websocket.manager import ws_manager

DemoMode = Literal["normal", "combined_failure"]

demo_state: Dict[str, object] = {
    "mode": "normal",
    "tick": 0,
}

_BASE_TEMPS = {
    "SHP-1042": 4.2,
    "SHP-1041": 5.1,
    "SHP-1043": 3.8,
}


def get_demo_status() -> dict:
    return {"mode": demo_state["mode"], "tick": demo_state["tick"]}


async def set_demo_mode(mode: DemoMode) -> dict:
    demo_state["mode"] = mode
    if mode == "normal":
        demo_state["tick"] = 0
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Shipment))
            for shipment in result.scalars().all():
                if shipment.status in ("AT_RISK", "WARNING", "DIVERTED"):
                    shipment.status = "IN_TRANSIT"
                    shipment.current_eta_minutes = shipment.planned_eta_minutes
                    shipment.delay_minutes = 0
            await session.commit()
        await ws_manager.broadcast({"type": "DEMO_RESET", "mode": mode})
    else:
        await ws_manager.broadcast({"type": "DEMO_SCENARIO", "mode": mode})
    return get_demo_status()


def _reading_for(code: str, tick: int, mode: str) -> TelemetryCreate:
    base = _BASE_TEMPS.get(code, 4.0)
    temperature = base
    humidity = 46.0
    speed = 38.0
    door_open = False
    cooling = 72
    delay_bias = 0.0

    if mode == "combined_failure" and code == "SHP-1042":
        temperature = min(12.5, base + tick * 0.35)
        humidity = min(70.0, 46.0 + tick * 0.8)
        speed = max(8.0, 38.0 - tick * 1.4)
        door_open = tick >= 4
        cooling = max(20, 72 - tick * 4)
        delay_bias = tick * 0.0004

    lat = 13.0750 + tick * 0.0003
    lng = 80.2650 - tick * 0.0002
    if code == "SHP-1041":
        lat, lng = 13.0810, 80.2715
        temperature = base + (0.15 if mode == "combined_failure" else 0.05)
    if code == "SHP-1043":
        lat, lng = 13.0200, 80.2280

    return TelemetryCreate(
        shipmentId=code,
        deviceId=f"BOX-{code[-2:]}",
        timestamp=datetime.now(timezone.utc),
        temperature=round(temperature, 2),
        humidity=round(humidity, 1),
        latitude=round(lat + delay_bias, 6),
        longitude=round(lng, 6),
        speed=round(speed, 1),
        doorOpen=door_open,
        coolingPower=cooling,
        battery=max(62.0, 94.0 - tick * 0.4),
    )


async def emit_tick() -> None:
    tick = int(demo_state["tick"])
    mode = str(demo_state["mode"])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Shipment.shipment_code))
        codes = [row[0] for row in result.all()] or list(_BASE_TEMPS.keys())
        for code in codes:
            payload = _reading_for(code, tick, mode)
            result_payload = await process_telemetry_ingestion(payload, session)
            await ws_manager.broadcast({"type": "TELEMETRY_UPDATE", "data": result_payload})
    demo_state["tick"] = tick + 1


async def run_demo_loop(interval_seconds: float = 4.0) -> None:
    await asyncio.sleep(1.5)
    try:
        await emit_tick()
    except Exception:
        pass
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await emit_tick()
        except Exception:
            continue

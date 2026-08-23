"""
AI Cold Chain Optimisation Platform — Production FastAPI Backend
================================================================
Unified backend connecting ESP32 Hardware, Supabase PostgreSQL,
AI Risk & What-If Engine, 3-Role JWT Auth, and Real-Time WebSockets.
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import engine, Base, AsyncSessionLocal
from app.db.models import User, Product, Shipment
from app.core.security import get_password_hash
from app.routers import auth, telemetry, shipments, products, interventions, public, audit, demo, edge
from app.websocket.manager import ws_manager
from app.services.demo_loop import run_demo_loop
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & Shutdown lifecycle handler."""
    # Ensure tables exist in DB (if using SQLite fallback or new PostgreSQL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Auto-seed initial baseline data if DB is empty
    async with AsyncSessionLocal() as session:
        # 1. Seed default users
        u_stmt = select(User).limit(1)
        u_res = await session.execute(u_stmt)
        if not u_res.scalars().first():
            demo_users = [
                User(email="admin@coldchain.ai", password_hash=get_password_hash("admin123"), full_name="Fleet Operations Admin", role="ADMIN"),
                User(email="driver@coldchain.ai", password_hash=get_password_hash("driver123"), full_name="Ramesh (Field Driver)", role="FIELD_AGENT"),
                User(email="client@coldchain.ai", password_hash=get_password_hash("client123"), full_name="Apollo Hospital Pharmacy", role="CLIENT")
            ]
            session.add_all(demo_users)
            
        # 2. Seed products
        p_stmt = select(Product).limit(1)
        p_res = await session.execute(p_stmt)
        if not p_res.scalars().first():
            demo_products = [
                Product(name="Pasteurized Milk", category="Dairy", safe_temp_min=1.0, safe_temp_max=5.0, critical_temp_max=8.0, shelf_life_hours=72.0),
                Product(name="COVID-19 Vaccines", category="Vaccines", safe_temp_min=2.0, safe_temp_max=8.0, critical_temp_max=10.0, shelf_life_hours=120.0),
                Product(name="Insulin Glargine", category="Insulin", safe_temp_min=2.0, safe_temp_max=8.0, critical_temp_max=12.0, shelf_life_hours=96.0),
                Product(name="Monoclonal Antibodies", category="Biologics", safe_temp_min=2.0, safe_temp_max=8.0, critical_temp_max=10.0, shelf_life_hours=48.0),
                Product(name="Frozen Seafood", category="Seafood", safe_temp_min=-25.0, safe_temp_max=-15.0, critical_temp_max=-10.0, shelf_life_hours=720.0)
            ]
            session.add_all(demo_products)
            
        # 3. Seed initial shipments
        s_stmt = select(Shipment).limit(1)
        s_res = await session.execute(s_stmt)
        if not s_res.scalars().first():
            products = (await session.execute(select(Product))).scalars().all()
            by_name = {p.name: p.id for p in products}
            demo_shipments = [
                Shipment(
                    shipment_code="SHP-1042",
                    product_id=by_name.get("Pasteurized Milk"),
                    vehicle_number="TN-07-CD-5678",
                    origin_name="MediCold Distribution Centre",
                    origin_lat=13.0827,
                    origin_lng=80.2707,
                    destination_name="Apollo Hospital Pharmacy",
                    destination_lat=13.0604,
                    destination_lng=80.2496,
                    current_lat=13.0750,
                    current_lng=80.2650,
                    status="IN_TRANSIT",
                    planned_eta_minutes=45,
                    current_eta_minutes=45,
                    estimated_cargo_value=240000.0
                ),
                Shipment(
                    shipment_code="SHP-1041",
                    product_id=by_name.get("COVID-19 Vaccines"),
                    vehicle_number="TN-07-AB-1234",
                    origin_name="MediCold Distribution Centre",
                    origin_lat=13.0827,
                    origin_lng=80.2707,
                    destination_name="Govt. General Hospital",
                    destination_lat=13.0786,
                    destination_lng=80.2728,
                    current_lat=13.0810,
                    current_lng=80.2715,
                    status="IN_TRANSIT",
                    planned_eta_minutes=22,
                    current_eta_minutes=22,
                    estimated_cargo_value=520000.0
                ),
                Shipment(
                    shipment_code="SHP-1043",
                    product_id=by_name.get("Insulin Glargine"),
                    vehicle_number="TN-07-EF-9012",
                    origin_name="Cold Storage A (Guindy)",
                    origin_lat=13.0067,
                    origin_lng=80.2206,
                    destination_name="MedPlus Pharmacy (T. Nagar)",
                    destination_lat=13.0418,
                    destination_lng=80.2341,
                    current_lat=13.0200,
                    current_lng=80.2280,
                    status="IN_TRANSIT",
                    planned_eta_minutes=15,
                    current_eta_minutes=15,
                    estimated_cargo_value=180000.0
                )
            ]
            session.add_all(demo_shipments)

        missing_products = (await session.execute(select(Shipment).where(Shipment.product_id.is_(None)))).scalars().all()
        if missing_products:
            products = (await session.execute(select(Product))).scalars().all()
            by_name = {p.name: p.id for p in products}
            mapping = {"SHP-1042": "Pasteurized Milk", "SHP-1041": "COVID-19 Vaccines", "SHP-1043": "Insulin Glargine"}
            for shipment in missing_products:
                name = mapping.get(shipment.shipment_code)
                if name and name in by_name:
                    shipment.product_id = by_name[name]
            
        await session.commit()

    loop_task = asyncio.create_task(run_demo_loop())
    yield
    loop_task.cancel()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for AI Cold Chain Risk & Intervention Intelligence (SIH 2026 PS215)",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(telemetry.router, prefix=settings.API_V1_STR)
app.include_router(shipments.router, prefix=settings.API_V1_STR)
app.include_router(products.router, prefix=settings.API_V1_STR)
app.include_router(interventions.router, prefix=settings.API_V1_STR)
app.include_router(public.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(demo.router, prefix=settings.API_V1_STR)
app.include_router(edge.router, prefix=settings.API_V1_STR)

# Top-level aliases for canonical endpoints as specified in contract
app.include_router(telemetry.router)
app.include_router(edge.router)


# Health Check Endpoints
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "cold-chain-backend",
        "database": "connected",
        "version": settings.VERSION
    }


# WebSocket Endpoints
@app.websocket("/ws/telemetry")
@app.websocket("/ws")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Live real-time state broadcast endpoint for connected dashboards.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to Cold-Chain Live Telemetry Broadcast"
        })
        while True:
            # Keep connection open and accept client heartbeats / commands
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

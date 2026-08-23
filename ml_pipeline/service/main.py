"""
FrostLink ML Inference Service -- Main Application
==================================================
FastAPI application exposing production risk prediction, health endpoints,
and local edge gateway communication endpoints (Phase 21).
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import SERVICE_NAME, SERVICE_VERSION, API_PREFIX
from schemas import PredictionRequest, PredictionResponse, HealthResponse, ErrorResponse
from model_service import ModelService, ArtifactIntegrityError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("frostlink_ml_service")

# Hardware Ingestion Gateway & Edge Network imports
try:
    from gateway import HardwareGateway
    from edge_network import EdgeNetworkManager
    from edge_sync import EdgeSyncManager
    from local_storage import LocalStorage
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hardware")))
    from gateway import HardwareGateway
    from edge_network import EdgeNetworkManager
    from edge_sync import EdgeSyncManager
    from local_storage import LocalStorage

_gateway = HardwareGateway()

# Lifespan context manager for startup / shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing FrostLink ML Inference & Edge Gateway Service...")
    try:
        ModelService.get_instance()
        logger.info("Model service successfully initialized & artifact integrity verified.")
    except ArtifactIntegrityError as e:
        logger.critical(f"FATAL: Model artifact integrity verification failed: {e}")
    except Exception as e:
        logger.critical(f"FATAL: Unexpected error loading model service: {e}")
    yield
    logger.info("Shutting down FrostLink ML Inference & Edge Gateway Service.")

app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    description="Edge-resilient ML inference service serving frozen XGBoost early-warning risk predictions, SHAP attributions, and local edge telemetry ingestion.",
    lifespan=lifespan
)

# Custom Exception Handlers (Prevent stack trace leakage)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        error_details.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Request Validation Error",
            "detail": "; ".join(error_details),
            "error_code": "INVALID_INPUT"
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Value Error",
            "detail": str(exc),
            "error_code": "INVALID_FEATURE_PAYLOAD"
        }
    )

@app.exception_handler(ArtifactIntegrityError)
async def integrity_error_handler(request: Request, exc: ArtifactIntegrityError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Service Unavailable",
            "detail": "Model artifact verification failed or package is corrupted.",
            "error_code": "ARTIFACT_INTEGRITY_FAILURE"
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred during prediction inference.",
            "error_code": "INFERENCE_FAILED"
        }
    )

# Routes
@app.get("/", tags=["Info"])
async def root_info():
    net_status = _gateway.network_manager.get_status(_gateway.local_storage)
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "ONLINE",
        "network_mode": net_status.network_mode.value,
        "docs_url": "/docs",
        "health_check": "/health",
        "edge_status_check": f"{API_PREFIX}/edge/status",
        "predict_endpoint": f"{API_PREFIX}/predict_risk",
        "telemetry_endpoint": f"{API_PREFIX}/telemetry",
        "notice": "Advisory early-warning ML baseline with local-edge offline resilience."
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    try:
        service = ModelService.get_instance()
        return service.get_health_status()
    except ArtifactIntegrityError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Artifact integrity check failed."
        )

@app.post(
    f"{API_PREFIX}/predict_risk",
    response_model=PredictionResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation Error (missing or invalid features)"},
        503: {"model": ErrorResponse, "description": "Service Unavailable (corrupt model package)"},
        500: {"model": ErrorResponse, "description": "Internal Inference Error"}
    },
    tags=["Inference"]
)
async def predict_risk(request: PredictionRequest):
    service = ModelService.get_instance()
    try:
        return service.predict_risk(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ArtifactIntegrityError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prediction inference failure.")

# ============================================================
# Local Edge Ingestion & Health Routes (Phase 21)
# ============================================================

@app.post(
    f"{API_PREFIX}/telemetry/ingest",
    tags=["Hardware Ingestion"],
    summary="Ingest raw ESP32 multi-probe sensor telemetry packet"
)
@app.post(
    f"{API_PREFIX}/telemetry",
    tags=["Hardware Ingestion"],
    summary="ESP32 firmware default ingestion route"
)
async def ingest_raw_telemetry(payload: Dict[str, Any]):
    try:
        res = _gateway.process_raw_telemetry(payload)
        if not res.success:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Telemetry Ingestion Rejected",
                    "detail": res.error_message,
                    "error_code": "INVALID_RAW_TELEMETRY"
                }
            )
        return res.dict()
    except Exception as e:
        logger.error(f"Hardware ingestion error: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Hardware Gateway Ingestion Failure",
                "detail": str(e),
                "error_code": "INGESTION_SERVER_ERROR"
            }
        )

@app.get(
    f"{API_PREFIX}/edge/status",
    tags=["Edge Health"],
    summary="Get explicit local edge network and health status"
)
@app.get(
    "/edge/status",
    tags=["Edge Health"],
    summary="Root alias for edge status"
)
async def get_edge_status():
    status_obj = _gateway.network_manager.get_status(_gateway.local_storage)
    return status_obj.dict()

@app.post(
    f"{API_PREFIX}/edge/sync",
    tags=["Edge Sync"],
    summary="Manually trigger cloud sync of queued observations"
)
async def trigger_cloud_sync():
    res = _gateway.sync_manager.sync_pending_records()
    return res

class NetworkSimulationBody(BaseModel):
    internet_connected: Optional[bool] = None
    edge_gateway_reachable: Optional[bool] = None
    sensor_connected: Optional[bool] = None

@app.post(
    f"{API_PREFIX}/edge/simulate_network",
    tags=["Edge Simulation"],
    summary="Simulate network state transitions for resilience testing"
)
async def simulate_network_transition(body: NetworkSimulationBody):
    if body.internet_connected is not None:
        _gateway.network_manager.set_internet_connected(body.internet_connected)
    if body.edge_gateway_reachable is not None:
        _gateway.network_manager.set_edge_gateway_reachable(body.edge_gateway_reachable)
    if body.sensor_connected is not None:
        _gateway.network_manager.set_sensor_connected(body.sensor_connected)
        
    return _gateway.network_manager.get_status(_gateway.local_storage).dict()

@app.get(
    f"{API_PREFIX}/edge/assessment/{{shipment_id}}",
    tags=["Edge Assessment"],
    summary="Get latest local ML evaluation and protective action request for a shipment"
)
async def get_latest_edge_assessment(shipment_id: str):
    eval_record = _gateway.local_storage.get_latest_evaluation(shipment_id)
    if not eval_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry evaluations found for shipment: {shipment_id}"
        )
    return eval_record

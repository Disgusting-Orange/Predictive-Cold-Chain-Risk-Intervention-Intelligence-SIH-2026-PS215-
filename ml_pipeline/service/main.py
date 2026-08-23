"""
FrostLink ML Inference Service -- Main Application
==================================================
FastAPI application exposing production risk prediction and health endpoints.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import SERVICE_NAME, SERVICE_VERSION, API_PREFIX
from schemas import PredictionRequest, PredictionResponse, HealthResponse, ErrorResponse
from model_service import ModelService, ArtifactIntegrityError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("frostlink_ml_service")

# Lifespan context manager for startup / shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing FrostLink ML Inference Service...")
    try:
        ModelService.get_instance()
        logger.info("Model service successfully initialized & artifact integrity verified.")
    except ArtifactIntegrityError as e:
        logger.critical(f"FATAL: Model artifact integrity verification failed: {e}")
    except Exception as e:
        logger.critical(f"FATAL: Unexpected error loading model service: {e}")
    yield
    logger.info("Shutting down FrostLink ML Inference Service.")

app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    description="Isolated ML inference microservice serving frozen XGBoost early-warning risk predictions and SHAP attributions.",
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
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "ONLINE",
        "docs_url": "/docs",
        "health_check": "/health",
        "predict_endpoint": f"{API_PREFIX}/predict_risk",
        "notice": "This model is an advisory early-warning baseline and is not yet validated for autonomous intervention."
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
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

# Hardware Ingestion Gateway Routes (ESP32 Wi-Fi / HTTP POST)
try:
    from gateway import HardwareGateway
    _gateway = HardwareGateway()
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hardware")))
    from gateway import HardwareGateway
    _gateway = HardwareGateway()

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

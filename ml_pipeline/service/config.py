"""
FrostLink ML Inference Service -- Configuration
===============================================
Defines filesystem paths, service port, host, and artifact settings.
"""

import os
from pathlib import Path

# Base directories
SERVICE_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVICE_DIR.parent.parent
ML_PIPELINE_DIR = ROOT_DIR / "ml_pipeline"
ARTIFACT_NAME = os.getenv("FROSTLINK_MODEL_ARTIFACT", "frostlink_xgb_v2")
ARTIFACT_DIR = ML_PIPELINE_DIR / "model_artifacts" / ARTIFACT_NAME

# Artifact file paths
MODEL_PATH = ARTIFACT_DIR / "model.json"
FEATURE_SCHEMA_PATH = ARTIFACT_DIR / "feature_schema.json"
THRESHOLD_PATH = ARTIFACT_DIR / "threshold.json"
MODEL_METADATA_PATH = ARTIFACT_DIR / "model_metadata.json"
MODEL_MANIFEST_PATH = ARTIFACT_DIR / "model_manifest.json"
FEATURE_DISPLAY_METADATA_PATH = ML_PIPELINE_DIR / "explainability" / "feature_display_metadata.json"

# Service Settings
SERVICE_HOST = os.getenv("FROSTLINK_ML_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("FROSTLINK_ML_PORT", "8000"))
API_PREFIX = "/api/v1"
SERVICE_NAME = "FrostLink ML Inference Service"
SERVICE_VERSION = "1.0.0"

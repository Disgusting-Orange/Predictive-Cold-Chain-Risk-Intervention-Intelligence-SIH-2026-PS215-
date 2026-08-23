"""
FrostLink ML Inference Service -- Model Service Engine
======================================================
Singleton ML inference engine providing:
- Cryptographic artifact verification at startup (fails closed).
- Deterministic 40-feature schema enforcement.
- Model probability inference via frozen XGBoost booster.
- Data-driven threshold evaluation and business risk-level mapping.
- Real-time SHAP attributions via TreeExplainer.
"""

import os
import json
import hashlib
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from config import (
    MODEL_PATH,
    FEATURE_SCHEMA_PATH,
    THRESHOLD_PATH,
    MODEL_METADATA_PATH,
    MODEL_MANIFEST_PATH,
    FEATURE_DISPLAY_METADATA_PATH,
    SERVICE_NAME,
    SERVICE_VERSION
)
from schemas import (
    PredictionRequest,
    PredictionResponse,
    HealthResponse,
    RiskLevelEnum,
    ExplanationFactor,
    SHAPExplanation
)

class ArtifactIntegrityError(Exception):
    """Raised when packaged model artifact SHA-256 hashes do not match manifest."""
    pass

class ModelService:
    _instance: Optional["ModelService"] = None

    def __init__(self):
        self.start_time = datetime.utcnow()
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names: List[str] = []
        self.feature_meta: Dict[str, Dict[str, Any]] = {}
        self.operating_threshold: float = 0.50
        self.model_version: str = "1.0.0"
        self.schema_version: str = "1.0.0"
        self.explainer: Optional[shap.TreeExplainer] = None
        self.base_value: float = -3.0227
        self.artifact_integrity_verified: bool = False
        
        # Initialize
        self._load_and_verify_artifacts()

    @classmethod
    def get_instance(cls) -> "ModelService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_and_verify_artifacts(self):
        """Verifies cryptographic hashes and loads ML artifacts once at startup."""
        print("[-] Verifying model package integrity against SHA-256 manifest...")
        
        if not os.path.exists(MODEL_MANIFEST_PATH):
            raise ArtifactIntegrityError(f"Model manifest not found at: {MODEL_MANIFEST_PATH}")

        with open(MODEL_MANIFEST_PATH, "r") as f:
            manifest = json.load(f)

        artifact_dir = os.path.dirname(MODEL_PATH)
        hashes_dict = manifest.get("hashes", manifest.get("files", {}))
        for fname, entry in hashes_dict.items():
            fpath = os.path.join(artifact_dir, fname)
            if not os.path.exists(fpath):
                raise ArtifactIntegrityError(f"Missing packaged file listed in manifest: {fname}")
            
            with open(fpath, "rb") as f_bytes:
                computed_hash = hashlib.sha256(f_bytes.read()).hexdigest()
            
            expected_hash = entry if isinstance(entry, str) else entry.get("sha256", "")
            if computed_hash != expected_hash:
                raise ArtifactIntegrityError(
                    f"Integrity Check Failed for {fname}! Expected {expected_hash[:12]}, computed {computed_hash[:12]}"
                )

        self.artifact_integrity_verified = True
        print("[+] Artifact integrity verified: all SHA-256 checksums match.")

        # 1. Load Feature Schema
        with open(FEATURE_SCHEMA_PATH, "r") as f:
            schema_data = json.load(f)
            self.schema_version = schema_data.get("schema_version", "1.0.0")
            # Preserve exact feature ordering
            sorted_features = sorted(schema_data["features"], key=lambda x: x["feature_order"])
            self.feature_names = [f["feature_name"] for f in sorted_features]

        # 2. Load Threshold Config
        with open(THRESHOLD_PATH, "r") as f:
            th_data = json.load(f)
            self.operating_threshold = float(th_data.get("operating_threshold", th_data.get("f1_optimal_threshold", 0.5750)))

        # 3. Load Model Metadata
        with open(MODEL_METADATA_PATH, "r") as f:
            meta_data = json.load(f)
            self.model_version = meta_data.get("model_version", "1.0.0")

        # 4. Load Display Metadata for SHAP
        if os.path.exists(FEATURE_DISPLAY_METADATA_PATH):
            with open(FEATURE_DISPLAY_METADATA_PATH, "r") as f:
                self.feature_meta = json.load(f).get("features", {})

        # 5. Load Frozen XGBoost Booster
        self.model = xgb.XGBClassifier()
        self.model.load_model(str(MODEL_PATH))
        print(f"[+] Loaded XGBoost model artifact (v{self.model_version}) with {len(self.feature_names)} features.")

        # 6. Initialize SHAP TreeExplainer
        self.explainer = shap.TreeExplainer(self.model)
        if isinstance(self.explainer.expected_value, np.ndarray):
            self.base_value = float(self.explainer.expected_value[0])
        else:
            self.base_value = float(self.explainer.expected_value)
        print(f"[+] Initialized SHAP TreeExplainer. Base Value Margin: {self.base_value:.4f}")

    def predict_risk(self, request: PredictionRequest) -> PredictionResponse:
        """
        Validates input vector, executes model prediction, and generates SHAP attributions.
        """
        if not self.artifact_integrity_verified:
            raise ArtifactIntegrityError("Model service unavailable: artifact integrity verification failed.")

        # 1. Validate required features presence
        missing_features = [f for f in self.feature_names if f not in request.features]
        if missing_features:
            raise ValueError(f"Missing {len(missing_features)} required feature(s): {missing_features[:5]}...")

        # 2. Construct ordered feature vector (cast None to np.nan and enforce float64 dtype)
        vector = [np.nan if request.features[f] is None else float(request.features[f]) for f in self.feature_names]
        df_input = pd.DataFrame([vector], columns=self.feature_names, dtype=np.float64)

        # 3. Predict Probability via XGBoost
        prob = float(self.model.predict_proba(df_input)[0, 1])

        # 4. Map Business Risk Level
        if prob >= 0.75:
            risk_level = RiskLevelEnum.CRITICAL
        elif prob >= self.operating_threshold:
            risk_level = RiskLevelEnum.WARNING
        elif prob >= 0.20:
            risk_level = RiskLevelEnum.ELEVATED
        else:
            risk_level = RiskLevelEnum.SAFE

        # 5. Compute SHAP Attributions
        shap_vals = self.explainer.shap_values(df_input)[0]

        factors = []
        for name, val, s_val in zip(self.feature_names, vector, shap_vals):
            meta = self.feature_meta.get(name, {})
            factors.append(
                ExplanationFactor(
                    feature_name=name,
                    display_name=meta.get("display_name", name),
                    observed_value=val,
                    unit=meta.get("unit", ""),
                    shap_value=float(s_val),
                    feature_group=meta.get("feature_group", "thermal")
                )
            )

        # Top risk-increasing (positive SHAP) and risk-reducing (negative SHAP)
        inc_factors = sorted([f for f in factors if f.shap_value > 0], key=lambda x: x.shap_value, reverse=True)[:5]
        dec_factors = sorted([f for f in factors if f.shap_value < 0], key=lambda x: x.shap_value)[:5]

        return PredictionResponse(
            model_version=self.model_version,
            risk_probability=prob,
            risk_level=risk_level,
            threshold=self.operating_threshold,
            prediction_horizon_minutes=60,
            explanation=SHAPExplanation(
                top_risk_increasing_factors=inc_factors,
                top_risk_reducing_factors=dec_factors
            )
        )

    def get_health_status(self) -> HealthResponse:
        """Returns service health, model version, and integrity status."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        return HealthResponse(
            status="HEALTHY" if self.artifact_integrity_verified else "UNHEALTHY",
            service_name=SERVICE_NAME,
            service_version=SERVICE_VERSION,
            model_version=self.model_version,
            feature_schema_version=self.schema_version,
            artifact_integrity_verified=self.artifact_integrity_verified,
            uptime_seconds=uptime
        )

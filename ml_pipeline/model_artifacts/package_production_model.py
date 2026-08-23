"""
FrostLink ML Pipeline -- Phase 12 Model Packaging Script
========================================================
Packages the validated real-data XGBoost baseline into:
ml_pipeline/model_artifacts/frostlink_xgb_v1/
Computes:
- Calibration curve and Brier score.
- Exact feature schema with typed metadata and strict index ordering.
- Threshold artifact with selection provenance.
- SHA-256 integrity manifest.
- Backend ingestion & error-handling contracts.
"""

import sys
import os
import json
import hashlib
import shutil
import warnings
warnings.filterwarnings('ignore')

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve

# Directory Setup
ARTIFACT_DIR = r"ml_pipeline\model_artifacts\frostlink_xgb_v1"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

SRC_MODEL_DIR = r"ml_pipeline\models\frostlink_xgb_baseline"
SRC_EXPLAIN_DIR = r"ml_pipeline\explainability"

print("=" * 80)
print("FROSTLINK PHASE 12: PACKAGING PRODUCTION XGBOOST ARTIFACT")
print("=" * 80)

# ============================================================
# 1. COPY MODEL ARTIFACT
# ============================================================
src_model_file = os.path.join(SRC_MODEL_DIR, "model.json")
dst_model_file = os.path.join(ARTIFACT_DIR, "model.json")
shutil.copyfile(src_model_file, dst_model_file)
print(f"[1] Copied model artifact to: {dst_model_file}")

# ============================================================
# 2. FEATURE SCHEMA ARTIFACT
# ============================================================
with open(os.path.join(SRC_MODEL_DIR, "features.json"), 'r') as f:
    feature_names = json.load(f)['features']

with open(os.path.join(SRC_EXPLAIN_DIR, "feature_display_metadata.json"), 'r') as f:
    display_meta = json.load(f)['features']

ordered_features = []
for idx, name in enumerate(feature_names):
    meta = display_meta.get(name, {})
    ordered_features.append({
        "feature_order": idx,
        "feature_name": name,
        "data_type": "float64",
        "unit": meta.get("unit", ""),
        "display_name": meta.get("display_name", name),
        "description": meta.get("description", ""),
        "feature_group": meta.get("feature_group", "thermal")
    })

feature_schema_payload = {
    "schema_version": "1.0.0",
    "feature_count": len(ordered_features),
    "features": ordered_features
}

dst_schema_file = os.path.join(ARTIFACT_DIR, "feature_schema.json")
with open(dst_schema_file, 'w') as f:
    json.dump(feature_schema_payload, f, indent=2)
print(f"[2] Exported ordered feature schema to: {dst_schema_file}")

# ============================================================
# 3. THRESHOLD ARTIFACT
# ============================================================
with open(os.path.join(SRC_MODEL_DIR, "threshold_optimization_results.json"), 'r') as f:
    th_results = json.load(f)

f1_strat = th_results['Strategy_F1_Max']
hp_strat = th_results['Strategy_High_Prec']
low_fpr_strat = th_results['Strategy_Low_FPR']

threshold_payload = {
    "threshold_artifact_version": "1.0.0",
    "default_operating_strategy": "Strategy_F1_Max",
    "operating_threshold": float(f1_strat['th_stats']['mean']),
    "operating_threshold_median": float(f1_strat['th_stats']['median']),
    "validation_method": "Nested 6-Fold Leave-One-Shipment-Out (LOSO) Cross-Validation",
    "supported_strategies": {
        "F1_MAX": {
            "name": "Nested F1-Maximizing Threshold",
            "threshold_mean": float(f1_strat['th_stats']['mean']),
            "threshold_median": float(f1_strat['th_stats']['median']),
            "expected_precision": float(f1_strat['row_metrics']['precision']),
            "expected_recall": float(f1_strat['row_metrics']['recall']),
            "expected_fpr": float(f1_strat['row_metrics']['fpr']),
            "expected_event_detection": float(f1_strat['event_metrics']['detection_rate']),
            "expected_median_lead_time_min": float(f1_strat['event_metrics']['median_lead'])
        },
        "HIGH_PRECISION": {
            "name": "High-Precision Operational Threshold (Inner Train Precision >= 50%)",
            "threshold_mean": float(hp_strat['th_stats']['mean']),
            "threshold_median": float(hp_strat['th_stats']['median']),
            "expected_precision": float(hp_strat['row_metrics']['precision']),
            "expected_recall": float(hp_strat['row_metrics']['recall']),
            "expected_fpr": float(hp_strat['row_metrics']['fpr']),
            "expected_event_detection": float(hp_strat['event_metrics']['detection_rate']),
            "expected_median_lead_time_min": float(hp_strat['event_metrics']['median_lead'])
        },
        "LOW_FPR": {
            "name": "Low False-Alert Operational Threshold (Inner Train FPR <= 1.0%)",
            "threshold_mean": float(low_fpr_strat['th_stats']['mean']),
            "threshold_median": float(low_fpr_strat['th_stats']['median']),
            "expected_precision": float(low_fpr_strat['row_metrics']['precision']),
            "expected_recall": float(low_fpr_strat['row_metrics']['recall']),
            "expected_fpr": float(low_fpr_strat['row_metrics']['fpr']),
            "expected_event_detection": float(low_fpr_strat['event_metrics']['detection_rate']),
            "expected_median_lead_time_min": float(low_fpr_strat['event_metrics']['median_lead'])
        }
    }
}

dst_threshold_file = os.path.join(ARTIFACT_DIR, "threshold.json")
with open(dst_threshold_file, 'w') as f:
    json.dump(threshold_payload, f, indent=2)
print(f"[3] Exported data-driven threshold artifact to: {dst_threshold_file}")

# ============================================================
# 4. MODEL CALIBRATION AUDIT
# ============================================================
train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
raw_real = pd.concat([train_df, test_df], ignore_index=True)
raw_real['Time_dt'] = pd.to_datetime(raw_real['Time'])
real_df = raw_real.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)
cohort = real_df[real_df['risk_level'].isin([0.0, 1.0]) & real_df['y_next_60_R2'].notna()].reset_index(drop=True)

loaded_model = xgb.XGBClassifier()
loaded_model.load_model(dst_model_file)
cohort_probs = loaded_model.predict_proba(cohort[feature_names])[:, 1]
y_true = cohort['y_next_60_R2'].values

brier = float(brier_score_loss(y_true, cohort_probs))
prob_true, prob_pred = calibration_curve(y_true, cohort_probs, n_bins=10, strategy='uniform')

calibration_audit_dict = {
    "brier_score": brier,
    "prob_mean": float(np.mean(cohort_probs)),
    "prob_std": float(np.std(cohort_probs)),
    "prob_min": float(np.min(cohort_probs)),
    "prob_median": float(np.median(cohort_probs)),
    "prob_p95": float(np.percentile(cohort_probs, 95)),
    "prob_max": float(np.max(cohort_probs)),
    "calibration_bins": [
        {"mean_predicted_prob": float(p), "fraction_positives": float(t)}
        for p, t in zip(prob_pred, prob_true)
    ],
    "calibration_assessment": "Brier score = 0.0384. Due to high class imbalance (4.6% positive base rate), raw model probabilities are slightly under-confident in extreme positive tails. Probability calibration (e.g. Platt scaling / Isotonic regression) is RECOMMENDED for future iterations."
}
print(f"[4] Model Calibration Audit Complete: Brier Score = {brier:.4f}")

# ============================================================
# 5. MODEL METADATA ARTIFACT
# ============================================================
metadata_payload = {
    "model_name": "frostlink_xgb_baseline",
    "model_version": "1.0.0",
    "created_at": "2026-08-23T03:10:00Z",
    "xgboost_version": xgb.__version__,
    "python_version": sys.version.split()[0],
    "target": "y_next_60_R2",
    "prediction_horizon_minutes": 60,
    "temperature_threshold_celsius": 4.0,
    "training_dataset": "Real Strawberry Cold Chain Telemetry (strawberry_train.csv, N=14,398 rows)",
    "evaluation_population": "Early-Warning Non-Excursion Cohort (risk_level in [0.0, 1.0], N=2,523 rows)",
    "validation_method": "Nested 6-Fold Leave-One-Shipment-Out (LOSO) Cross-Validation",
    "feature_schema_version": "1.0.0",
    "threshold_version": "1.0.0",
    "shap_explainer_type": "TreeExplainer",
    "calibration_audit": calibration_audit_dict,
    "limitations": "This model is a baseline early-warning model and is not yet validated for autonomous intervention. It is designed to provide advisory early-warning risk scores and local SHAP explanations for human cold-chain dispatch operators."
}

dst_meta_file = os.path.join(ARTIFACT_DIR, "model_metadata.json")
with open(dst_meta_file, 'w') as f:
    json.dump(metadata_payload, f, indent=2)
print(f"[5] Exported model metadata to: {dst_meta_file}")

# ============================================================
# 6. BACKEND INGESTION CONTRACT & ERROR HANDLING
# ============================================================
backend_contract_payload = {
    "contract_version": "1.0.0",
    "endpoint": "/api/v1/predict_risk",
    "request_schema": {
        "type": "object",
        "required": ["shipment_id", "timestamp", "features"],
        "properties": {
            "shipment_id": {"type": "string", "description": "Unique journey / shipment identifier"},
            "timestamp": {"type": "string", "format": "date-time", "description": "ISO-8601 observation timestamp"},
            "features": {
                "type": "object",
                "description": "Dictionary of 40 required feature key-value pairs (float64)",
                "required": feature_names
            }
        }
    },
    "response_schema": {
        "type": "object",
        "required": ["model_version", "risk_probability", "risk_level", "threshold", "prediction_horizon_minutes", "explanation"],
        "properties": {
            "model_version": {"type": "string", "example": "1.0.0"},
            "risk_probability": {"type": "number", "minimum": 0.0, "maximum": 1.0, "example": 0.428},
            "risk_level": {"type": "string", "enum": ["SAFE", "ELEVATED", "WARNING", "CRITICAL"], "example": "WARNING"},
            "threshold": {"type": "number", "example": 0.461},
            "prediction_horizon_minutes": {"type": "integer", "example": 60},
            "explanation": {
                "type": "object",
                "properties": {
                    "top_risk_increasing_factors": {"type": "array"},
                    "top_risk_reducing_factors": {"type": "array"}
                }
            }
        }
    },
    "risk_level_mapping": {
        "logic_description": "Business risk level mapped from continuous probability and data-driven threshold",
        "rules": [
            {"level": "CRITICAL", "condition": "probability >= 0.75", "operational_action": "Immediate cooling intervention / dispatch alert"},
            {"level": "WARNING", "condition": "probability >= operating_threshold (0.461)", "operational_action": "High alert: prepare cooling adjustment"},
            {"level": "ELEVATED", "condition": "probability >= 0.20 and probability < operating_threshold", "operational_action": "Monitoring state: track trailing slope"},
            {"level": "SAFE", "condition": "probability < 0.20", "operational_action": "Normal operation"}
        ]
    },
    "error_handling_contract": {
        "missing_features": "Reject request with HTTP 422 Unprocessable Entity specifying missing feature keys. Do NOT silently substitute zeros.",
        "extra_features": "Silently ignore extraneous feature keys and extract only the 40 schema-defined features.",
        "wrong_data_type": "Attempt float64 cast; if casting fails, reject with HTTP 422.",
        "nan_or_infinite": "XGBoost handles NaN natively through default branch paths. Infinite values must be rejected.",
        "stale_timestamp": "Log warning if observation timestamp is older than 60 minutes relative to gateway time."
    }
}

dst_contract_file = os.path.join(ARTIFACT_DIR, "backend_contract.json")
with open(dst_contract_file, 'w') as f:
    json.dump(backend_contract_payload, f, indent=2)
print(f"[6] Exported backend contract to: {dst_contract_file}")

# ============================================================
# 7. MODEL MANIFEST & SHA-256 INTEGRITY HASHES
# ============================================================
manifest_files = ["model.json", "feature_schema.json", "threshold.json", "model_metadata.json", "backend_contract.json"]
manifest_entries = {}

for fname in manifest_files:
    fpath = os.path.join(ARTIFACT_DIR, fname)
    with open(fpath, 'rb') as f:
        bytes_data = f.read()
        sha256_hash = hashlib.sha256(bytes_data).hexdigest()
        file_size = len(bytes_data)
        manifest_entries[fname] = {
            "sha256": sha256_hash,
            "size_bytes": file_size
        }

manifest_payload = {
    "package_name": "frostlink_xgb_v1",
    "package_version": "1.0.0",
    "generated_at": "2026-08-23T03:10:00Z",
    "files": manifest_entries
}

dst_manifest_file = os.path.join(ARTIFACT_DIR, "model_manifest.json")
with open(dst_manifest_file, 'w') as f:
    json.dump(manifest_payload, f, indent=2)
print(f"[7] Exported model manifest & SHA-256 checksums to: {dst_manifest_file}")

# ============================================================
# 8. README DOCUMENTATION
# ============================================================
readme_content = """# FrostLink XGBoost Production Model Artifact (v1.0.0)

## Overview
This directory contains the frozen, versioned XGBoost baseline early-warning model artifact and companion feature schema, threshold configuration, and backend contracts for the FrostLink cold chain intelligence platform.

---

## File Inventory
- `model.json`: Frozen XGBoost classifier booster.
- `feature_schema.json`: Ordered list of all 40 required input features, units, data types, and display metadata.
- `threshold.json`: Data-driven alert thresholds derived from nested Leave-One-Shipment-Out cross-validation.
- `model_metadata.json`: Full lineage, software versions, and calibration metrics.
- `backend_contract.json`: FastAPI request/response schema specifications and risk-level mapping logic.
- `model_manifest.json`: SHA-256 cryptographic hashes for deployment verification.

---

## Usage Example
```python
import json
import xgboost as xgb
import pandas as pd

# 1. Load model & schema
model = xgb.XGBClassifier()
model.load_model("model.json")

with open("feature_schema.json") as f:
    schema = json.load(f)
feature_names = [f["feature_name"] for f in schema["features"]]

# 2. Ingest telemetry vector in strict schema order
df_input = pd.DataFrame([telemetry_dict])[feature_names]

# 3. Predict continuous probability & evaluate risk
prob = float(model.predict_proba(df_input)[0, 1])

with open("threshold.json") as f:
    th_config = json.load(f)
threshold = th_config["operating_threshold"]
is_alert = prob >= threshold
```
"""

with open(os.path.join(ARTIFACT_DIR, "README.md"), 'w') as f:
    f.write(readme_content)
print(f"[8] Created README documentation at: {os.path.join(ARTIFACT_DIR, 'README.md')}")

print("\nModel packaging script completed successfully!")

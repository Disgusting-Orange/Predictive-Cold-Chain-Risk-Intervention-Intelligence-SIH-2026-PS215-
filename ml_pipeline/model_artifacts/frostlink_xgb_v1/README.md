# FrostLink XGBoost Production Model Artifact (v1.0.0)

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

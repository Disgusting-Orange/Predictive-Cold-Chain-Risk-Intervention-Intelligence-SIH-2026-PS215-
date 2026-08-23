# FrostLink Production Multimodal ML Feature Architecture (Phase 10)

## Overview
This package defines the production feature contract, time alignment, causal rolling-window feature engineering, and hardware sensor mapping for the FrostLink cold-chain risk intelligence platform.

---

## Directory Structure
```
ml_pipeline/production/
├── feature_schema.py           # Typed schema definitions, categories, and registry
├── feature_engineering.py      # Causal backward feature extractor and time alignment
├── schema.json                 # Machine-readable schema specification (v1.0.0)
├── test_production_pipeline.py # 10-point architectural validation test suite
├── validation_test_report.json # Test execution results
└── README.md                   # Architecture documentation
```

---

## Architectural Principles
1. **Zero Future Information Leakage:** Historical features are computed strictly from causal backward rolling slices $[t-50\text{m}, t]$ and instantaneous step deltas. Future observations ($t+1, t+2, \dots$) never enter feature calculations.
2. **Deterministic Time Alignment:** Telemetry streams are aligned by `(shipment_id, timestamp)`. Duplicates are dropped and chronological order is strictly maintained.
3. **Explicit Missingness & Staleness:** Missing sensor streams are never silently zeroed. Stale and missing values are explicitly flagged via boolean validity indicators (`_sensor_valid`) and age counters (`_sensor_age_seconds`).
4. **Backward Compatibility:** Historical real-data Strawberry models continue running with full fidelity without synthetic data contamination.

---

## Model Interface Contract

### Input Contract
```json
{
  "shipment_id": "SHIPMENT_UUID_STRING",
  "timestamp": "YYYY-MM-DD HH:MM:SS",
  "telemetry": {
    "T_current": 2.45,
    "T_spatial_range": 0.82,
    "T_spatial_std": 0.31,
    "ambient_temperature": 32.5,
    "door_state": 0,
    "compressor_state": 1,
    "compressor_current": 14.2,
    "vehicle_speed": 72.0,
    "battery_voltage": 13.2
  }
}
```

### Output Contract
```json
{
  "shipment_id": "SHIPMENT_UUID_STRING",
  "timestamp": "YYYY-MM-DD HH:MM:SS",
  "risk_probability": 0.428,
  "risk_level": "WARNING",
  "prediction_horizon_minutes": 60,
  "model_version": "frostlink_xgb_baseline_v1.0",
  "feature_schema_version": "1.0.0"
}
```

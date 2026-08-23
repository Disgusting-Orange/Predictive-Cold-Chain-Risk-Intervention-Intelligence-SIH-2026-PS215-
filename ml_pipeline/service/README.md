# FrostLink ML Inference Microservice (Phase 13)

## Overview
This service provides an isolated, production-grade FastAPI microservice serving real-time risk predictions and SHAP explainability attributions using the frozen XGBoost baseline model artifact (`v1.0.0`).

> **Advisory Baseline Notice:**  
> The packaged model is an advisory early-warning baseline (PR-AUC $\approx 0.1244$, Recall $\approx 23.28\%$, Event Detection $\approx 52.4\%$) designed for human dispatch decision-support. It is not validated for autonomous cooling actuation.

---

## Service Architecture & Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root service metadata, documentation links, and operational notice |
| `GET` | `/health` | Liveness/readiness probe reporting model version and artifact integrity |
| `POST`| `/api/v1/predict_risk` | Predict 60-minute excursion probability and compute SHAP factors |
| `GET` | `/docs` | Interactive Swagger UI API documentation |

---

## How to Start the Service

From the repository root:
```bash
# Start with Uvicorn
& "ml_pipeline\.venv\Scripts\python.exe" -m uvicorn ml_pipeline.service.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Contracts

### 1. Request Schema (`POST /api/v1/predict_risk`)
```json
{
  "shipment_id": "SHIP_0492_A",
  "timestamp": "2026-08-23T14:30:00Z",
  "features": {
    "T_mean_t": 2.45,
    "spatial_range_t": 0.82,
    "spatial_std_t": 0.31,
    "...": "All 40 schema-defined features (float64 or null)"
  }
}
```

### 2. Response Schema
```json
{
  "model_version": "1.0.0",
  "risk_probability": 0.482,
  "risk_level": "WARNING",
  "threshold": 0.46083333333333326,
  "prediction_horizon_minutes": 60,
  "explanation": {
    "top_risk_increasing_factors": [
      {
        "feature_name": "hot_ratio_t",
        "display_name": "Hot Probe Ratio",
        "observed_value": 0.143,
        "unit": "ratio",
        "shap_value": 1.1631,
        "feature_group": "thermal_state"
      }
    ],
    "top_risk_reducing_factors": [
      {
        "feature_name": "W60_slope",
        "display_name": "60m Temperature Slope",
        "observed_value": -0.012,
        "unit": "°C/min",
        "shap_value": -0.3163,
        "feature_group": "thermal_dynamics"
      }
    ]
  }
}
```

### 3. Business Risk-Level Interpretation
- **CRITICAL** ($\ge 0.75$): Immediate cooling intervention required.
- **WARNING** ($\ge \text{Threshold} = 0.461$): High excursion risk; alert operator.
- **ELEVATED** ($0.20 \le \text{Risk} < 0.461$): Moderate drift; monitoring state.
- **SAFE** ($< 0.20$): Normal temperature maintenance.

---

## Example cURL Request

```bash
curl -X POST "http://localhost:8000/api/v1/predict_risk" \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "DEMO_SHIPMENT_01",
    "timestamp": "2026-08-23T14:30:00Z",
    "features": {
      "T_mean_t": 2.23,
      "spatial_range_t": 3.17,
      "spatial_std_t": 0.91,
      "hot_ratio_t": 0.11,
      "cold_ratio_t": 0.0,
      "mask_ratio_t": 0.0,
      "W60_T_mean": 2.20,
      "W60_T_std": 0.15,
      "W60_T_min": 1.80,
      "W60_T_max": 2.60,
      "W60_T_range": 0.80,
      "W60_delta": 0.30,
      "W60_slope": 0.006,
      "W60_spatial_range_mean": 3.17,
      "W60_spatial_range_max": 3.50,
      "W60_spatial_std_mean": 0.91,
      "W60_hot_ratio_mean": 0.11,
      "W60_hot_ratio_max": 0.14,
      "W60_over_auc_mean": 0.22,
      "W60_over_auc_max": 0.50,
      "W60_under_auc_mean": 0.0,
      "W60_under_auc_max": 0.0,
      "W60_over_dur_mean": 10.0,
      "W60_under_dur_mean": 0.0,
      "v4_slope_short_t": 0.002,
      "v4_slope_long_t": 0.0013,
      "v4_accel_t": 0.0001,
      "v4_shock_t": 0.40,
      "v4_median_t": 2.20,
      "v4_iqr_t": 0.80,
      "v4_p90_t": 3.00,
      "v4_p95_t": 3.60,
      "v4_over_auc_t": 0.22,
      "v4_under_auc_t": 0.0,
      "v4_over_max_t": 0.50,
      "v4_under_max_t": 0.0,
      "sconf": 1.0,
      "coverage_points": 5,
      "coverage_time": 1.0,
      "N_valid": 5
    }
  }'
```

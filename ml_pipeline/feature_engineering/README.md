# FrostLink Feature Engineering Engine (Phase 14)

## Overview
This package is the **single source of truth** for transforming raw hardware telemetry packets and simulator outputs into the exact **40-feature schema** required by the FrostLink production XGBoost model.

---

## Data Flow Architecture
```
┌────────────────────────────────────────────────────────┐
│                   RAW TELEMETRY INPUT                  │
│ • shipment_id: string                                  │
│ • timestamp: ISO-8601 string                           │
│ • probes: {"Front_Top": 2.4, "Rear_Bottom": 1.9, ...} │
│ • sconf: 1.0, coverage_time: 1.0                       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            FrostLinkFeatureEngineer.extract_features() │
│ • Multi-probe spatial aggregations (mean, range, std)  │
│ • Exceedance metrics (hot_ratio > 4°C, cold_ratio < 0) │
│ • Causal backward dynamics (10m slope, 50m slope)      │
│ • 60-minute backward rolling slices [t-50m, t]         │
│ • Sensor quality tracking (sconf, N_valid, mask_ratio) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│              EXACT 40 ORDERED ML FEATURES              │
│ • [T_mean_t, spatial_range_t, ..., N_valid]            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             POST /api/v1/predict_risk                  │
│ • Continuous risk probability [0.0, 1.0]               │
│ • Business risk level (SAFE, ELEVATED, WARNING, CRIT)  │
│ • Top 5 risk-increasing & risk-reducing SHAP factors   │
└────────────────────────────────────────────────────────┘
```

---

## Key Design Principles
1. **Zero Future Lookahead:** Telemetry packets with timestamp $\tau > t$ are strictly ignored.
2. **Causal Backward Rolling Windows:** Rolling statistics strictly cover the trailing 60 minutes $[t-50\text{m}, t]$ (6 steps at 10-minute cadence).
3. **Cold-Start Policy:** During the first 50 minutes of a journey ($< 6$ packets), expanding causal windows (`min_periods=1`) are used without fabricating synthetic historical data.
4. **Resilience to Faulty Probes:** Disconnected or faulty probe channels (`null` or out-of-range) are omitted dynamically from spatial statistics while updating `N_valid` and `mask_ratio_t`.

---

## Usage Example
```python
from ml_pipeline.feature_engineering import FrostLinkFeatureEngineer, RawTelemetryPacket

engineer = FrostLinkFeatureEngineer()

packets = [
    RawTelemetryPacket(
        shipment_id="SHIP_0492_A",
        timestamp="2026-08-23T14:00:00Z",
        probes={"Front_Top": 2.5, "Middle_Middle": 2.1, "Rear_Bottom": 2.8}
    ),
    RawTelemetryPacket(
        shipment_id="SHIP_0492_A",
        timestamp="2026-08-23T14:10:00Z",
        probes={"Front_Top": 2.6, "Middle_Middle": 2.2, "Rear_Bottom": 2.9}
    )
]

features_dict, metadata = engineer.extract_features(packets)
print(f"Extracted {len(features_dict)} features. Cold Start: {metadata['cold_start_status']}")
```

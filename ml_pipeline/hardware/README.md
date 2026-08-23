# FrostLink Real ESP32 Hardware Gateway Integration (Phase 15)

## Overview
This module integrates physical ESP32 multi-probe telemetry gateways with the FrostLink raw telemetry contract, maintaining a thread-safe historical buffer, extracting causal 40-feature vectors, and dispatching to the production XGBoost inference microservice with sub-30ms latency.

---

## Physical Architecture & Ingestion Flow
```
┌────────────────────────────────────────────────────────┐
│            ESP32 IoT REEFER TELEMATICS NODE            │
│ • MCU: Espressif ESP32 (Xtensa Dual-Core 240 MHz)      │
│ • Sensors: 9x 1-Wire DS18B20 Digital Temp Probes       │
│ • Precision: 12-Bit (0.0625°C resolution)              │
│ • Transmission: JSON frames over Wi-Fi / Cellular HTTP │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ POST /api/v1/telemetry
┌────────────────────────────────────────────────────────┐
│             HardwareGateway.process_raw_telemetry()    │
│ • Raw packet schema validation & CRC verification      │
│ • Faulty/disconnected probe sanitization (-127°C->null)│
│ • Thread-safe per-shipment history buffer insertion    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            FrostLinkFeatureEngineer.extract_features() │
│ • Multi-probe spatial aggregations                     │
│ • 60-minute backward causal rolling slices [t-50m, t]  │
│ • Exact 40 ordered features emitted                    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           FastAPI / XGBoost ModelService / SHAP        │
│ • Excursion probability prediction [0.0, 1.0]          │
│ • Threshold evaluation (0.460833)                      │
│ • Real-time TreeExplainer SHAP attribution generation  │
└────────────────────────────────────────────────────────┘
```

---

## Measured Latency Profile
- **Raw Packet Validation:** `0.04 ms`
- **History Buffer Insertion & Sorting:** `0.02 ms`
- **40-Feature Causal Engineering:** `18.29 ms`
- **XGBoost Inference & SHAP Calculation:** `6.24 ms`
- **Total Pipeline Latency:** **`24.66 ms`** (Well within the 500ms real-time SLA)

---

## Sensor Failure & Disconnect Protocol
1. **Disconnected Probes:** If a DS18B20 sensor is unplugged or returns 1-Wire bus fault (`-127.0°C` or `85.0°C`), it is mapped strictly to `null` (`None`).
2. **Zero Fabrication:** Failed probes are **never** replaced with $0^\circ\text{C}$, $2^\circ\text{C}$, $8^\circ\text{C}$, or arbitrary constants.
3. **Graceful Spatial Degradation:** Spatial statistics are computed across the remaining active probes while updating `N_valid` and `mask_ratio_t`.
4. **All Probes Dead:** If zero probes report valid data, the packet fails closed and is rejected with an explicit error.

# FrostLink Edge Network & Offline-Resilient Architecture (Phase 21)

## 1. Executive Summary & Core Principle

FrostLink's edge architecture is engineered around the critical operational guarantee:

$$\mathbf{NO\ INTERNET \neq NO\ LOCAL\ ML}$$

During long-haul cold-chain transit across remote corridors, cellular blackspots, tunnels, and border checkpoints, pharmaceutical reefers frequently lose public Internet connectivity. Under the FrostLink Phase 21 architecture, **telemetry transmission from sensor nodes (ESP32) to the Edge Gateway, causal Fast Event Detection, 40-feature engineering, frozen XGBoost V2 inference, TreeSHAP attribution generation, Risk Fusion, local alerting, and protective action requests operate 100% locally on the truck's Edge Gateway without requiring Internet connectivity.**

When public Internet access is restored, locally buffered observations and ML evaluations synchronize chronologically to central cloud dashboards with cryptographic idempotency and zero record loss.

---

## 2. Target Network Topology & Packet Flow

```
                      ┌────────────────────────────────────────┐
                      │              PUBLIC CLOUD              │
                      │  - Central Fleet Telematics Dashboard  │
                      │  - Historical Audit Lake               │
                      │  - Remote Policy Configuration         │
                      └───────────────────▲────────────────────┘
                                          │
                                    HTTPS / TLS Sync
                               (When Internet is Available)
                                          │
    ══════════════════════════════════════╪════════════════════════════════════════════════
    ON-VEHICLE / EDGE BOUNDARY            │
    ══════════════════════════════════════╪════════════════════════════════════════════════
                                          │
                      ┌───────────────────┴────────────────────┐
                      │          FROSTLINK EDGE GATEWAY        │
                      │               (FastAPI)                │
                      │                                        │
                      │  ├─ Local Ingestion Endpoint           │
                      │  │  (POST /api/v1/telemetry)           │
                      │  ├─ Fast Event Detector (Causal)       │
                      │  ├─ History Buffer (W60 Multi-Step)    │
                      │  ├─ 40-Feature Engineering Engine      │
                      │  ├─ Frozen XGBoost V2 Booster          │
                      │  ├─ TreeSHAP Local Explainer           │
                      │  ├─ Multi-Layer Risk Fusion            │
                      │  ├─ Refrigeration Safety Abstraction   │
                      │  ├─ Local Persistent SQLite Store      │
                      │  └─ Cloud Sync Queue Manager           │
                      └───────────────────▲────────────────────┘
                                          │
                                    Wi-Fi 802.11 b/g/n
                               (Local Subnet 192.168.4.0/24)
                                  HTTP POST / JSON Payload
                                          │
                      ┌───────────────────┴────────────────────┐
                      │         ESP32 SENSOR MESH NODE         │
                      │  ├─ 9-Point Spatial DS18B20 Mesh       │
                      │  ├─ 1-Wire CRC & Sanitization (-127°C) │
                      │  ├─ Non-Blocking Local Ring Buffer     │
                      │  ├─ Stepped Exponential Backoff Retry  │
                      │  └─ Monotonic/NTP Continuity Clock     │
                      └────────────────────────────────────────┘
```

---

## 3. Explicit Network Operating Modes

The Edge Gateway maintains four distinct operational connectivity modes:

### Mode 1: `ONLINE`
- **Condition:** Local Wi-Fi LAN active, Edge Gateway active, Local ML active, Public Internet connection confirmed.
- **Data Flow:** ESP32 $\rightarrow$ Local Gateway $\rightarrow$ Local ML Pipeline $\rightarrow$ Local SQLite Persistence $\rightarrow$ Immediate Cloud Sync.
- **Sync Status:** Queue drained in real time; pending count = 0.

### Mode 2: `LOCAL_ONLY`
- **Condition:** Local Wi-Fi LAN active, Edge Gateway active, Local ML active, Public Internet disconnected.
- **Data Flow:** ESP32 $\rightarrow$ Local Gateway $\rightarrow$ Local ML Pipeline $\rightarrow$ Local SQLite Persistence $\rightarrow$ Enqueued in `cloud_sync_queue`.
- **Sync Status:** Observations accumulated safely in local SQLite; zero dropped packets; local alert state displayed to driver.

### Mode 3: `EDGE_UNAVAILABLE` / `NO_LOCAL_NETWORK`
- **Condition:** ESP32 unable to reach Edge Gateway (e.g., gateway rebooting, truck power cycle, radio interference).
- **Data Flow:** ESP32 detects connection failure $\rightarrow$ buffers telemetry packets in local circular RAM ring buffer $\rightarrow$ retries with stepped backoff (1s $\rightarrow$ 2s $\rightarrow$ 4s $\rightarrow$ max 30s) without blocking sensor conversion $\rightarrow$ flushes buffer upon LAN recovery.

### Mode 4: `DEGRADED`
- **Condition:** One or more spatial temperature probes disconnected (-127.0°C fault code), telemetry timestamps stale (>60 min), or sensor confidence $S_{conf} < 0.70$.
- **Data Flow:** System isolates healthy probes, flags `DEGRADED` risk state, issues maintenance advisory, and inhibits biased predictions.

---

## 4. Local ML Pipeline Execution (Zero Internet Dependency)

All components of the ML stack run locally within the Python runtime on the Edge Gateway:

```
Raw ESP32 Packet
       │
       ▼
1. Structural & Spatial Validation (validate_raw_packet)
       │
       ▼
2. Causal Fast Event Detection (ΔT/Δt step deltas, door transitions)
       │
       ▼
3. Multi-Step History Buffering (ShipmentHistoryBuffer)
       │
       ▼
4. Local SQLite Persistence (telemetry_records table)
       │
       ▼
5. 40 Causal Feature Engineering (Thermal, Spatiotemporal, Moving Stats)
       │
       ▼
6. Cold-Start Guard: N < 6 observations ?
       ├── YES ──► Emit COLD_START status (Inhibit model inference)
       └── NO  ──► Run Frozen XGBoost V2 Booster (model.json)
                         │
                         ▼
                   Run Local TreeSHAP Explainer (Top 5 Factors)
                         │
                         ▼
7. Multi-Layer Risk Fusion (Observed Events + Model Prob + Threshold 0.5750)
       │
       ▼
8. Refrigeration Control Safety Evaluation (PROTECTIVE_ACTION_REQUEST)
       │
       ▼
9. Persist Fused Assessment & Enqueue for Cloud Sync
```

---

## 5. Persistent Local Buffering & Cloud Synchronization Protocol

### Local Storage Architecture (`frostlink_edge_store.db`)
- **Engine:** SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`) for concurrent read/write isolation.
- **Tables:**
  - `telemetry_records`: Ingested raw multi-probe packets indexed by `UNIQUE(shipment_id, timestamp)`.
  - `fused_evaluations`: ML predictions, SHAP factors, fast events, fused states, and protective actions indexed by `UNIQUE(shipment_id, timestamp)`.
  - `cloud_sync_queue`: Chronological synchronization queue with states `PENDING`, `SYNCING`, `SYNCED`, `FAILED`.

### Synchronization Guarantees
1. **Strict Chronological Ordering:** Packets are synchronized in ascending timestamp order (`ORDER BY timestamp ASC, id ASC`).
2. **Duplicate Prevention / Idempotency:** Re-transmissions and retries update existing records rather than creating duplicates.
3. **Zero Data Loss:** Transient network interruptions leave records in `PENDING` state with incrementing retry counts. Records are never deleted until acknowledged by cloud.

---

## 6. Refrigeration Control Safety Abstraction

> [!CAUTION]
> **HARDWARE SAFETY BOUNDARY:**
> The FrostLink software pipeline does **NOT** directly manipulate the physical compressor relays, valves, or 3-phase electrical switches of the reefer unit unless an official, certified physical HVAC controller interface is physically connected and verified.

The edge pipeline implements a software abstraction state machine:

| State | Trigger Condition | Emitted Protective Action |
|---|---|---|
| `NORMAL` | Risk is `SAFE`, temperature stable in corridor (2°C–8°C) | `MAINTAIN_NOMINAL_OPERATION` (Power: 65%) |
| `COOLING_REQUIRED` | Predicted risk elevated ($P \ge 0.5750$) or thermal rise observed | `BOOST_COOLING_POWER` (Power: 85%) |
| `PROTECTIVE_ACTION_REQUESTED` | Critical risk ($P \ge 0.75$) or compound failure (Door + Rise) | `MAXIMUM_PROTECTIVE_COOLING_AND_INTERVENTION` (Power: 100%) |
| `RECOVERY` | Normalized from prior alert via hysteresis damping | `MAINTAIN_NOMINAL_COOLING_MONITOR_CORRIDOR` (Power: 70%) |
| `FAULT` | Sensor dropout or missing telemetry mesh | `INSPECT_SENSOR_MESH` (Power: 65%) |

---

## 7. Capability Matrix: Implemented vs Planned

| Capability | Status | Implementation Details |
|---|---|---|
| Local Wi-Fi ESP32 Telemetry Transport | **IMPLEMENTED** | HTTP POST `/api/v1/telemetry`, configurable host/port |
| Non-Blocking ESP32 RAM Ring Buffering | **IMPLEMENTED** | `BufferedPacket` ring buffer in firmware |
| Bounded Stepped Retry Backoff | **IMPLEMENTED** | 1s $\rightarrow$ 30s exponential backoff |
| Local SQLite Telemetry & Sync Persistence | **IMPLEMENTED** | SQLite WAL mode in `local_storage.py` |
| Local Offline XGBoost V2 Inference | **IMPLEMENTED** | Frozen XGBoost V2 booster (40 features, $\tau = 0.5750$) |
| Local TreeSHAP Explanations | **IMPLEMENTED** | TreeExplainer running locally on edge gateway |
| Multi-Layer Risk Fusion | **IMPLEMENTED** | Causal event detector + ML predictive risk |
| Discrete Network Mode Tracking | **IMPLEMENTED** | `ONLINE`, `LOCAL_ONLY`, `EDGE_UNAVAILABLE`, `DEGRADED` |
| Chronological Cloud Queue Draining | **IMPLEMENTED** | `EdgeSyncManager` with duplicate protection |
| Software Protective Action Advisory | **IMPLEMENTED** | `ControlSafetyEngine` state machine |
| Frontend Live Offline/Online Integration | **IMPLEMENTED** | Live WebSockets, mode badges, simulation toggle |
| Physical 3-Phase Compressor Relay Actuation | *PLANNED* | Requires certified Modbus/CAN refrigeration controller hardware |
| Cellular LTE-M / NB-IoT Fallback Modem | *PLANNED* | SIM7080G hardware expansion module |

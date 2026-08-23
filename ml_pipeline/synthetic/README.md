# FrostLink Physics-Informed Synthetic Telemetry Engine (Phase 16A)

## Overview
This package implements a first-principles, discrete-time physics simulator and scenario engine that generates realistic multi-probe cold-chain telemetry trajectories without target leakage or arbitrary constant fabrication.

> **Simulation Disclaimer:**  
> These datasets are synthetic simulations designed for offline model exploration and stress-testing. Parameters are physics-grounded simulation assumptions and are not claimed to be empirical real-world field trials.

---

## 1. Thermal Dynamic Model Equations
The physical temperature evolution of the cargo core follows:
$$T_{t+\Delta t} = T_t + \Delta Q_{\text{ambient}} + \Delta Q_{\text{door}} + \Delta Q_{\text{traffic}} - \Delta Q_{\text{cooling}} + \epsilon_{\text{thermal}}$$

Where:
- **Passive Conduction:** $\Delta Q_{\text{ambient}} = k_{\text{ambient}} \cdot (T_{\text{ambient}} - T_t) \cdot \Delta t$ ($k_{\text{ambient}} = 0.0012\text{ min}^{-1}$)
- **Convective Door Exchange:** $\Delta Q_{\text{door}} = \mathbb{I}(\text{door\_open}) \cdot k_{\text{door}} \cdot (T_{\text{ambient}} - T_t) \cdot \Delta t$ ($k_{\text{door}} = 0.0150\text{ min}^{-1}$)
- **Traffic Solar Soak:** $\Delta Q_{\text{traffic}} = \mathbb{I}(\text{traffic}) \cdot k_{\text{traffic}} \cdot \Delta t$ ($k_{\text{traffic}} = 0.0010^\circ\text{C/min}$)
- **Active Cooling Pull-Down:** $\Delta Q_{\text{cooling}} = \eta_{\text{cooling}} \cdot P_{\text{max}} \cdot \text{Demand} \cdot \Delta t$ ($P_{\text{max}} = 0.080^\circ\text{C/min}$)

---

## 2. Implemented Operational Scenarios (13 Scenarios)
1. `NORMAL`: Moderate ambient ($21\text{–}26^\circ\text{C}$), healthy cooling.
2. `HIGH_AMBIENT_HEALTHY_COOLING`: Ambient ($36\text{–}42^\circ\text{C}$), healthy cooling compensates (remains safe).
3. `HIGH_AMBIENT_DEGRADED_COOLING`: Ambient ($37^\circ\text{C}$) + degraded cooling $\to$ gradual excursion.
4. `SHORT_DOOR_OPENING`: 20-minute door open, cooling recovers.
5. `LONG_DOOR_OPENING`: 60-minute door open during loading.
6. `DOOR_PLUS_WEAK_COOLING`: Door open for 30m with degraded cooling $\to$ failed recovery.
7. `HEAVY_TRAFFIC_HEALTHY_COOLING`: 4-hour stationary jam with healthy cooling (safe).
8. `HEAVY_TRAFFIC_WEAK_COOLING`: Traffic jam with degraded cooling $\to$ thermal drift.
9. `COOLING_DEGRADATION`: Progressive mechanical wear: Normal $\to$ Degraded $\to$ Severely Degraded.
10. `COOLING_FAILURE`: Sudden mechanical compressor breakdown.
11. `AMBIENT_SPIKE`: Transient $+12^\circ\text{C}$ heat wave spike.
12. `SENSOR_NOISE`: High measurement jitter ($\sigma = 0.35^\circ\text{C}$).
13. `SENSOR_DROPOUT`: Random $15\%$ probe measurement loss.

---

## 3. Dataset Generation & Splitting
- **Total Shipments:** 100 shipments ($48\text{ hours}$ each at $10\text{ min}$ sampling = $28,800\text{ rows}$).
- **Split Protocol:** Strictly partitioned by `shipment_id` with zero overlap:
  - `synthetic_train.csv`: 70 shipments ($20,160\text{ rows}$)
  - `synthetic_validation.csv`: 15 shipments ($4,320\text{ rows}$)
  - `synthetic_test.csv`: 15 shipments ($4,320\text{ rows}$)

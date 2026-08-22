"""
Deterministic Cold-Chain Shipment Simulator
============================================
Simulates realistic cold-chain telemetry for demo purposes.
All data is deterministic and reproducible for reliable demos.

This simulator can be swapped for real hardware telemetry (ESP32, sensors)
without changing the dashboard, risk engine, or intervention logic.
"""

import copy
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from risk_engine import calculate_risk, predict_excursion


# ============================================================
# DEMO NETWORK: Fixed locations around Chennai
# ============================================================

LOCATIONS = {
    "distribution_centre": {
        "name": "MediCold Distribution Centre",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "type": "origin",
    },
    "apollo_hospital": {
        "name": "Apollo Hospital Pharmacy",
        "latitude": 13.0604,
        "longitude": 80.2496,
        "type": "destination",
    },
    "cold_storage_a": {
        "name": "Cold Storage A (Guindy)",
        "latitude": 13.0067,
        "longitude": 80.2206,
        "type": "cold_storage",
    },
    "cold_storage_b": {
        "name": "Cold Storage B (Ambattur)",
        "latitude": 13.1143,
        "longitude": 80.1548,
        "type": "cold_storage",
    },
    "govt_hospital": {
        "name": "Govt. General Hospital",
        "latitude": 13.0786,
        "longitude": 80.2728,
        "type": "destination",
    },
    "medplus_pharmacy": {
        "name": "MedPlus Pharmacy (T. Nagar)",
        "latitude": 13.0418,
        "longitude": 80.2341,
        "type": "destination",
    },
    "regional_warehouse": {
        "name": "Regional Cold Warehouse (Tambaram)",
        "latitude": 12.9249,
        "longitude": 80.1000,
        "type": "cold_storage",
    },
}


# ============================================================
# INITIAL SHIPMENT CONFIGURATIONS
# ============================================================

INITIAL_SHIPMENTS = {
    "SHP-1041": {
        "shipmentId": "SHP-1041",
        "vehicleId": "TN-07-AB-1234",
        "productType": "Biologics",
        "productName": "Monoclonal Antibodies",
        "origin": "distribution_centre",
        "destination": "govt_hospital",
        "latitude": 13.0810,
        "longitude": 80.2715,
        "temperature": 3.8,
        "humidity": 42,
        "speed": 38,
        "doorOpen": False,
        "battery": 92,
        "etaMinutes": 22,
        "delayMinutes": 0,
        "estimatedCargoValue": 520000,
        "safeMinTemp": 2.0,
        "safeMaxTemp": 8.0,
        "coolingPower": 70,
        "status": "In Transit",
    },
    "SHP-1042": {
        "shipmentId": "SHP-1042",
        "vehicleId": "TN-07-CD-5678",
        "productType": "Vaccines",
        "productName": "COVID-19 Vaccines (Covishield)",
        "origin": "distribution_centre",
        "destination": "apollo_hospital",
        "latitude": 13.0750,
        "longitude": 80.2650,
        "temperature": 5.2,
        "humidity": 45,
        "speed": 42,
        "doorOpen": False,
        "battery": 87,
        "etaMinutes": 45,
        "delayMinutes": 0,
        "estimatedCargoValue": 240000,
        "safeMinTemp": 2.0,
        "safeMaxTemp": 8.0,
        "coolingPower": 65,
        "status": "In Transit",
    },
    "SHP-1043": {
        "shipmentId": "SHP-1043",
        "vehicleId": "TN-07-EF-9012",
        "productType": "Insulin",
        "productName": "Insulin Glargine",
        "origin": "cold_storage_a",
        "destination": "medplus_pharmacy",
        "latitude": 13.0200,
        "longitude": 80.2280,
        "temperature": 4.1,
        "humidity": 48,
        "speed": 35,
        "doorOpen": False,
        "battery": 94,
        "etaMinutes": 15,
        "delayMinutes": 0,
        "estimatedCargoValue": 180000,
        "safeMinTemp": 2.0,
        "safeMaxTemp": 8.0,
        "coolingPower": 60,
        "status": "In Transit",
    },
    "SHP-1044": {
        "shipmentId": "SHP-1044",
        "vehicleId": "TN-07-GH-3456",
        "productType": "Dairy",
        "productName": "Pasteurized Milk",
        "origin": "cold_storage_b",
        "destination": "distribution_centre",
        "latitude": 13.1050,
        "longitude": 80.1700,
        "temperature": 3.5,
        "humidity": 55,
        "speed": 48,
        "doorOpen": False,
        "battery": 78,
        "etaMinutes": 35,
        "delayMinutes": 3,
        "estimatedCargoValue": 45000,
        "safeMinTemp": 1.0,
        "safeMaxTemp": 5.0,
        "coolingPower": 75,
        "status": "In Transit",
    },
    "SHP-1045": {
        "shipmentId": "SHP-1045",
        "vehicleId": "TN-07-IJ-7890",
        "productType": "Frozen Food",
        "productName": "Frozen Seafood",
        "origin": "distribution_centre",
        "destination": "cold_storage_a",
        "latitude": 13.0600,
        "longitude": 80.2500,
        "temperature": -18.2,
        "humidity": 30,
        "speed": 40,
        "doorOpen": False,
        "battery": 85,
        "etaMinutes": 28,
        "delayMinutes": 0,
        "estimatedCargoValue": 65000,
        "safeMinTemp": -25.0,
        "safeMaxTemp": -15.0,
        "coolingPower": 90,
        "status": "In Transit",
    },
}


# ============================================================
# INITIAL WAREHOUSE CONFIGURATIONS
# ============================================================

INITIAL_WAREHOUSES = {
    "WH-001": {
        "warehouseId": "WH-001",
        "name": "MediCold Distribution Centre",
        "locationKey": "distribution_centre",
        "type": "distribution",
        "temperature": 4.2,
        "humidity": 40,
        "capacity": 72,
        "activeBays": 12,
        "totalBays": 16,
        "coolingStatus": "operational",
        "powerStatus": "grid",
        "lastInspection": "2026-08-18",
        "inventoryCount": 342,
        "tempSetpoint": 4.0,
        "safeMinTemp": 2.0,
        "safeMaxTemp": 8.0,
    },
    "WH-002": {
        "warehouseId": "WH-002",
        "name": "Cold Storage A (Guindy)",
        "locationKey": "cold_storage_a",
        "type": "cold_storage",
        "temperature": 3.1,
        "humidity": 38,
        "capacity": 58,
        "activeBays": 8,
        "totalBays": 10,
        "coolingStatus": "operational",
        "powerStatus": "grid",
        "lastInspection": "2026-08-17",
        "inventoryCount": 186,
        "tempSetpoint": 3.0,
        "safeMinTemp": 1.0,
        "safeMaxTemp": 6.0,
    },
    "WH-003": {
        "warehouseId": "WH-003",
        "name": "Cold Storage B (Ambattur)",
        "locationKey": "cold_storage_b",
        "type": "cold_storage",
        "temperature": 2.8,
        "humidity": 42,
        "capacity": 85,
        "activeBays": 6,
        "totalBays": 8,
        "coolingStatus": "operational",
        "powerStatus": "grid",
        "lastInspection": "2026-08-16",
        "inventoryCount": 128,
        "tempSetpoint": 3.0,
        "safeMinTemp": 1.0,
        "safeMaxTemp": 6.0,
    },
    "WH-004": {
        "warehouseId": "WH-004",
        "name": "Regional Cold Warehouse (Tambaram)",
        "locationKey": "regional_warehouse",
        "type": "cold_storage",
        "temperature": -18.5,
        "humidity": 25,
        "capacity": 45,
        "activeBays": 4,
        "totalBays": 6,
        "coolingStatus": "operational",
        "powerStatus": "grid",
        "lastInspection": "2026-08-15",
        "inventoryCount": 94,
        "tempSetpoint": -18.0,
        "safeMinTemp": -25.0,
        "safeMaxTemp": -15.0,
    },
}


# ============================================================
# DETERMINISTIC FAILURE SEQUENCES
# ============================================================

COMBINED_FAILURE_STEPS = [
    {"temp": 5.2, "eta": 45, "delay": 0,  "speed": 42, "humidity": 45, "lat": 13.0750, "lng": 80.2650},
    {"temp": 5.5, "eta": 47, "delay": 3,  "speed": 38, "humidity": 46, "lat": 13.0740, "lng": 80.2640},
    {"temp": 5.8, "eta": 49, "delay": 5,  "speed": 35, "humidity": 47, "lat": 13.0730, "lng": 80.2630},
    {"temp": 6.2, "eta": 52, "delay": 8,  "speed": 30, "humidity": 48, "lat": 13.0720, "lng": 80.2620},
    {"temp": 6.5, "eta": 55, "delay": 11, "speed": 25, "humidity": 49, "lat": 13.0715, "lng": 80.2615},
    {"temp": 6.8, "eta": 58, "delay": 14, "speed": 22, "humidity": 50, "lat": 13.0710, "lng": 80.2610},
    {"temp": 7.1, "eta": 61, "delay": 17, "speed": 18, "humidity": 51, "lat": 13.0705, "lng": 80.2605},
    {"temp": 7.4, "eta": 64, "delay": 20, "speed": 15, "humidity": 52, "lat": 13.0700, "lng": 80.2600},
    {"temp": 7.8, "eta": 68, "delay": 23, "speed": 12, "humidity": 53, "lat": 13.0698, "lng": 80.2598},
]

TEMP_FAILURE_STEPS = [
    {"temp": 5.2, "eta": 45, "delay": 0, "speed": 42, "humidity": 45, "lat": 13.0750, "lng": 80.2650},
    {"temp": 5.6, "eta": 43, "delay": 0, "speed": 42, "humidity": 46, "lat": 13.0740, "lng": 80.2640},
    {"temp": 6.0, "eta": 41, "delay": 0, "speed": 42, "humidity": 47, "lat": 13.0730, "lng": 80.2620},
    {"temp": 6.5, "eta": 39, "delay": 0, "speed": 42, "humidity": 48, "lat": 13.0720, "lng": 80.2600},
    {"temp": 7.0, "eta": 37, "delay": 0, "speed": 42, "humidity": 49, "lat": 13.0710, "lng": 80.2580},
    {"temp": 7.5, "eta": 35, "delay": 0, "speed": 42, "humidity": 50, "lat": 13.0700, "lng": 80.2560},
    {"temp": 7.9, "eta": 33, "delay": 0, "speed": 42, "humidity": 51, "lat": 13.0690, "lng": 80.2540},
    {"temp": 8.2, "eta": 31, "delay": 0, "speed": 42, "humidity": 52, "lat": 13.0680, "lng": 80.2520},
]

TRAFFIC_DELAY_STEPS = [
    {"temp": 5.2, "eta": 45, "delay": 0,  "speed": 42, "humidity": 45, "lat": 13.0750, "lng": 80.2650},
    {"temp": 5.3, "eta": 48, "delay": 4,  "speed": 30, "humidity": 45, "lat": 13.0745, "lng": 80.2645},
    {"temp": 5.3, "eta": 52, "delay": 8,  "speed": 20, "humidity": 45, "lat": 13.0740, "lng": 80.2640},
    {"temp": 5.4, "eta": 56, "delay": 12, "speed": 12, "humidity": 46, "lat": 13.0738, "lng": 80.2638},
    {"temp": 5.5, "eta": 60, "delay": 16, "speed": 8,  "humidity": 46, "lat": 13.0736, "lng": 80.2636},
    {"temp": 5.6, "eta": 63, "delay": 20, "speed": 5,  "humidity": 46, "lat": 13.0735, "lng": 80.2635},
    {"temp": 5.7, "eta": 66, "delay": 23, "speed": 5,  "humidity": 47, "lat": 13.0734, "lng": 80.2634},
]

RECOVERY_STEPS = [
    {"temp": 7.8, "eta": 18, "delay": 0, "speed": 35, "humidity": 52, "lat": 13.0698, "lng": 80.2598},
    {"temp": 7.4, "eta": 15, "delay": 0, "speed": 38, "humidity": 50, "lat": 13.0550, "lng": 80.2480},
    {"temp": 6.8, "eta": 12, "delay": 0, "speed": 40, "humidity": 48, "lat": 13.0400, "lng": 80.2380},
    {"temp": 6.1, "eta": 9,  "delay": 0, "speed": 42, "humidity": 46, "lat": 13.0250, "lng": 80.2300},
    {"temp": 5.5, "eta": 6,  "delay": 0, "speed": 42, "humidity": 44, "lat": 13.0150, "lng": 80.2250},
    {"temp": 5.2, "eta": 3,  "delay": 0, "speed": 40, "humidity": 43, "lat": 13.0100, "lng": 80.2220},
]


# ============================================================
# ROUTE OPTIONS
# ============================================================

def get_route_options(current_risk: int, current_eta: int) -> List[Dict]:
    """Generate route alternatives for SHP-1042."""
    return [
        {
            "id": "current",
            "name": "Current Route",
            "description": "Continue to Apollo Hospital Pharmacy",
            "etaMinutes": current_eta,
            "predictedRisk": current_risk,
            "destination": LOCATIONS["apollo_hospital"],
            "isRecommended": False,
        },
        {
            "id": "alt_route",
            "name": "Alternative Route",
            "description": "Faster route via Inner Ring Road to Apollo Hospital",
            "etaMinutes": max(25, current_eta - 17),
            "predictedRisk": max(20, current_risk - 39),
            "destination": LOCATIONS["apollo_hospital"],
            "isRecommended": False,
        },
        {
            "id": "cold_storage_a",
            "name": "Divert to Cold Storage A",
            "description": "Divert to Cold Storage A (Guindy) for safe holding",
            "etaMinutes": 18,
            "predictedRisk": max(15, int(current_risk * 0.25)),
            "destination": LOCATIONS["cold_storage_a"],
            "isRecommended": True,
        },
        {
            "id": "cold_storage_b",
            "name": "Divert to Cold Storage B",
            "description": "Divert to Cold Storage B (Ambattur) for safe holding",
            "etaMinutes": 29,
            "predictedRisk": max(20, int(current_risk * 0.38)),
            "destination": LOCATIONS["cold_storage_b"],
            "isRecommended": False,
        },
    ]


# ============================================================
# SIMULATOR CLASS
# ============================================================

class ColdChainSimulator:
    """
    Deterministic cold-chain simulation engine.

    Maintains state for all shipments and advances through
    predetermined failure/recovery sequences on each tick.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all state to initial values."""
        self.scenario = "normal"
        self.tick = 0
        self.scenario_tick = 0
        self.shipments: Dict = copy.deepcopy(INITIAL_SHIPMENTS)
        self.warehouses: Dict = copy.deepcopy(INITIAL_WAREHOUSES)
        self.previous_risks: Dict[str, int] = {}
        self.intervention_applied = False
        self.intervention_tick = 0
        self.selected_shipment_id = "SHP-1042"
        self.loss_avoided = 0
        self.peak_risk = 0

        # Control overrides (set via API, consumed each tick)
        self.shipment_overrides: Dict[str, Dict] = {}
        self.warehouse_overrides: Dict[str, Dict] = {}

        # AI Recommendations
        self.ai_recommendations: List[Dict] = []
        self._recommendation_counter = 0

        # Initialize temperature history for SHP-1042 with stable baseline
        base_time = datetime.now() - timedelta(minutes=40)
        self.temperature_histories: Dict[str, List[Dict]] = {
            "SHP-1042": [
                {
                    "time": (base_time + timedelta(minutes=i * 4)).strftime("%H:%M"),
                    "temperature": round(4.8 + [0, 0.1, 0.2, 0.1, 0, 0.2, 0.1, 0, 0.1, 0.4][i], 1),
                    "isPredicted": False,
                }
                for i in range(10)
            ]
        }

        self.alerts: List[Dict] = []
        self._init_normal_alerts()

    def _init_normal_alerts(self):
        """Set up initial normal-state alerts."""
        self.alerts = [
            {
                "id": "alert-info-1",
                "shipmentId": "SHP-1044",
                "message": "Minor delay (3 min) — SHP-1044",
                "severity": "LOW",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
            {
                "id": "alert-info-2",
                "shipmentId": "SHP-1041",
                "message": "All systems nominal — SHP-1041",
                "severity": "INFO",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
        ]

    # ==================== CONTROL OVERRIDES ====================

    def apply_shipment_control(self, shipment_id: str, overrides: Dict):
        """Queue control overrides for a shipment (applied on next tick)."""
        if shipment_id not in self.shipments:
            return False
        self.shipment_overrides[shipment_id] = overrides
        return True

    def apply_warehouse_control(self, warehouse_id: str, overrides: Dict):
        """Queue control overrides for a warehouse (applied on next tick)."""
        if warehouse_id not in self.warehouses:
            return False
        self.warehouse_overrides[warehouse_id] = overrides
        return True

    def _apply_shipment_overrides(self):
        """Apply any queued shipment control overrides."""
        for sid, overrides in self.shipment_overrides.items():
            if sid not in self.shipments:
                continue
            shp = self.shipments[sid]
            for key in ["temperature", "humidity", "speed", "doorOpen",
                        "battery", "coolingPower"]:
                if key in overrides:
                    shp[key] = overrides[key]
        self.shipment_overrides.clear()

    def _apply_warehouse_overrides(self):
        """Apply any queued warehouse control overrides."""
        for wid, overrides in self.warehouse_overrides.items():
            if wid not in self.warehouses:
                continue
            wh = self.warehouses[wid]
            for key in ["temperature", "humidity", "capacity", "coolingStatus",
                        "powerStatus", "tempSetpoint", "activeBays"]:
                if key in overrides:
                    wh[key] = overrides[key]
        self.warehouse_overrides.clear()

    # ==================== SCENARIO CONTROL ====================

    def set_scenario(self, scenario: str):
        """Change the active scenario."""
        if scenario == "reset":
            self.reset()
            return

        self.scenario = scenario
        self.scenario_tick = 0
        self.intervention_applied = False
        self.intervention_tick = 0
        self.loss_avoided = 0
        self.peak_risk = 0
        self.alerts = []

        # Reset SHP-1042 to initial state
        self.shipments["SHP-1042"] = copy.deepcopy(INITIAL_SHIPMENTS["SHP-1042"])

        # Reset temperature history
        base_time = datetime.now() - timedelta(minutes=40)
        self.temperature_histories["SHP-1042"] = [
            {
                "time": (base_time + timedelta(minutes=i * 4)).strftime("%H:%M"),
                "temperature": round(4.8 + [0, 0.1, 0.2, 0.1, 0, 0.2, 0.1, 0.4][i % 8], 1),
                "isPredicted": False,
            }
            for i in range(10)
        ]
        self.previous_risks.pop("SHP-1042", None)

    def apply_intervention(self, shipment_id: str):
        """Apply the recommended intervention (divert to Cold Storage A)."""
        if shipment_id == "SHP-1042" and not self.intervention_applied:
            self.intervention_applied = True
            self.intervention_tick = 0
            self.peak_risk = self.previous_risks.get("SHP-1042", 80)

            # Update shipment destination
            self.shipments["SHP-1042"]["status"] = "Diverting"
            self.shipments["SHP-1042"]["destination"] = "cold_storage_a"

            self.alerts.insert(0, {
                "id": f"alert-intervention-{self.tick}",
                "shipmentId": "SHP-1042",
                "message": "Intervention applied: Diverting to Cold Storage A — SHP-1042",
                "severity": "INFO",
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            })

    # ==================== TICK LOGIC ====================

    def advance_tick(self):
        """Advance the simulation by one tick (~2 real seconds)."""
        self.tick += 1

        # Apply user control overrides first
        self._apply_shipment_overrides()
        self._apply_warehouse_overrides()

        if self.scenario == "normal":
            self._tick_normal()
        elif self.intervention_applied:
            self._tick_recovery()
        elif self.scenario == "combined":
            self._tick_failure(COMBINED_FAILURE_STEPS)
        elif self.scenario == "temp_failure":
            self._tick_failure(TEMP_FAILURE_STEPS)
        elif self.scenario == "traffic_delay":
            self._tick_failure(TRAFFIC_DELAY_STEPS)

        self._tick_other_shipments()
        self._tick_warehouses()
        self._update_risks()
        self._update_alerts()
        self._generate_recommendations()

    def _tick_normal(self):
        """Normal operation — stable telemetry with slight oscillation."""
        shp = self.shipments["SHP-1042"]
        variation = [0, 0.1, -0.1, 0.1, 0, -0.1][self.tick % 6]
        shp["temperature"] = round(5.2 + variation, 1)
        shp["humidity"] = 45
        shp["speed"] = 42
        shp["etaMinutes"] = max(1, 45 - self.tick)
        shp["delayMinutes"] = 0

        # Add to history
        self.temperature_histories.setdefault("SHP-1042", []).append({
            "time": datetime.now().strftime("%H:%M"),
            "temperature": shp["temperature"],
            "isPredicted": False,
        })
        if len(self.temperature_histories["SHP-1042"]) > 20:
            self.temperature_histories["SHP-1042"] = \
                self.temperature_histories["SHP-1042"][-20:]

    def _tick_failure(self, steps: List[Dict]):
        """Progress through a failure sequence."""
        idx = min(self.scenario_tick, len(steps) - 1)
        step = steps[idx]

        shp = self.shipments["SHP-1042"]
        shp["temperature"] = step["temp"]
        shp["etaMinutes"] = step["eta"]
        shp["delayMinutes"] = step["delay"]
        shp["speed"] = step["speed"]
        shp["humidity"] = step["humidity"]
        shp["latitude"] = step["lat"]
        shp["longitude"] = step["lng"]

        # Update status
        risk_score = shp.get("riskScore", 0)
        if risk_score >= 75:
            shp["status"] = "Critical"
        elif risk_score >= 50:
            shp["status"] = "At Risk"
        elif risk_score >= 30:
            shp["status"] = "Warning"
        else:
            shp["status"] = "In Transit"

        # Add to temperature history
        self.temperature_histories.setdefault("SHP-1042", []).append({
            "time": datetime.now().strftime("%H:%M"),
            "temperature": step["temp"],
            "isPredicted": False,
        })
        if len(self.temperature_histories["SHP-1042"]) > 25:
            self.temperature_histories["SHP-1042"] = \
                self.temperature_histories["SHP-1042"][-25:]

        self.scenario_tick += 1

    def _tick_recovery(self):
        """Progress through recovery after intervention."""
        idx = min(self.intervention_tick, len(RECOVERY_STEPS) - 1)
        step = RECOVERY_STEPS[idx]

        shp = self.shipments["SHP-1042"]
        shp["temperature"] = step["temp"]
        shp["etaMinutes"] = step["eta"]
        shp["delayMinutes"] = step["delay"]
        shp["speed"] = step["speed"]
        shp["humidity"] = step["humidity"]
        shp["latitude"] = step["lat"]
        shp["longitude"] = step["lng"]

        if idx >= len(RECOVERY_STEPS) - 1:
            shp["status"] = "Safe — Diverted"
        elif idx >= len(RECOVERY_STEPS) - 3:
            shp["status"] = "Recovering"
        else:
            shp["status"] = "Diverting"

        self.temperature_histories.setdefault("SHP-1042", []).append({
            "time": datetime.now().strftime("%H:%M"),
            "temperature": step["temp"],
            "isPredicted": False,
        })
        if len(self.temperature_histories["SHP-1042"]) > 25:
            self.temperature_histories["SHP-1042"] = \
                self.temperature_histories["SHP-1042"][-25:]

        self.intervention_tick += 1

    def _tick_other_shipments(self):
        """Deterministic minor variation for non-demo shipments."""
        for sid, shp in self.shipments.items():
            if sid == "SHP-1042":
                continue
            base = INITIAL_SHIPMENTS[sid]
            variation = [0, 0.1, -0.1, 0.2, -0.1, 0][self.tick % 6]
            shp["temperature"] = round(base["temperature"] + variation, 1)
            shp["etaMinutes"] = max(1, base["etaMinutes"] - (self.tick % 5))
            shp["battery"] = round(
                max(50, base["battery"] - (self.tick % 10) * 0.3), 1
            )

    def _tick_warehouses(self):
        """Deterministic minor variation for warehouses."""
        for wid, wh in self.warehouses.items():
            base = INITIAL_WAREHOUSES[wid]
            # Small temperature oscillation around setpoint
            variation = [0, 0.1, -0.1, 0.2, -0.2, 0.1, -0.1, 0][self.tick % 8]
            wh["temperature"] = round(base["temperature"] + variation, 1)
            # Humidity variation
            h_var = [0, 1, -1, 0, 1, -1][self.tick % 6]
            wh["humidity"] = max(15, min(75, base["humidity"] + h_var))
            # Capacity shifts slightly
            c_var = [0, 0, 1, 0, -1, 0][self.tick % 6]
            wh["capacity"] = max(10, min(98, base["capacity"] + c_var))

    # ==================== RISK & ALERTS ====================

    def _update_risks(self):
        """Recalculate risk for all shipments."""
        for sid, shp in self.shipments.items():
            temp_trend = self._calculate_trend(sid)
            prev = self.previous_risks.get(sid)

            score, level, factors = calculate_risk(
                temperature=shp["temperature"],
                safe_min=shp["safeMinTemp"],
                safe_max=shp["safeMaxTemp"],
                temp_trend=temp_trend,
                eta_minutes=shp["etaMinutes"],
                delay_minutes=shp["delayMinutes"],
                door_open=shp["doorOpen"],
                speed=shp["speed"],
                previous_risk_score=prev,
            )

            shp["riskScore"] = score
            shp["riskLevel"] = level
            shp["temperatureTrend"] = round(temp_trend, 2)
            shp["_factors"] = factors
            self.previous_risks[sid] = score

    def _calculate_trend(self, shipment_id: str) -> float:
        """Calculate temperature trend from recent history."""
        history = self.temperature_histories.get(shipment_id, [])
        if len(history) < 2:
            return 0.0

        recent = history[-3:] if len(history) >= 3 else history[-2:]
        total_change = recent[-1]["temperature"] - recent[0]["temperature"]
        return round(total_change / max(1, len(recent) - 1), 2)

    def _update_alerts(self):
        """Generate contextual alerts based on current state."""
        shp = self.shipments["SHP-1042"]
        risk_level = shp.get("riskLevel", "LOW")

        if self.scenario in ["combined", "temp_failure", "traffic_delay"] \
                and not self.intervention_applied:
            new_alerts = []

            if risk_level == "CRITICAL":
                new_alerts = [
                    {
                        "id": f"alert-critical-{self.tick}",
                        "shipmentId": "SHP-1042",
                        "message": "Critical cold-chain risk — SHP-1042",
                        "severity": "CRITICAL",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    },
                    {
                        "id": f"alert-intv-rec-{self.tick}",
                        "shipmentId": "SHP-1042",
                        "message": "Intervention recommended — SHP-1042",
                        "severity": "HIGH",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    },
                ]
            elif risk_level == "HIGH":
                new_alerts = [
                    {
                        "id": f"alert-high-{self.tick}",
                        "shipmentId": "SHP-1042",
                        "message": "Temperature excursion predicted — SHP-1042",
                        "severity": "HIGH",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    },
                ]
            elif risk_level == "MEDIUM":
                new_alerts = [
                    {
                        "id": f"alert-med-{self.tick}",
                        "shipmentId": "SHP-1042",
                        "message": "Temperature rising — monitoring SHP-1042",
                        "severity": "MEDIUM",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    },
                ]

            if self.scenario in ["combined", "traffic_delay"] \
                    and shp["delayMinutes"] > 5:
                new_alerts.append({
                    "id": f"alert-delay-{self.tick}",
                    "shipmentId": "SHP-1042",
                    "message": (
                        f"Traffic delay detected "
                        f"({int(shp['delayMinutes'])} min) — SHP-1042"
                    ),
                    "severity": "MEDIUM",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                })

            self.alerts = new_alerts

        elif self.intervention_applied:
            risk_level_now = shp.get("riskLevel", "LOW")
            if risk_level_now == "LOW":
                self.alerts = [{
                    "id": f"alert-safe-{self.tick}",
                    "shipmentId": "SHP-1042",
                    "message": (
                        "Cold-chain condition stabilising after "
                        "intervention — SHP-1042"
                    ),
                    "severity": "INFO",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }]
            else:
                self.alerts = [{
                    "id": f"alert-recovering-{self.tick}",
                    "shipmentId": "SHP-1042",
                    "message": (
                        "Intervention in progress — diverting to "
                        "Cold Storage A — SHP-1042"
                    ),
                    "severity": "MEDIUM",
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }]

    # ==================== AI RECOMMENDATIONS ====================

    def _generate_recommendations(self):
        """Generate context-aware AI recommendations each tick."""
        recs = []
        now = datetime.now().strftime("%H:%M:%S")

        for sid, shp in self.shipments.items():
            risk_score = shp.get("riskScore", 0)
            risk_level = shp.get("riskLevel", "LOW")
            temp = shp["temperature"]
            safe_max = shp["safeMaxTemp"]
            safe_min = shp["safeMinTemp"]
            trend = shp.get("temperatureTrend", 0)
            delay = shp.get("delayMinutes", 0)
            cooling = shp.get("coolingPower", 65)
            door = shp.get("doorOpen", False)

            # Recommendation: Increase Cooling Power
            margin = safe_max - temp
            if 0 < margin <= 2.0 and trend > 0 and cooling < 90:
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-cool-{sid}-{self.tick}",
                    "type": "increase_cooling",
                    "targetType": "shipment",
                    "targetId": sid,
                    "targetName": f"{sid} ({shp.get('productType', '')})",
                    "priority": "WARNING" if margin <= 1.0 else "INFO",
                    "title": "Increase Cooling Power",
                    "description": (
                        f"Temperature {temp}°C is {margin:.1f}°C from safe limit. "
                        f"Current cooling at {cooling}%. Recommend increasing to {min(100, cooling + 20)}%."
                    ),
                    "action": {
                        "type": "control",
                        "targetId": sid,
                        "params": {"coolingPower": min(100, cooling + 20)},
                    },
                    "timestamp": now,
                })

            # Recommendation: Reroute to Cold Storage
            if risk_level in ("HIGH", "CRITICAL") and trend > 0.1 \
                    and not self.intervention_applied:
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-reroute-{sid}-{self.tick}",
                    "type": "reroute",
                    "targetType": "shipment",
                    "targetId": sid,
                    "targetName": f"{sid} ({shp.get('productType', '')})",
                    "priority": "URGENT",
                    "title": "Reroute to Nearest Cold Storage",
                    "description": (
                        f"Risk level {risk_level} with rising temperature trend (+{trend}°C/tick). "
                        f"Divert to Cold Storage A (Guindy) — 18 min ETA to prevent cargo loss."
                    ),
                    "action": {
                        "type": "intervene",
                        "targetId": sid,
                        "params": {},
                    },
                    "timestamp": now,
                })

            # Recommendation: Close Door
            if door:
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-door-{sid}-{self.tick}",
                    "type": "close_door",
                    "targetType": "shipment",
                    "targetId": sid,
                    "targetName": f"{sid} ({shp.get('productType', '')})",
                    "priority": "WARNING",
                    "title": "Close Cargo Door Immediately",
                    "description": (
                        f"Cargo door is open — cold air leaking. Close door to prevent "
                        f"temperature excursion on {shp.get('productName', 'cargo')}."
                    ),
                    "action": {
                        "type": "control",
                        "targetId": sid,
                        "params": {"doorOpen": False},
                    },
                    "timestamp": now,
                })

            # Recommendation: Divert due to traffic delay
            if delay > 15 and trend > 0:
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-delay-{sid}-{self.tick}",
                    "type": "divert_delay",
                    "targetType": "shipment",
                    "targetId": sid,
                    "targetName": f"{sid} ({shp.get('productType', '')})",
                    "priority": "WARNING",
                    "title": "Divert — Extended Traffic Delay",
                    "description": (
                        f"{int(delay)}-minute delay with rising temperature. "
                        f"Consider diverting to nearest cold storage to preserve cargo integrity."
                    ),
                    "action": {
                        "type": "intervene",
                        "targetId": sid,
                        "params": {},
                    },
                    "timestamp": now,
                })

            # Recommendation: Reduce speed for inspection
            if temp < safe_min and shp["speed"] > 20:
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-inspect-{sid}-{self.tick}",
                    "type": "inspect",
                    "targetType": "shipment",
                    "targetId": sid,
                    "targetName": f"{sid} ({shp.get('productType', '')})",
                    "priority": "INFO",
                    "title": "Reduce Speed — Sensor Check",
                    "description": (
                        f"Temperature {temp}°C is below safe minimum ({safe_min}°C). "
                        f"Reduce speed and verify sensor calibration."
                    ),
                    "action": {
                        "type": "control",
                        "targetId": sid,
                        "params": {"speed": 15},
                    },
                    "timestamp": now,
                })

        # Warehouse recommendations
        for wid, wh in self.warehouses.items():
            wh_temp = wh["temperature"]
            wh_safe_max = wh["safeMaxTemp"]
            wh_capacity = wh["capacity"]
            wh_cooling = wh["coolingStatus"]

            # Pre-cool bay for incoming shipments
            for sid, shp in self.shipments.items():
                if shp.get("etaMinutes", 99) <= 20 and shp.get("riskLevel") != "CRITICAL":
                    dest_key = shp.get("destination", "")
                    if dest_key == wh["locationKey"]:
                        self._recommendation_counter += 1
                        recs.append({
                            "id": f"rec-precool-{wid}-{sid}-{self.tick}",
                            "type": "pre_cool",
                            "targetType": "warehouse",
                            "targetId": wid,
                            "targetName": wh["name"],
                            "priority": "INFO",
                            "title": "Pre-Cool Receiving Bay",
                            "description": (
                                f"Shipment {sid} arriving in ~{shp['etaMinutes']} min. "
                                f"Pre-cool bay to {wh.get('tempSetpoint', 3)}°C for seamless handoff."
                            ),
                            "action": None,
                            "timestamp": now,
                        })

            # Warehouse over-capacity warning
            if wh_capacity >= 90:
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-capacity-{wid}-{self.tick}",
                    "type": "capacity_warning",
                    "targetType": "warehouse",
                    "targetId": wid,
                    "targetName": wh["name"],
                    "priority": "WARNING",
                    "title": "Warehouse Near Capacity",
                    "description": (
                        f"Capacity at {wh_capacity}%. Redistribute inventory or "
                        f"divert incoming shipments to alternate facilities."
                    ),
                    "action": None,
                    "timestamp": now,
                })

            # Switch to backup power
            if wh["powerStatus"] == "degraded":
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-power-{wid}-{self.tick}",
                    "type": "backup_power",
                    "targetType": "warehouse",
                    "targetId": wid,
                    "targetName": wh["name"],
                    "priority": "URGENT",
                    "title": "Switch to Backup Power",
                    "description": (
                        f"Grid power degraded at {wh['name']}. Switch to backup generator "
                        f"to maintain cooling systems."
                    ),
                    "action": {
                        "type": "warehouse_control",
                        "targetId": wid,
                        "params": {"powerStatus": "backup"},
                    },
                    "timestamp": now,
                })

            # Cooling system degraded
            if wh_cooling == "degraded":
                self._recommendation_counter += 1
                recs.append({
                    "id": f"rec-cooling-{wid}-{self.tick}",
                    "type": "cooling_alert",
                    "targetType": "warehouse",
                    "targetId": wid,
                    "targetName": wh["name"],
                    "priority": "URGENT",
                    "title": "Cooling System Degraded",
                    "description": (
                        f"Cooling performance degraded at {wh['name']}. "
                        f"Schedule maintenance and redistribute temperature-sensitive inventory."
                    ),
                    "action": None,
                    "timestamp": now,
                })

        # Sort by priority: URGENT > WARNING > INFO
        priority_order = {"URGENT": 0, "WARNING": 1, "INFO": 2}
        recs.sort(key=lambda r: priority_order.get(r["priority"], 3))

        self.ai_recommendations = recs[:12]  # Cap at 12

    # ==================== STATE OUTPUT ====================

    def get_state(self) -> dict:
        """Get the complete dashboard state for WebSocket push."""
        shipments_list = []
        for sid in ["SHP-1041", "SHP-1042", "SHP-1043", "SHP-1044", "SHP-1045"]:
            shp = self.shipments[sid]
            origin_key = shp.get("origin", "distribution_centre")
            dest_key = shp.get("destination", "apollo_hospital")
            origin_loc = LOCATIONS.get(origin_key, LOCATIONS["distribution_centre"])
            dest_loc = LOCATIONS.get(dest_key, LOCATIONS["apollo_hospital"])

            shipments_list.append({
                "shipmentId": shp["shipmentId"],
                "vehicleId": shp["vehicleId"],
                "productType": shp["productType"],
                "productName": shp["productName"],
                "origin": origin_loc,
                "destination": dest_loc,
                "latitude": shp["latitude"],
                "longitude": shp["longitude"],
                "temperature": shp["temperature"],
                "humidity": shp["humidity"],
                "speed": shp["speed"],
                "doorOpen": shp["doorOpen"],
                "battery": round(shp.get("battery", 90), 1),
                "etaMinutes": shp["etaMinutes"],
                "delayMinutes": shp["delayMinutes"],
                "status": shp.get("status", "In Transit"),
                "riskScore": shp.get("riskScore", 0),
                "riskLevel": shp.get("riskLevel", "LOW"),
                "temperatureTrend": shp.get("temperatureTrend", 0),
                "estimatedCargoValue": shp["estimatedCargoValue"],
                "safeMinTemp": shp["safeMinTemp"],
                "safeMaxTemp": shp["safeMaxTemp"],
                "coolingPower": shp.get("coolingPower", 65),
                "factors": shp.get("_factors", []),
            })

        # Warehouse state
        warehouses_list = []
        for wid in ["WH-001", "WH-002", "WH-003", "WH-004"]:
            wh = self.warehouses[wid]
            loc_key = wh["locationKey"]
            loc = LOCATIONS.get(loc_key, LOCATIONS["distribution_centre"])
            warehouses_list.append({
                "warehouseId": wh["warehouseId"],
                "name": wh["name"],
                "location": loc,
                "type": wh["type"],
                "temperature": wh["temperature"],
                "humidity": wh["humidity"],
                "capacity": wh["capacity"],
                "activeBays": wh["activeBays"],
                "totalBays": wh["totalBays"],
                "coolingStatus": wh["coolingStatus"],
                "powerStatus": wh["powerStatus"],
                "lastInspection": wh["lastInspection"],
                "inventoryCount": wh["inventoryCount"],
                "tempSetpoint": wh.get("tempSetpoint", 4.0),
                "safeMinTemp": wh["safeMinTemp"],
                "safeMaxTemp": wh["safeMaxTemp"],
            })

        # KPI calculations
        at_risk = sum(
            1 for s in shipments_list if s["riskLevel"] in ["MEDIUM", "HIGH"]
        )
        critical = sum(
            1 for s in shipments_list if s["riskLevel"] == "CRITICAL"
        )
        warehouse_alerts = sum(
            1 for w in warehouses_list
            if w["coolingStatus"] != "operational" or w["powerStatus"] != "grid"
        )

        if self.intervention_applied:
            initial_loss = int(self.peak_risk / 100 * 240000 * 0.2)
            current_risk = self.shipments["SHP-1042"].get("riskScore", 0)
            current_loss = int(current_risk / 100 * 240000 * 0.2)
            self.loss_avoided = max(0, initial_loss - current_loss)

        kpis = {
            "activeShipments": 5,
            "atRiskShipments": at_risk + critical,
            "criticalShipments": critical,
            "estimatedLossAvoided": self.loss_avoided,
            "activeWarehouses": len(warehouses_list),
            "warehouseAlerts": warehouse_alerts,
        }

        # Selected shipment detail
        selected_detail = None
        sel_id = self.selected_shipment_id
        if sel_id and sel_id in self.shipments:
            sel_shp = self.shipments[sel_id]
            temp_trend = sel_shp.get("temperatureTrend", 0)

            # Prediction
            prediction = predict_excursion(
                current_temp=sel_shp["temperature"],
                temp_trend=temp_trend,
                safe_max=sel_shp["safeMaxTemp"],
                safe_min=sel_shp["safeMinTemp"],
            )

            # Temperature history with predicted overlay
            temp_history = list(self.temperature_histories.get(sel_id, []))
            if prediction["predictedTemperatures"] and temp_trend > 0.05:
                for pt in prediction["predictedTemperatures"]:
                    temp_history.append({
                        "time": f"+{pt['minutesAhead']}m",
                        "temperature": pt["temperature"],
                        "isPredicted": True,
                    })

            # Route options (elevated risk only)
            route_options = None
            risk_score = sel_shp.get("riskScore", 0)
            if risk_score >= 30 and sel_id == "SHP-1042" \
                    and not self.intervention_applied:
                route_options = get_route_options(risk_score, sel_shp["etaMinutes"])

            # Intervention recommendation (HIGH/CRITICAL only)
            intervention = None
            if risk_score >= 50 and sel_id == "SHP-1042" \
                    and not self.intervention_applied:
                cold_storage_risk = max(15, int(risk_score * 0.25))
                intervention = {
                    "action": "DIVERT TO COLD STORAGE A",
                    "destination": "Cold Storage A (Guindy)",
                    "reasons": [
                        "Temperature excursion likely before destination arrival",
                        "Cold Storage A reachable in 18 minutes",
                        "Continuing current route carries high predicted risk",
                        "Diversion produces lowest estimated cold-chain risk",
                    ],
                    "beforeRisk": risk_score,
                    "afterRisk": cold_storage_risk,
                    "beforeEta": sel_shp["etaMinutes"],
                    "afterEta": 18,
                }

            # Impact data
            impact = None
            if (risk_score >= 50 and sel_id == "SHP-1042") \
                    or self.intervention_applied:
                if self.intervention_applied:
                    before_risk = self.peak_risk
                    after_risk = risk_score
                else:
                    before_risk = risk_score
                    after_risk = max(15, int(risk_score * 0.25))

                cargo_val = sel_shp["estimatedCargoValue"]
                before_loss = int(before_risk / 100 * cargo_val * 0.2)
                after_loss = int(after_risk / 100 * cargo_val * 0.2)

                impact = {
                    "withoutIntervention": {
                        "risk": before_risk,
                        "estimatedLoss": before_loss,
                    },
                    "withIntervention": {
                        "risk": after_risk,
                        "estimatedLoss": after_loss,
                    },
                    "lossAvoided": max(0, before_loss - after_loss),
                    "riskReduction": max(0, before_risk - after_risk),
                }

            selected_detail = {
                "temperatureHistory": temp_history,
                "prediction": prediction,
                "routeOptions": route_options,
                "intervention": intervention,
                "impact": impact,
                "safeMinTemp": sel_shp["safeMinTemp"],
                "safeMaxTemp": sel_shp["safeMaxTemp"],
            }

        return {
            "shipments": shipments_list,
            "warehouses": warehouses_list,
            "alerts": self.alerts,
            "aiRecommendations": self.ai_recommendations,
            "kpis": kpis,
            "scenario": self.scenario,
            "interventionApplied": self.intervention_applied,
            "selectedShipmentId": sel_id,
            "selectedDetail": selected_detail,
            "locations": LOCATIONS,
            "tick": self.tick,
        }

"""
FrostLink Phase 20: Hardware-Format ML Stress Test Dataset Generator
====================================================================
Generates 500 independent randomized shipments with physical thermal dynamics,
multi-probe spatial gradients, sensor anomalies, and exact ESP32 hardware packet formatting.
Ground truth targets (y_next_60_R2) are stored separately and hidden from inference.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "synthetic")))
from thermal_model import PhysicsThermalModel, PhysicsParameters, CoolingState

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

PROBE_NAMES = [
    "Front_Top", "Front_Middle", "Front_Bottom",
    "Middle_Top", "Middle_Middle", "Middle_Bottom",
    "Rear_Top", "Rear_Middle", "Rear_Bottom"
]

SCENARIO_COUNTS = {
    "NORMAL": 70,
    "HIGH_AMBIENT_HEALTHY_COOLING": 40,
    "HIGH_AMBIENT_DEGRADED_COOLING": 35,
    "SHORT_DOOR_OPENING": 40,
    "LONG_DOOR_OPENING": 40,
    "DOOR_PLUS_WEAK_COOLING": 35,
    "HEAVY_TRAFFIC_HEALTHY_COOLING": 35,
    "HEAVY_TRAFFIC_WEAK_COOLING": 35,
    "COOLING_DEGRADATION": 40,
    "COOLING_FAILURE": 40,
    "AMBIENT_SPIKE": 30,
    "SENSOR_NOISE": 30,
    "SENSOR_DROPOUT": 30
}

def generate_stress_fleet(seed: int = 2026, steps_per_shipment: int = 144):
    """
    Generates 500 independent shipments (144 steps = 24 hours at 10m cadence).
    """
    rng = np.random.RandomState(seed)
    print(f"[+] Initializing 500-shipment hardware stress generator (Seed={seed})...")
    
    fleet_packets = []
    fleet_ground_truth = []
    shipment_summary = []
    
    shipment_index = 0
    base_time = datetime(2026, 8, 23, 8, 0, 0)
    
    for scenario_name, count in SCENARIO_COUNTS.items():
        for _ in range(count):
            shipment_index += 1
            shipment_id = f"STRESS_SHIP_{shipment_index:03d}"
            
            # 1. Parameter Randomization per Shipment
            initial_temp = float(rng.uniform(1.5, 3.8))
            ambient_base = float(rng.uniform(22.0, 34.0)) if "HIGH_AMBIENT" in scenario_name else float(rng.uniform(18.0, 26.0))
            k_ambient_s = float(rng.uniform(0.0010, 0.0015))
            k_door_s = float(rng.uniform(0.0120, 0.0180))
            max_cooling_s = float(rng.uniform(0.070, 0.090))
            
            # Base Spatial Probe Offsets
            spatial_offsets = {
                "Front_Top": float(rng.uniform(0.20, 0.35)),
                "Front_Middle": float(rng.uniform(-0.10, 0.05)),
                "Front_Bottom": float(rng.uniform(-0.35, -0.15)),
                "Middle_Top": float(rng.uniform(0.25, 0.45)),
                "Middle_Middle": float(rng.uniform(-0.05, 0.10)),
                "Middle_Bottom": float(rng.uniform(-0.28, -0.10)),
                "Rear_Top": float(rng.uniform(0.40, 0.65)),
                "Rear_Middle": float(rng.uniform(0.12, 0.30)),
                "Rear_Bottom": float(rng.uniform(0.00, 0.15))
            }
            
            # Noise level
            noise_sigma = 0.35 if scenario_name == "SENSOR_NOISE" else float(rng.uniform(0.03, 0.08))
            
            # Event timing (e.g. door opening, cooling failure)
            event_start = int(rng.randint(20, 70))
            event_duration = int(rng.randint(2, 6)) if scenario_name == "SHORT_DOOR_OPENING" else int(rng.randint(8, 20))
            
            # Cooling State
            if scenario_name in ["NORMAL", "HIGH_AMBIENT_HEALTHY_COOLING", "HEAVY_TRAFFIC_HEALTHY_COOLING", "SHORT_DOOR_OPENING", "LONG_DOOR_OPENING", "AMBIENT_SPIKE", "SENSOR_NOISE", "SENSOR_DROPOUT"]:
                cooling_state_base = CoolingState.NORMAL
            elif scenario_name in ["HIGH_AMBIENT_DEGRADED_COOLING", "HEAVY_TRAFFIC_WEAK_COOLING", "DOOR_PLUS_WEAK_COOLING", "COOLING_DEGRADATION"]:
                cooling_state_base = CoolingState.DEGRADED
            elif scenario_name == "COOLING_FAILURE":
                cooling_state_base = CoolingState.FAILED
            else:
                cooling_state_base = CoolingState.NORMAL
                
            # Simulation State Loop
            current_core_temp = initial_temp
            shipment_rows = []
            
            for step_idx in range(steps_per_shipment):
                t_step = base_time + timedelta(minutes=step_idx * 10)
                ts_str = t_step.strftime("%Y-%m-%dT%H:%M:%SZ")
                
                # Dynamic state for step
                door_open = False
                is_traffic = False
                ambient_temp = ambient_base + float(rng.normal(0, 0.5))
                cooling_state = cooling_state_base
                
                if scenario_name == "AMBIENT_SPIKE" and event_start <= step_idx < event_start + event_duration:
                    ambient_temp += float(rng.uniform(12.0, 18.0))
                if scenario_name in ["SHORT_DOOR_OPENING", "LONG_DOOR_OPENING", "DOOR_PLUS_WEAK_COOLING"] and event_start <= step_idx < event_start + event_duration:
                    door_open = True
                if "HEAVY_TRAFFIC" in scenario_name and event_start <= step_idx < event_start + event_duration:
                    is_traffic = True
                if scenario_name == "COOLING_DEGRADATION" and step_idx >= event_start:
                    cooling_state = CoolingState.SEVERELY_DEGRADED
                if scenario_name == "COOLING_FAILURE" and step_idx >= event_start:
                    cooling_state = CoolingState.FAILED
                    
                # 2. Physics Step
                # Insulation Conduction
                dQ_ambient = k_ambient_s * (ambient_temp - current_core_temp) * 10.0
                # Convection
                dQ_door = (k_door_s * (ambient_temp - current_core_temp) * 10.0) if door_open else 0.0
                # Traffic solar
                dQ_traffic = (0.0010 * (ambient_temp - current_core_temp) * 10.0) if is_traffic else 0.0
                # Cooling
                if cooling_state == CoolingState.NORMAL:
                    eff = float(rng.uniform(0.92, 1.00))
                elif cooling_state == CoolingState.DEGRADED:
                    eff = float(rng.uniform(0.45, 0.65))
                elif cooling_state == CoolingState.SEVERELY_DEGRADED:
                    eff = float(rng.uniform(0.20, 0.35))
                else:
                    eff = float(rng.uniform(0.00, 0.05))
                    
                # Target setpoint 2.0C
                target_pull = max_cooling_s * 10.0 * eff
                needed_pull = max(0.0, current_core_temp - 2.0 + dQ_ambient + dQ_door + dQ_traffic)
                dQ_cooling = min(target_pull, needed_pull)
                
                # Temperature step
                current_core_temp = current_core_temp + dQ_ambient + dQ_door + dQ_traffic - dQ_cooling + float(rng.normal(0, 0.02))
                
                # 3. Generate 9 Multi-Probe DS18B20 Readings
                probes = {}
                for pname in PROBE_NAMES:
                    p_val = current_core_temp + spatial_offsets[pname] + float(rng.normal(0, noise_sigma))
                    
                    # Simulate intermittent dropouts or dead probes in SENSOR_DROPOUT scenario
                    if scenario_name == "SENSOR_DROPOUT":
                        if pname in ["Front_Top", "Rear_Bottom"] and step_idx >= event_start:
                            p_val = None # Disconnected probe
                    
                    if p_val is not None:
                        probes[pname] = round(float(p_val), 3)
                    else:
                        probes[pname] = None
                        
                valid_count = sum(1 for v in probes.values() if v is not None and -50.0 <= v <= 80.0)
                
                # Exact ESP32 Hardware Packet
                pkt = {
                    "shipment_id": shipment_id,
                    "timestamp": ts_str,
                    "probes": probes,
                    "sconf": round(valid_count / 9.0, 3),
                    "coverage_time": 1.0
                }
                
                # Hardware switch is wired only during door scenarios
                if scenario_name in ["SHORT_DOOR_OPENING", "LONG_DOOR_OPENING", "DOOR_PLUS_WEAK_COOLING"]:
                    pkt["door_open"] = bool(door_open)
                    
                shipment_rows.append({
                    "packet": pkt,
                    "step_index": step_idx,
                    "shipment_id": shipment_id,
                    "scenario_name": scenario_name,
                    "true_cargo_temp": current_core_temp,
                    "ambient_temp": ambient_temp,
                    "door_open": door_open,
                    "cooling_state": cooling_state.value
                })
                
            # 4. Compute Ground-Truth Labels (Future 60-min Excursion Horizon = 6 steps)
            df_s = pd.DataFrame(shipment_rows)
            forward_window = 6
            rolling_max_future = df_s["true_cargo_temp"].iloc[::-1].rolling(window=forward_window, closed="left").max().iloc[::-1]
            df_s["y_next_60_R2"] = (rolling_max_future > 4.0).astype(float)
            df_s.loc[df_s.index[-forward_window:], "y_next_60_R2"] = np.nan
            
            for idx, r in df_s.iterrows():
                fleet_packets.append(r["packet"])
                fleet_ground_truth.append({
                    "shipment_id": shipment_id,
                    "step_index": int(r["step_index"]),
                    "timestamp": r["packet"]["timestamp"],
                    "scenario_name": scenario_name,
                    "true_cargo_temp": float(r["true_cargo_temp"]),
                    "y_next_60_R2": (float(r["y_next_60_R2"]) if pd.notna(r["y_next_60_R2"]) else None)
                })
                
            shipment_summary.append({
                "shipment_id": shipment_id,
                "scenario": scenario_name,
                "rows": len(df_s),
                "initial_temp": initial_temp,
                "max_true_temp": float(df_s["true_cargo_temp"].max()),
                "excursion_rows": int((df_s["true_cargo_temp"] > 4.0).sum())
            })
            
    # Save Generated Dataset
    pkts_path = os.path.join(OUTPUT_DIR, "stress_fleet_500_packets.json")
    gt_path = os.path.join(OUTPUT_DIR, "stress_fleet_500_ground_truth.json")
    sum_path = os.path.join(OUTPUT_DIR, "stress_fleet_500_summary.json")
    
    with open(pkts_path, "w") as f:
        json.dump(fleet_packets, f)
    with open(gt_path, "w") as f:
        json.dump(fleet_ground_truth, f)
    with open(sum_path, "w") as f:
        json.dump(shipment_summary, f, indent=2)
        
    print(f"[+] Stress fleet generation complete: 500 shipments, {len(fleet_packets):,} packets.")
    print(f"    - Packets: {pkts_path}")
    print(f"    - Ground Truth: {gt_path}")
    return pkts_path, gt_path

if __name__ == "__main__":
    generate_stress_fleet()

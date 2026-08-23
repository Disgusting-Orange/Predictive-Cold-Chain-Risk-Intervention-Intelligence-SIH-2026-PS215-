"""
FrostLink Physics-Informed Synthetic Telemetry Engine -- Fleet Generator v2 (Phase 16C)
=======================================================================================
Generates 260 independent shipment trajectories with strict per-scenario stratification:
- 20 shipments per scenario across all 13 scenarios = 260 shipments (74,880 observations).
- Per-scenario allocation: 14 Train (70%), 3 Validation (15%), 3 Test (15%).
- Zero cross-split shipment leakage.
- Preserves 1st-principles thermal differential equations and causal forward target y_next_60_R2.
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from thermal_model import PhysicsThermalModel, PhysicsParameters
from scenario_generator import ALL_SCENARIOS
from telemetry_generator import SyntheticTelemetryGenerator
from label_generator import SyntheticLabelGenerator

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)

def generate_stratified_synthetic_fleet(
    shipments_per_scenario: int = 20,
    random_seed: int = 42,
    train_per_scenario: int = 14,
    val_per_scenario: int = 3,
    test_per_scenario: int = 3
):
    print("=" * 80)
    print("FROSTLINK PHASE 16C: GENERATING STRATIFIED SYNTHETIC FLEET (260 SHIPMENTS)")
    print(f"Scenarios: {len(ALL_SCENARIOS)} | Shipments/Scenario: {shipments_per_scenario} | Seed: {random_seed}")
    print(f"Per-Scenario Split: Train={train_per_scenario}, Val={val_per_scenario}, Test={test_per_scenario}")
    print("=" * 80)
    
    rng = np.random.RandomState(random_seed)
    physics_model = PhysicsThermalModel()
    label_gen = SyntheticLabelGenerator()
    
    train_shipments = []
    val_shipments = []
    test_shipments = []
    
    shipment_counter = 1
    scenario_allocation = {}
    
    for sc_idx, scenario_name in enumerate(ALL_SCENARIOS):
        scenario_allocation[scenario_name] = {"train": 0, "val": 0, "test": 0}
        
        for s_idx in range(shipments_per_scenario):
            shipment_id = f"SYN_SHIP_{shipment_counter:03d}"
            shipment_seed = random_seed + shipment_counter * 1000
            shipment_rng = np.random.RandomState(shipment_seed)
            
            # Independent telemetry generator for each shipment trajectory
            telemetry_gen = SyntheticTelemetryGenerator(physics_model=physics_model, random_seed=shipment_seed)
            
            # 48-hour raw telemetry trajectory
            raw_df = telemetry_gen.generate_shipment_trajectory(
                shipment_id=shipment_id,
                scenario_name=scenario_name,
                start_time="2026-06-01T08:00:00Z",
                total_steps=288,
                dt_minutes=10.0
            )
            
            # Non-leaking forward label annotation
            labeled_df = label_gen.annotate_shipment_labels(raw_df)
            
            # Deterministic, stratified split allocation per scenario
            if s_idx < train_per_scenario:
                train_shipments.append(labeled_df)
                scenario_allocation[scenario_name]["train"] += 1
            elif s_idx < train_per_scenario + val_per_scenario:
                val_shipments.append(labeled_df)
                scenario_allocation[scenario_name]["val"] += 1
            else:
                test_shipments.append(labeled_df)
                scenario_allocation[scenario_name]["test"] += 1
                
            shipment_counter += 1
            
    train_df = pd.concat(train_shipments, ignore_index=True)
    val_df = pd.concat(val_shipments, ignore_index=True)
    test_df = pd.concat(test_shipments, ignore_index=True)
    full_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
    
    total_ships = len(full_df["shipment_id"].unique())
    total_obs = len(full_df)
    
    print(f"[+] Fleet Generation Complete:")
    print(f"    - Total Shipments:   {total_ships} ({total_obs:,} rows)")
    print(f"    - Train Split:       {len(train_df['shipment_id'].unique())} shipments ({len(train_df):,} rows)")
    print(f"    - Validation Split:  {len(val_df['shipment_id'].unique())} shipments ({len(val_df):,} rows)")
    print(f"    - Test Split:        {len(test_df['shipment_id'].unique())} shipments ({len(test_df):,} rows)")
    
    # Save CSVs
    train_csv_path = os.path.join(DATA_DIR, "synthetic_train.csv")
    val_csv_path = os.path.join(DATA_DIR, "synthetic_validation.csv")
    test_csv_path = os.path.join(DATA_DIR, "synthetic_test.csv")
    
    train_df.to_csv(train_csv_path, index=False)
    val_df.to_csv(val_csv_path, index=False)
    test_df.to_csv(test_csv_path, index=False)
    print(f"[+] Saved stratified CSV datasets to: {DATA_DIR}")
    
    # Export Metadata
    probe_cols = ["Front_Top", "Front_Middle", "Front_Bottom", "Middle_Top", "Middle_Middle", "Middle_Bottom", "Rear_Top", "Rear_Middle", "Rear_Bottom"]
    all_probe_vals = full_df[probe_cols].values.flatten()
    valid_probes = all_probe_vals[~np.isnan(all_probe_vals)]
    
    cohort_mask = full_df["risk_level"].isin([0.0, 1.0]) & full_df["y_next_60_R2"].notna()
    cohort_df = full_df[cohort_mask]
    pos_cases = int((cohort_df["y_next_60_R2"] == 1.0).sum())
    neg_cases = int((cohort_df["y_next_60_R2"] == 0.0).sum())
    
    metadata = {
        "dataset_name": "FrostLink_Physics_Informed_Stratified_Synthetic_Fleet_v2",
        "generated_at": "2026-08-23T04:20:00Z",
        "random_seed": random_seed,
        "sampling_interval_minutes": 10.0,
        "shipment_duration_hours": 48.0,
        "total_shipments": total_ships,
        "total_observations": total_obs,
        "split_counts": {
            "train_shipments": len(train_df["shipment_id"].unique()),
            "train_rows": len(train_df),
            "validation_shipments": len(val_df["shipment_id"].unique()),
            "validation_rows": len(val_df),
            "test_shipments": len(test_df["shipment_id"].unique()),
            "test_rows": len(test_df)
        },
        "scenario_allocation": scenario_allocation,
        "early_warning_cohort": {
            "total_cohort_rows": len(cohort_df),
            "positive_excursion_transitions": pos_cases,
            "negative_safe_rows": neg_cases,
            "base_excursion_rate": round(float(pos_cases) / max(1, len(cohort_df)), 4)
        },
        "temperature_statistics_celsius": {
            "probe_min": round(float(np.min(valid_probes)), 3),
            "probe_mean": round(float(np.mean(valid_probes)), 3),
            "probe_median": round(float(np.median(valid_probes)), 3),
            "probe_max": round(float(np.max(valid_probes)), 3),
            "ambient_min": round(float(full_df["ambient_temp"].min()), 3),
            "ambient_mean": round(float(full_df["ambient_temp"].mean()), 3),
            "ambient_max": round(float(full_df["ambient_temp"].max()), 3)
        }
    }
    
    meta_path = os.path.join(DATA_DIR, "dataset_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[+] Saved metadata to: {meta_path}")
    print("=" * 80)
    return full_df

if __name__ == "__main__":
    generate_stratified_synthetic_fleet()

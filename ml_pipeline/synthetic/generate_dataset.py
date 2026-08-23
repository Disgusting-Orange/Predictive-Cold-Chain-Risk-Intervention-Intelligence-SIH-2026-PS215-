"""
FrostLink Physics-Informed Synthetic Telemetry Engine -- Fleet Generation Script (Phase 16A)
===========================================================================================
Generates 100 reproducible synthetic shipments across 13 operational scenarios.
Splits strictly by shipment_id into Train (70%), Validation (15%), and Test (15%).
Exports synthetic_train.csv, synthetic_validation.csv, synthetic_test.csv, and dataset_metadata.json.
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from thermal_model import PhysicsThermalModel, PhysicsParameters
from scenario_generator import ALL_SCENARIOS
from telemetry_generator import SyntheticTelemetryGenerator
from label_generator import SyntheticLabelGenerator

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)

def generate_full_synthetic_fleet(
    total_shipments: int = 100,
    random_seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15
):
    print("=" * 80)
    print("FROSTLINK PHASE 16A: GENERATING PHYSICS-INFORMED SYNTHETIC TELEMETRY FLEET")
    print(f"Total Shipments: {total_shipments} | Seed: {random_seed} | Scenarios: {len(ALL_SCENARIOS)}")
    print("=" * 80)
    
    rng = np.random.RandomState(random_seed)
    physics_model = PhysicsThermalModel()
    telemetry_gen = SyntheticTelemetryGenerator(physics_model=physics_model, random_seed=random_seed)
    label_gen = SyntheticLabelGenerator()
    
    shipment_dfs = []
    scenario_counts = {sc: 0 for sc in ALL_SCENARIOS}
    
    for i in range(1, total_shipments + 1):
        shipment_id = f"SYN_SHIP_{i:03d}"
        
        # Round-robin scenario assignment with random jitter to cover all 13 scenarios
        scenario_idx = (i - 1) % len(ALL_SCENARIOS)
        scenario_name = ALL_SCENARIOS[scenario_idx]
        scenario_counts[scenario_name] += 1
        
        # Generate 48-hour raw telemetry trajectory
        raw_df = telemetry_gen.generate_shipment_trajectory(
            shipment_id=shipment_id,
            scenario_name=scenario_name,
            start_time="2026-06-01T08:00:00Z",
            total_steps=288, # 48 hours
            dt_minutes=10.0
        )
        
        # Annotate non-leaking forward labels
        labeled_df = label_gen.annotate_shipment_labels(raw_df)
        shipment_dfs.append(labeled_df)
        
    full_dataset = pd.concat(shipment_dfs, ignore_index=True)
    total_observations = len(full_dataset)
    print(f"[+] Successfully generated {total_shipments} shipments ({total_observations:,} total observations).")
    
    # -------------------------------------------------------------
    # Shipment-Level Strict Partitioning (Zero Overlap)
    # -------------------------------------------------------------
    unique_shipments = [f"SYN_SHIP_{i:03d}" for i in range(1, total_shipments + 1)]
    rng.shuffle(unique_shipments)
    
    n_train = int(total_shipments * train_ratio)
    n_val = int(total_shipments * val_ratio)
    
    train_ids = sorted(unique_shipments[:n_train])
    val_ids = sorted(unique_shipments[n_train : n_train + n_val])
    test_ids = sorted(unique_shipments[n_train + n_val :])
    
    train_df = full_dataset[full_dataset["shipment_id"].isin(train_ids)].reset_index(drop=True)
    val_df = full_dataset[full_dataset["shipment_id"].isin(val_ids)].reset_index(drop=True)
    test_df = full_dataset[full_dataset["shipment_id"].isin(test_ids)].reset_index(drop=True)
    
    print(f"[+] Train Set:      {len(train_ids)} shipments | {len(train_df):,} rows")
    print(f"[+] Validation Set: {len(val_ids)} shipments | {len(val_df):,} rows")
    print(f"[+] Test Set:       {len(test_ids)} shipments | {len(test_df):,} rows")
    
    # Export CSVs
    train_csv_path = os.path.join(DATA_DIR, "synthetic_train.csv")
    val_csv_path = os.path.join(DATA_DIR, "synthetic_validation.csv")
    test_csv_path = os.path.join(DATA_DIR, "synthetic_test.csv")
    
    train_df.to_csv(train_csv_path, index=False)
    val_df.to_csv(val_csv_path, index=False)
    test_df.to_csv(test_csv_path, index=False)
    print(f"[+] Saved CSV files to: {DATA_DIR}")
    
    # -------------------------------------------------------------
    # Calculate Dataset Metadata & Summary Statistics
    # -------------------------------------------------------------
    probe_cols = ["Front_Top", "Front_Middle", "Front_Bottom", "Middle_Top", "Middle_Middle", "Middle_Bottom", "Rear_Top", "Rear_Middle", "Rear_Bottom"]
    all_probe_vals = full_dataset[probe_cols].values.flatten()
    valid_probe_vals = all_probe_vals[~np.isnan(all_probe_vals)]
    
    cohort_mask = full_dataset["risk_level"].isin([0.0, 1.0]) & full_dataset["y_next_60_R2"].notna()
    cohort_df = full_dataset[cohort_mask]
    pos_cases = int((cohort_df["y_next_60_R2"] == 1.0).sum())
    neg_cases = int((cohort_df["y_next_60_R2"] == 0.0).sum())
    
    metadata = {
        "dataset_name": "FrostLink_Physics_Informed_Synthetic_Fleet_v2",
        "generated_at": "2026-08-23T04:15:00Z",
        "random_seed": random_seed,
        "sampling_interval_minutes": 10.0,
        "shipment_duration_hours": 48.0,
        "total_shipments": total_shipments,
        "total_observations": total_observations,
        "split_counts": {
            "train_shipments": len(train_ids),
            "train_rows": len(train_df),
            "validation_shipments": len(val_ids),
            "validation_rows": len(val_df),
            "test_shipments": len(test_ids),
            "test_rows": len(test_df)
        },
        "scenario_distribution": scenario_counts,
        "early_warning_cohort": {
            "total_cohort_rows": len(cohort_df),
            "positive_excursion_transitions": pos_cases,
            "negative_safe_rows": neg_cases,
            "base_excursion_rate": round(float(pos_cases) / max(1, len(cohort_df)), 4)
        },
        "temperature_statistics_celsius": {
            "probe_min": round(float(np.min(valid_probe_vals)), 3),
            "probe_mean": round(float(np.mean(valid_probe_vals)), 3),
            "probe_median": round(float(np.median(valid_probe_vals)), 3),
            "probe_max": round(float(np.max(valid_probe_vals)), 3),
            "ambient_min": round(float(full_dataset["ambient_temp"].min()), 3),
            "ambient_mean": round(float(full_dataset["ambient_temp"].mean()), 3),
            "ambient_max": round(float(full_dataset["ambient_temp"].max()), 3)
        },
        "sensor_quality_statistics": {
            "total_probe_readings": int(len(all_probe_vals)),
            "missing_probe_readings": int(np.isnan(all_probe_vals).sum()),
            "probe_dropout_rate": round(float(np.isnan(all_probe_vals).sum()) / len(all_probe_vals), 4),
            "mean_packet_sconf": round(float(full_dataset["sconf"].mean()), 4)
        },
        "cooling_state_distribution": {
            str(k): int(v) for k, v in full_dataset["cooling_state"].value_counts().to_dict().items()
        },
        "door_event_steps_count": int(full_dataset["door_open"].sum())
    }
    
    meta_path = os.path.join(DATA_DIR, "dataset_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[+] Saved dataset metadata to: {meta_path}")
    print("=" * 80)

if __name__ == "__main__":
    generate_full_synthetic_fleet()

"""
FrostLink Physics-Informed Synthetic Telemetry Engine -- Dataset Validator (Phase 16A)
=====================================================================================
Performs strict scientific validation on generated synthetic datasets:
1. File integrity & row count matches.
2. Shipment disjointness (zero data leakage across splits).
3. Temporal monotonicity within every shipment.
4. Physical temperature range plausibility.
5. Forward-looking target non-leakage verification.
6. Scenario diversity and distribution across splits.
7. Class balance in early-warning cohort.
8. Sensor dropout & confidence metadata verification.
"""

import sys
import os
import json
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
PROBE_COLS = ["Front_Top", "Front_Middle", "Front_Bottom", "Middle_Top", "Middle_Middle", "Middle_Bottom", "Rear_Top", "Rear_Middle", "Rear_Bottom"]

def validate_synthetic_dataset():
    print("=" * 80)
    print("FROSTLINK PHASE 16A: SYNTHETIC DATASET VALIDATION AUDIT")
    print("=" * 80)
    
    test_results = {}
    
    # 1. File Existence & Loading
    train_path = os.path.join(DATA_DIR, "synthetic_train.csv")
    val_path = os.path.join(DATA_DIR, "synthetic_validation.csv")
    test_path = os.path.join(DATA_DIR, "synthetic_test.csv")
    meta_path = os.path.join(DATA_DIR, "dataset_metadata.json")
    
    files_exist = all(os.path.exists(p) for p in [train_path, val_path, test_path, meta_path])
    if not files_exist:
        print("[!] ERROR: Dataset files missing. Run generate_dataset.py first.")
        return False
        
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)
    with open(meta_path) as f:
        meta = json.load(f)
        
    full_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
    expected_rows = meta.get("total_observations", len(full_df))
    expected_ships = meta.get("total_shipments", len(full_df["shipment_id"].unique()))
    t1_pass = bool(len(full_df) == expected_rows and len(full_df["shipment_id"].unique()) == expected_ships)
    test_results["1_file_integrity_and_row_counts"] = {"passed": t1_pass, "total_rows": len(full_df), "shipments": len(full_df["shipment_id"].unique())}
    print(f"Check 1 [Integrity & Row Counts]:      Passed = {t1_pass} (Rows: {len(full_df):,}, Shipments: {len(full_df['shipment_id'].unique())})")
    
    # 2. Strict Shipment-Level Disjointness (Zero Leakage)
    train_ships = set(train_df["shipment_id"].unique())
    val_ships = set(val_df["shipment_id"].unique())
    test_ships = set(test_df["shipment_id"].unique())
    
    overlap_train_val = train_ships & val_ships
    overlap_train_test = train_ships & test_ships
    overlap_val_test = val_ships & test_ships
    
    t2_pass = bool(len(overlap_train_val) == 0 and len(overlap_train_test) == 0 and len(overlap_val_test) == 0)
    test_results["2_shipment_disjointness"] = {"passed": t2_pass, "train_count": len(train_ships), "val_count": len(val_ships), "test_count": len(test_ships)}
    print(f"Check 2 [Shipment Zero Leakage]:       Passed = {t2_pass} (Train: {len(train_ships)}, Val: {len(val_ships)}, Test: {len(test_ships)})")
    
    # 3. Temporal Monotonicity & No Duplicates
    temporal_pass = True
    for s_id, s_df in full_df.groupby("shipment_id"):
        s_times = pd.to_datetime(s_df["Time"])
        if not s_times.is_monotonic_increasing or len(s_times) != len(s_times.unique()):
            temporal_pass = False
            break
    test_results["3_temporal_monotonicity"] = {"passed": temporal_pass}
    print(f"Check 3 [Temporal Monotonicity]:       Passed = {temporal_pass}")
    
    # 4. Temperature Physical Plausibility Range Checks
    all_probe_vals = full_df[PROBE_COLS].values.flatten()
    valid_probes = all_probe_vals[~np.isnan(all_probe_vals)]
    p_min = float(np.min(valid_probes))
    p_max = float(np.max(valid_probes))
    amb_min = float(full_df["ambient_temp"].min())
    amb_max = float(full_df["ambient_temp"].max())
    
    # Plausibility bounds: Probes in [-1.0°C, 35.0°C], Ambient in [15.0°C, 55.0°C]
    plausible = (-1.0 <= p_min) and (p_max <= 35.0) and (15.0 <= amb_min) and (amb_max <= 55.0)
    test_results["4_temperature_plausibility"] = {
        "passed": plausible,
        "probe_min": p_min,
        "probe_max": p_max,
        "ambient_min": amb_min,
        "ambient_max": amb_max
    }
    print(f"Check 4 [Physical Temperature Range]: Passed = {plausible} (Probes: [{p_min:.2f}, {p_max:.2f}]°C, Ambient: [{amb_min:.2f}, {amb_max:.2f}]°C)")
    
    # 5. Non-Leaking Target Verification
    # Verify that y_next_60_R2 at time t matches max(T(t+1..t+6)) > 4.0
    label_leak_pass = True
    for s_id, s_df in full_df.groupby("shipment_id"):
        s_df = s_df.sort_values("step_index").reset_index(drop=True)
        probe_means = s_df[PROBE_COLS].mean(axis=1).values
        y_vals = s_df["y_next_60_R2"].values
        for i in range(len(s_df) - 6):
            expected_y = 1.0 if np.max(probe_means[i + 1 : i + 7]) > 4.0 else 0.0
            if y_vals[i] != expected_y:
                label_leak_pass = False
                break
    test_results["5_target_causality_verification"] = {"passed": label_leak_pass}
    print(f"Check 5 [Target Non-Leakage Verified]: Passed = {label_leak_pass}")
    
    # 6. Scenario Diversity & Coverage
    scenario_counts = full_df["scenario_name"].value_counts().to_dict()
    all_13_present = bool(len(scenario_counts) == 13 and all(v > 0 for v in scenario_counts.values()))
    test_results["6_scenario_coverage"] = {"passed": all_13_present, "scenarios_count": len(scenario_counts)}
    print(f"Check 6 [13 Scenarios All Represented]:Passed = {all_13_present} (Count: {len(scenario_counts)} / 13)")
    
    # 7. Class Distribution in Early-Warning Cohort
    cohort_df = full_df[full_df["risk_level"].isin([0.0, 1.0]) & full_df["y_next_60_R2"].notna()]
    n_pos = int((cohort_df["y_next_60_R2"] == 1.0).sum())
    n_neg = int((cohort_df["y_next_60_R2"] == 0.0).sum())
    pos_rate = n_pos / len(cohort_df)
    
    class_valid = bool(n_pos > 0 and n_neg > 0 and 0.005 <= pos_rate <= 0.40)
    test_results["7_class_distribution"] = {"passed": class_valid, "cohort_size": len(cohort_df), "positive_excursions": n_pos, "safe_cases": n_neg, "pos_rate": pos_rate}
    print(f"Check 7 [Cohort Class Balance]:        Passed = {class_valid} (Pos: {n_pos:,} ({pos_rate*100:.1f}%), Neg: {n_neg:,})")
    
    # 8. Sensor Dropout Statistics
    missing_count = int(np.isnan(all_probe_vals).sum())
    dropout_rate = missing_count / len(all_probe_vals)
    mean_sconf = float(full_df["sconf"].mean())
    dropout_pass = bool(missing_count > 0 and 0.005 <= dropout_rate <= 0.05 and 0.90 <= mean_sconf <= 1.0)
    test_results["8_sensor_dropout_validation"] = {"passed": dropout_pass, "missing_probe_readings": missing_count, "dropout_rate": dropout_rate, "mean_sconf": mean_sconf}
    print(f"Check 8 [Sensor Dropouts & Confidence]:Passed = {dropout_pass} (Dropout Rate: {dropout_rate*100:.2f}%, Mean Sconf: {mean_sconf:.3f})")
    
    # Export Validation Report
    all_passed = all(v["passed"] for v in test_results.values())
    report_dict = {
        "validation_report_version": "1.0.0",
        "all_checks_passed": all_passed,
        "checks_passed_count": sum(v["passed"] for v in test_results.values()),
        "total_checks": len(test_results),
        "results": test_results
    }
    
    val_report_path = os.path.join(os.path.dirname(__file__), "validation_report.json")
    def json_serial(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)): return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)): return float(obj)
        elif isinstance(obj, (np.bool_, bool)): return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
        
    with open(val_report_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
        
    print("=" * 80)
    print(f"DATASET VALIDATION COMPLETE: {report_dict['checks_passed_count']} / {report_dict['total_checks']} CHECKS PASSED (All Passed = {all_passed})")
    print(f"Saved Validation Report to: {val_report_path}")
    print("=" * 80)
    return all_passed

if __name__ == "__main__":
    validate_synthetic_dataset()

"""
FrostLink Feature Engineering Test Suite -- Phase 14
====================================================
Verifies all 11 critical feature engineering assertions:
1. Raw packet schema validation.
2. Exact 40-feature output count.
3. Feature names and sequence match feature_schema.json 100%.
4. Strict causal isolation: Modifying future packets (t+1, t+5) does NOT alter features at time t.
5. Causal backward rolling windows: Rolling extractions strictly cover [t-50m, t].
6. Cold-start handling: Correctly processes early sequences (< 6 packets) without crashing.
7. Real-world Strawberry consistency: Compares feature engineer output against strawberry_train.csv.
8. Spatial probe gradient metrics: Correctly calculates range, std, hot_ratio, cold_ratio.
9. Faulty sensor / null probe resilience: Gracefully computes available probes.
10. End-to-end integration: Raw Telemetry -> Feature Engineer -> FastAPI /api/v1/predict_risk -> Output.
11. Feature vector validation helper checks.
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Add paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "feature_engineering")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service")))

from raw_schema import RawTelemetryPacket, RawTelemetryHistory
from feature_engineer import FrostLinkFeatureEngineer
from validation import validate_raw_packet, validate_feature_vector
from main import app

client = TestClient(app)

def run_feature_engineering_tests():
    print("=" * 80)
    print("RUNNING FROSTLINK FEATURE ENGINEERING TEST SUITE (11 Tests)")
    print("=" * 80)
    
    test_results = {}
    engineer = FrostLinkFeatureEngineer()
    
    # -------------------------------------------------------------
    # TEST 1: Raw Packet Validation
    # -------------------------------------------------------------
    sample_packet = {
        "shipment_id": "TEST_SHIP_01",
        "timestamp": "2026-08-23T14:00:00Z",
        "probes": {"Front_Top": 2.5, "Front_Middle": 2.3, "Rear_Bottom": 2.8},
        "sconf": 1.0,
        "coverage_time": 1.0
    }
    t1_pass = validate_raw_packet(sample_packet)
    test_results["1_raw_packet_validation"] = {"passed": t1_pass}
    print(f"Test 1 [Raw Packet Validation]:        Passed = {t1_pass}")
    
    # -------------------------------------------------------------
    # Construct a 10-step raw telemetry stream (10-min cadence)
    # -------------------------------------------------------------
    base_time = datetime(2026, 8, 23, 10, 0, 0)
    stream_packets = []
    for i in range(10):
        t_step = base_time + timedelta(minutes=10 * i)
        # Gradually warming temperature
        p_base = 2.0 + 0.1 * i
        pkt = RawTelemetryPacket(
            shipment_id="TEST_SHIP_01",
            timestamp=t_step.isoformat() + "Z",
            probes={
                "Front_Top": p_base + 0.2,
                "Front_Middle": p_base,
                "Front_Bottom": p_base - 0.2,
                "Middle_Top": p_base + 0.4,
                "Middle_Middle": p_base + 0.1,
                "Middle_Bottom": p_base - 0.1,
                "Rear_Top": p_base + 0.6,
                "Rear_Middle": p_base + 0.3,
                "Rear_Bottom": p_base
            },
            sconf=1.0,
            coverage_time=1.0
        )
        stream_packets.append(pkt)
        
    # -------------------------------------------------------------
    # TEST 2 & 3: Feature Count & Schema Sequence Match
    # -------------------------------------------------------------
    feat_dict, meta = engineer.extract_features(stream_packets)
    t2_pass = (len(feat_dict) == 40)
    t3_pass = (list(feat_dict.keys()) == engineer.feature_names)
    test_results["2_feature_count_40"] = {"passed": t2_pass, "count": len(feat_dict)}
    test_results["3_feature_order_match"] = {"passed": t3_pass}
    print(f"Test 2 [Feature Count = 40]:           Passed = {t2_pass}")
    print(f"Test 3 [Schema Sequence 100% Match]:   Passed = {t3_pass}")
    
    # -------------------------------------------------------------
    # TEST 4: Strict Causal Isolation (No Future Lookahead)
    # -------------------------------------------------------------
    # Extract features at step 5 (Time = 10:50) from unperturbed stream
    t_target = (base_time + timedelta(minutes=50)).isoformat() + "Z"
    feat_orig, _ = engineer.extract_features(stream_packets, target_timestamp=t_target)
    
    # Create perturbed stream where future steps (steps 6-9) are drastically modified
    perturbed_packets = [p.model_copy(deep=True) for p in stream_packets]
    for i in range(6, 10):
        perturbed_packets[i].probes = {k: v + 50.0 for k, v in perturbed_packets[i].probes.items()}
        
    feat_pert, _ = engineer.extract_features(perturbed_packets, target_timestamp=t_target)
    
    # Check max difference across all 40 features at time t
    max_lookahead_diff = max(abs(feat_orig[k] - feat_pert[k]) for k in engineer.feature_names if feat_orig[k] is not None)
    t4_pass = bool(max_lookahead_diff == 0.0)
    test_results["4_causal_no_lookahead"] = {"passed": t4_pass, "max_diff": max_lookahead_diff}
    print(f"Test 4 [Strict Causal No-Lookahead]:   Passed = {t4_pass} (Max Future Delta: {max_lookahead_diff:.2e})")
    
    # -------------------------------------------------------------
    # TEST 5: Causal Backward Rolling Windows [t-50m, t]
    # -------------------------------------------------------------
    # Step 5 is the 6th observation (indices 0..5). W60_T_mean should match mean of means of steps 0..5
    step_means = [np.mean(list(p.probes.values())) for p in stream_packets[:6]]
    expected_w60_mean = float(np.mean(step_means))
    actual_w60_mean = feat_orig["W60_T_mean"]
    diff_w60 = abs(expected_w60_mean - actual_w60_mean)
    t5_pass = bool(diff_w60 < 1e-6)
    test_results["5_backward_rolling_window"] = {"passed": t5_pass, "diff": diff_w60}
    print(f"Test 5 [Causal 60m Backward Window]:   Passed = {t5_pass} (Delta: {diff_w60:.2e})")
    
    # -------------------------------------------------------------
    # TEST 6: Cold-Start Handling (< 6 Packets)
    # -------------------------------------------------------------
    short_stream = stream_packets[:2]  # Only 2 packets (10 min history)
    feat_cold, meta_cold = engineer.extract_features(short_stream)
    t6_pass = bool(len(feat_cold) == 40 and meta_cold["cold_start_status"] == "COLD_START" and not np.isnan(feat_cold["T_mean_t"]))
    test_results["6_cold_start_handling"] = {"passed": t6_pass, "cold_status": meta_cold.get("cold_start_status")}
    print(f"Test 6 [Cold-Start (<6 pkts) Robust]:  Passed = {t6_pass} (Status: {meta_cold.get('cold_start_status')})")
    
    # -------------------------------------------------------------
    # TEST 7: Real Strawberry Dataset Consistency Check
    # -------------------------------------------------------------
    real_train_path = r"ml_pipeline\data\strawberry_train.csv"
    real_df = pd.read_csv(real_train_path)
    real_df["Time_dt"] = pd.to_datetime(real_df["Time"])
    dedup_df = real_df.drop_duplicates(subset=["shipment_id", "Time_dt"]).sort_values(["shipment_id", "Time_dt"]).reset_index(drop=True)
    s1_slice = dedup_df[dedup_df["shipment_id"] == "S1"].head(15).reset_index(drop=True)
    
    # Run feature engineer on S1 raw probe sequence at 6th step (index 5)
    target_t = s1_slice.loc[5, "Time"]
    feat_s1, _ = engineer.extract_features(s1_slice, target_timestamp=target_t)
    
    # Compare T_mean_t, spatial_range_t, spatial_std_t against existing S1 row 5
    row5_target = s1_slice.iloc[5]
    delta_t_mean = abs(feat_s1["T_mean_t"] - row5_target["T_mean_t"])
    delta_s_range = abs(feat_s1["spatial_range_t"] - row5_target["spatial_range_t"])
    delta_s_std = abs(feat_s1["spatial_std_t"] - row5_target["spatial_std_t"])
    delta_w60_mean = abs(feat_s1["W60_T_mean"] - row5_target["W60_T_mean"])
    
    max_d = max(delta_t_mean, delta_s_range, delta_s_std, delta_w60_mean)
    t7_pass = bool(max_d < 1e-5)
    test_results["7_real_data_consistency"] = {
        "passed": t7_pass,
        "delta_T_mean": delta_t_mean,
        "delta_spatial_range": delta_s_range,
        "delta_spatial_std": delta_s_std,
        "delta_W60_mean": delta_w60_mean
    }
    print(f"Test 7 [Real Dataset Consistency]:     Passed = {t7_pass} (Max Delta: {max_d:.2e})")
    
    # -------------------------------------------------------------
    # TEST 8: Spatial Probe Gradient Metrics
    # -------------------------------------------------------------
    probes_test = {"p1": 2.0, "p2": 3.0, "p3": 5.0, "p4": -1.0}
    test_pkt = RawTelemetryPacket(shipment_id="TEST_SPATIAL", timestamp="2026-08-23T12:00:00Z", probes=probes_test)
    feat_spat, _ = engineer.extract_features([test_pkt])
    
    # p_max=5.0, p_min=-1.0 -> range=6.0, hot (>4.0) = 1/4 = 0.25, cold (<0.0) = 1/4 = 0.25
    t8_pass = bool(
        abs(feat_spat["spatial_range_t"] - 6.0) < 1e-6 and
        abs(feat_spat["hot_ratio_t"] - 0.25) < 1e-6 and
        abs(feat_spat["cold_ratio_t"] - 0.25) < 1e-6
    )
    test_results["8_spatial_gradient_metrics"] = {"passed": t8_pass}
    print(f"Test 8 [Spatial Gradient Logic]:       Passed = {t8_pass}")
    
    # -------------------------------------------------------------
    # TEST 9: Faulty Sensor / Missing Probe Resilience
    # -------------------------------------------------------------
    faulty_pkt = RawTelemetryPacket(
        shipment_id="TEST_FAULT",
        timestamp="2026-08-23T12:10:00Z",
        probes={"p1": 2.5, "p2": None, "p3": None, "p4": 3.5}
    )
    feat_fault, meta_fault = engineer.extract_features([faulty_pkt])
    # Active probes count should be 2, mean should be (2.5+3.5)/2 = 3.0
    t9_pass = bool(abs(feat_fault["T_mean_t"] - 3.0) < 1e-6 and feat_fault["N_valid"] == 2.0)
    test_results["9_missing_probe_resilience"] = {"passed": t9_pass, "active_count": feat_fault["N_valid"]}
    print(f"Test 9 [Faulty Probe Resilience]:      Passed = {t9_pass} (Active Probes: {int(feat_fault['N_valid'])})")
    
    # -------------------------------------------------------------
    # TEST 10: End-to-End Integration: Raw -> Engineer -> FastAPI Service
    # -------------------------------------------------------------
    # Build a full payload from raw stream extractions and query FastAPI service
    api_payload = {
        "shipment_id": "TEST_SHIP_01",
        "timestamp": stream_packets[-1].timestamp,
        "features": feat_dict
    }
    
    response = client.post("/api/v1/predict_risk", json=api_payload)
    resp_data = response.json()
    
    t10_pass = bool(
        response.status_code == 200 and
        "risk_probability" in resp_data and
        "explanation" in resp_data and
        0.0 <= resp_data["risk_probability"] <= 1.0
    )
    test_results["10_end_to_end_integration"] = {
        "passed": t10_pass,
        "status_code": response.status_code,
        "risk_prob": resp_data.get("risk_probability"),
        "risk_level": resp_data.get("risk_level")
    }
    print(f"Test 10 [End-to-End API Integration]: Passed = {t10_pass} (HTTP 200, Risk: {resp_data.get('risk_level')})")
    
    # -------------------------------------------------------------
    # TEST 11: Feature Vector Validation Helper
    # -------------------------------------------------------------
    is_valid, val_msg = validate_feature_vector(feat_dict, engineer.feature_names)
    t11_pass = bool(is_valid and val_msg == "Valid")
    test_results["11_validation_helper"] = {"passed": t11_pass}
    print(f"Test 11 [Feature Vector Validator]:    Passed = {t11_pass}")
    
    # Save Report
    all_passed = all(v["passed"] for v in test_results.values())
    report_dict = {
        "test_suite_version": "1.0.0",
        "all_tests_passed": all_passed,
        "tests_passed_count": sum(v["passed"] for v in test_results.values()),
        "total_tests": len(test_results),
        "results": test_results
    }
    
    report_path = os.path.join(os.path.dirname(__file__), "feature_engineering_test_report.json")
    def json_serial(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)): return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)): return float(obj)
        elif isinstance(obj, (np.bool_, bool)): return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
        
    with open(report_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
        
    print("=" * 80)
    print(f"FEATURE ENGINEERING TEST SUITE COMPLETE: {report_dict['tests_passed_count']} / {report_dict['total_tests']} TESTS PASSED (All Passed = {all_passed})")
    print(f"Saved Report to: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_feature_engineering_tests()

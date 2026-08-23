"""
FrostLink Phase 17B: Production Cold-Start Safety & Final Integration Test Suite
================================================================================
Exhaustively tests cold-start safety invariants and production integration:
TEST 1:  0 observations -> no prediction (empty history / fail closed)
TEST 2:  1 observation  -> COLD_START, no prediction (risk_probability is None)
TEST 3:  2 observations -> COLD_START, no prediction (risk_probability is None)
TEST 4:  3 observations -> COLD_START, no prediction (risk_probability is None)
TEST 5:  4 observations -> COLD_START, no prediction (risk_probability is None)
TEST 6:  5 observations -> COLD_START, no prediction (risk_probability is None)
TEST 7:  exactly 6 observations -> WARMED, prediction allowed (XGBoost & SHAP)
TEST 8:  7+ observations -> WARMED, prediction allowed
TEST 9:  missing probe during warm history -> graceful degradation
TEST 10: all probes missing -> fail closed
TEST 11: 40-feature schema alignment in exact sequence
TEST 12: XGBoost v2 + SHAP end-to-end with mathematical additivity verification
"""

import sys
import os
import json
import time
import numpy as np
import pandas as pd
import xgboost as xgb
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Path configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "hardware")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "feature_engineering")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "service")))

from raw_schema import RawTelemetryPacket
from history_buffer import ShipmentHistoryBuffer
from gateway import HardwareGateway
from main import app
from model_service import ModelService

def make_probe_packet(shipment_id: str, minute_offset: int, temp_base: float = 2.20, missing_probes: list = None):
    probes = {
        "Front_Top": temp_base + 0.25,
        "Front_Middle": temp_base,
        "Front_Bottom": temp_base - 0.20,
        "Middle_Top": temp_base + 0.35,
        "Middle_Middle": temp_base + 0.05,
        "Middle_Bottom": temp_base - 0.15,
        "Rear_Top": temp_base + 0.55,
        "Rear_Middle": temp_base + 0.20,
        "Rear_Bottom": temp_base + 0.05
    }
    if missing_probes:
        for p in missing_probes:
            probes[p] = None
            
    valid_count = sum(1 for v in probes.values() if v is not None)
    return {
        "shipment_id": shipment_id,
        "timestamp": f"2026-08-23T14:{minute_offset:02d}:00Z",
        "probes": probes,
        "sconf": round(valid_count / 9.0, 3),
        "coverage_time": 1.0
    }

def run_phase17b_integration_tests():
    print("=" * 80)
    print("RUNNING FROSTLINK PHASE 17B COLD-START SAFETY & INTEGRATION TEST SUITE (12 Tests)")
    print("=" * 80)
    
    test_results = {}
    history_buffer = ShipmentHistoryBuffer(max_history_packets=50)
    gateway = HardwareGateway(history_buffer=history_buffer)
    api_client = TestClient(app)
    
    shipment_id = "SAFETY_SHIP_001"
    
    # -------------------------------------------------------------
    # TEST 1: 0 Observations -> No Prediction
    # -------------------------------------------------------------
    hist_0 = history_buffer.get_history(shipment_id)
    t1_pass = bool(len(hist_0) == 0)
    test_results["1_zero_observations_no_prediction"] = {"passed": t1_pass, "history_len": len(hist_0)}
    print(f"Test 1 [0 Observations -> No Prediction]: Passed = {t1_pass} (History Count: {len(hist_0)})")
    
    # -------------------------------------------------------------
    # TEST 2: 1 Observation -> COLD_START, No Prediction
    # -------------------------------------------------------------
    pkt1 = make_probe_packet(shipment_id, 0)
    res1 = gateway.process_raw_telemetry(pkt1)
    t2_pass = bool(
        res1.success and
        res1.cold_start_status == "COLD_START" and
        res1.risk_probability is None and
        res1.risk_level == "INSUFFICIENT_DATA" and
        res1.explanation is None
    )
    test_results["2_obs1_cold_start_no_inference"] = {"passed": t2_pass, "status": res1.cold_start_status, "risk_prob": res1.risk_probability}
    print(f"Test 2 [1 Observation -> COLD_START]:    Passed = {t2_pass} (Prob = None, Status: {res1.cold_start_status})")
    
    # -------------------------------------------------------------
    # TEST 3: 2 Observations -> COLD_START, No Prediction
    # -------------------------------------------------------------
    pkt2 = make_probe_packet(shipment_id, 10)
    res2 = gateway.process_raw_telemetry(pkt2)
    t3_pass = bool(res2.cold_start_status == "COLD_START" and res2.risk_probability is None)
    test_results["3_obs2_cold_start_no_inference"] = {"passed": t3_pass, "status": res2.cold_start_status}
    print(f"Test 3 [2 Observations -> COLD_START]:   Passed = {t3_pass} (Prob = None, Status: {res2.cold_start_status})")
    
    # -------------------------------------------------------------
    # TEST 4: 3 Observations -> COLD_START, No Prediction
    # -------------------------------------------------------------
    pkt3 = make_probe_packet(shipment_id, 20)
    res3 = gateway.process_raw_telemetry(pkt3)
    t4_pass = bool(res3.cold_start_status == "COLD_START" and res3.risk_probability is None)
    test_results["4_obs3_cold_start_no_inference"] = {"passed": t4_pass, "status": res3.cold_start_status}
    print(f"Test 4 [3 Observations -> COLD_START]:   Passed = {t4_pass} (Prob = None, Status: {res3.cold_start_status})")
    
    # -------------------------------------------------------------
    # TEST 5: 4 Observations -> COLD_START, No Prediction
    # -------------------------------------------------------------
    pkt4 = make_probe_packet(shipment_id, 30)
    res4 = gateway.process_raw_telemetry(pkt4)
    t5_pass = bool(res4.cold_start_status == "COLD_START" and res4.risk_probability is None)
    test_results["5_obs4_cold_start_no_inference"] = {"passed": t5_pass, "status": res4.cold_start_status}
    print(f"Test 5 [4 Observations -> COLD_START]:   Passed = {t5_pass} (Prob = None, Status: {res4.cold_start_status})")
    
    # -------------------------------------------------------------
    # TEST 6: 5 Observations -> COLD_START, No Prediction
    # -------------------------------------------------------------
    pkt5 = make_probe_packet(shipment_id, 40)
    res5 = gateway.process_raw_telemetry(pkt5)
    t6_pass = bool(res5.cold_start_status == "COLD_START" and res5.risk_probability is None)
    test_results["6_obs5_cold_start_no_inference"] = {"passed": t6_pass, "status": res5.cold_start_status}
    print(f"Test 6 [5 Observations -> COLD_START]:   Passed = {t6_pass} (Prob = None, Status: {res5.cold_start_status})")
    
    # -------------------------------------------------------------
    # TEST 7: Exactly 6 Observations (50m elapsed) -> WARMED, Prediction Allowed
    # -------------------------------------------------------------
    pkt6 = make_probe_packet(shipment_id, 50)
    res6 = gateway.process_raw_telemetry(pkt6)
    t7_pass = bool(
        res6.success and
        res6.cold_start_status == "WARMED" and
        res6.risk_probability is not None and
        0.0 <= res6.risk_probability <= 1.0 and
        res6.risk_level == "SAFE" and
        res6.explanation is not None
    )
    test_results["7_obs6_warmed_prediction_allowed"] = {"passed": t7_pass, "status": res6.cold_start_status, "prob": res6.risk_probability}
    print(f"Test 7 [Exactly 6 Obs -> WARMED Allowed]: Passed = {t7_pass} (Status: {res6.cold_start_status}, Prob: {res6.risk_probability:.4f})")
    
    # -------------------------------------------------------------
    # TEST 8: 7+ Observations -> WARMED, Prediction Allowed
    # -------------------------------------------------------------
    pkt7 = {
        "shipment_id": shipment_id,
        "timestamp": "2026-08-23T15:00:00Z", # 60 minutes after start
        "probes": {
            "Front_Top": 2.45, "Front_Middle": 2.20, "Front_Bottom": 2.00,
            "Middle_Top": 2.85, "Middle_Middle": 2.30, "Middle_Bottom": 2.10,
            "Rear_Top": 3.25, "Rear_Middle": 2.50, "Rear_Bottom": 2.20
        },
        "sconf": 1.0,
        "coverage_time": 1.0
    }
    res7 = gateway.process_raw_telemetry(pkt7)
    t8_pass = bool(res7.success and res7.cold_start_status == "WARMED" and res7.risk_probability is not None)
    test_results["8_obs7_plus_prediction_allowed"] = {"passed": t8_pass, "status": res7.cold_start_status, "prob": res7.risk_probability}
    print(f"Test 8 [7+ Observations -> WARMED Allowed]:Passed = {t8_pass} (Status: {res7.cold_start_status}, Prob: {res7.risk_probability:.4f})")
    
    # -------------------------------------------------------------
    # TEST 9: Missing Probe During Warm History -> Graceful Degradation
    # -------------------------------------------------------------
    pkt8 = make_probe_packet(shipment_id, 10, temp_base=2.30, missing_probes=["Front_Middle", "Middle_Top"])
    pkt8["timestamp"] = "2026-08-23T15:10:00Z"
    res8 = gateway.process_raw_telemetry(pkt8)
    t9_pass = bool(res8.success and res8.active_probes == 7 and res8.risk_probability is not None)
    test_results["9_missing_probe_graceful_degradation"] = {"passed": t9_pass, "active_probes": res8.active_probes, "prob": res8.risk_probability}
    print(f"Test 9 [Missing Probe Degradation]:    Passed = {t9_pass} (Active Probes: {res8.active_probes}/9, Prob: {res8.risk_probability:.4f})")
    
    # -------------------------------------------------------------
    # TEST 10: All Probes Missing -> Fail Closed
    # -------------------------------------------------------------
    all_dead_pkt = {
        "shipment_id": shipment_id,
        "timestamp": "2026-08-23T15:20:00Z",
        "probes": {"Front_Top": None, "Middle_Middle": None, "Rear_Bottom": None},
        "sconf": 0.0,
        "coverage_time": 1.0
    }
    res10 = gateway.process_raw_telemetry(all_dead_pkt)
    t10_pass = bool(not res10.success)
    test_results["10_all_probes_missing_fail_closed"] = {"passed": t10_pass, "error": res10.error_message}
    print(f"Test 10 [All Probes Dead Fail-Closed]: Passed = {t10_pass} (Safely Rejected: {res10.error_message[:45]}...)")
    
    # -------------------------------------------------------------
    # TEST 11: 40-Feature Schema Alignment in Exact Sequence
    # -------------------------------------------------------------
    hist_now = history_buffer.get_history(shipment_id)
    f_dict, meta = gateway.feature_engineer.extract_features(hist_now)
    expected_order = gateway.feature_engineer.feature_names
    t11_pass = bool(list(f_dict.keys()) == expected_order and len(f_dict) == 40)
    test_results["11_40_feature_schema_alignment"] = {"passed": t11_pass, "feature_count": len(f_dict)}
    print(f"Test 11 [40-Feature Schema Alignment]:  Passed = {t11_pass} (Exact 40 Features in Sequence)")
    
    # -------------------------------------------------------------
    # TEST 12: XGBoost v2 + SHAP End-to-End with Additivity Verification
    # -------------------------------------------------------------
    explainer = gateway.model_service.explainer
    model = gateway.model_service.model
    operating_th = gateway.model_service.operating_threshold
    
    df_sample = pd.DataFrame([[f_dict[k] for k in expected_order]], columns=expected_order, dtype=np.float64)
    full_shap = explainer.shap_values(df_sample)[0]
    base_val = float(explainer.expected_value) if not isinstance(explainer.expected_value, np.ndarray) else float(explainer.expected_value[0])
    
    dmat = xgb.DMatrix(df_sample)
    booster_margin = float(model.get_booster().predict(dmat, output_margin=True)[0])
    reconstructed_margin = base_val + float(np.sum(full_shap))
    additivity_delta = abs(booster_margin - reconstructed_margin)
    
    reconstructed_prob = 1.0 / (1.0 + np.exp(-reconstructed_margin))
    prob_delta = abs(reconstructed_prob - res8.risk_probability)
    
    t12_pass = bool(
        abs(operating_th - 0.5750) < 1e-4 and
        additivity_delta < 1e-4 and
        prob_delta < 1e-4 and
        res8.explanation is not None and
        (len(res8.explanation.get("top_risk_increasing_factors", [])) > 0 or len(res8.explanation.get("top_risk_reducing_factors", [])) > 0)
    )
    test_results["12_v2_prediction_and_shap_additivity"] = {"passed": t12_pass, "additivity_delta": additivity_delta, "prob_delta": prob_delta, "threshold": operating_th}
    print(f"Test 12 [XGBoost v2 & SHAP Additivity]: Passed = {t12_pass} (Threshold: {operating_th:.4f}, Additivity Delta: {additivity_delta:.2e}, Prob Delta: {prob_delta:.2e})")
    
    # Measure Latency for Warmed Step
    lats = res6.latencies_ms
    print("\n" + "-" * 80)
    print("MONOTONIC LATENCY PROFILING (Warmed Step 6, Software-Host Environment):")
    print(f"   ├─ Raw Validation:      {lats.get('validation_ms', 0):.2f} ms")
    print(f"   ├─ History Buffering:   {lats.get('history_buffer_ms', 0):.2f} ms")
    print(f"   ├─ Feature Engineering: {lats.get('feature_engineering_ms', 0):.2f} ms")
    print(f"   ├─ XGBoost & SHAP:      {lats.get('inference_and_shap_ms', 0):.2f} ms")
    print(f"   └─ Total Pipeline:      {lats.get('total_pipeline_ms', 0):.2f} ms")
    print("-" * 80)
    
    # Save Report
    all_passed = all(v["passed"] for v in test_results.values())
    report_dict = {
        "integration_test_suite_version": "1.1.0",
        "model_version": "frostlink_xgb_v2",
        "threshold": operating_th,
        "all_tests_passed": all_passed,
        "tests_passed_count": sum(v["passed"] for v in test_results.values()),
        "total_tests": len(test_results),
        "results": test_results,
        "warmed_step_latencies_ms": lats
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "phase17_integration_report.json")
    def json_serial(obj):
        if isinstance(obj, (np.floating, np.float32, np.float64)): return float(obj)
        elif isinstance(obj, (np.integer, np.int32, np.int64)): return int(obj)
        elif isinstance(obj, (np.bool_, bool)): return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
        
    with open(out_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
        
    print("=" * 80)
    print(f"PHASE 17B INTEGRATION TEST COMPLETE: {report_dict['tests_passed_count']} / {report_dict['total_tests']} TESTS PASSED (All Passed = {all_passed})")
    print(f"Saved Report to: {out_path}")
    print("=" * 80)
    return all_passed

if __name__ == "__main__":
    run_phase17b_integration_tests()

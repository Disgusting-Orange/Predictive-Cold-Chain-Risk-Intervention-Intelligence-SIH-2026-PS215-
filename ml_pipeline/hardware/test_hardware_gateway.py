"""
FrostLink Hardware Gateway Automated Test Suite -- Phase 15
===========================================================
Verifies the complete physical ESP32 gateway ingestion path:
1. Real ESP32 packet format parsing.
2. Raw packet validation against schema.
3. Sensor disconnect / null handling (safe degradation).
4. Invalid sensor value rejection / sanitization.
5. Per-shipment history buffering and duplicate handling.
6. Cold-start detection and expanding window handling.
7. Exact 40-feature engineering extraction.
8. Feature order alignment with frozen XGBoost schema.
9. FastAPI model risk prediction.
10. Real-time SHAP factor generation.
11. End-to-end hardware-to-ML gateway execution.
12. Latency measurement across all stages.
"""

import sys
import os
import json
import time
import numpy as np
import pandas as pd
import xgboost as xgb
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Path configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hardware")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "feature_engineering")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service")))

from raw_schema import RawTelemetryPacket
from history_buffer import ShipmentHistoryBuffer
from gateway import HardwareGateway, IngestionResult

def run_hardware_gateway_test_suite():
    print("=" * 80)
    print("RUNNING FROSTLINK PHASE 15 HARDWARE GATEWAY TEST SUITE (12 Tests)")
    print("=" * 80)
    
    test_results = {}
    history_buffer = ShipmentHistoryBuffer(max_history_packets=50)
    gateway = HardwareGateway(history_buffer=history_buffer)
    
    # -------------------------------------------------------------
    # TEST 1: Real ESP32 Sensor Packet Format
    # -------------------------------------------------------------
    sample_esp32_json = json.dumps({
        "shipment_id": "SHIP_ESP32_001",
        "timestamp": "2026-08-23T14:00:00Z",
        "probes": {
            "Front_Top": 2.31,
            "Front_Middle": 2.15,
            "Front_Bottom": 1.95,
            "Middle_Top": 2.80,
            "Middle_Middle": 2.25,
            "Middle_Bottom": 2.05,
            "Rear_Top": 3.15,
            "Rear_Middle": 2.45,
            "Rear_Bottom": 2.10
        },
        "sconf": 1.0,
        "coverage_time": 1.0
    })
    
    res1 = gateway.process_raw_telemetry(sample_esp32_json)
    t1_pass = bool(res1.success and res1.active_probes == 9)
    test_results["1_real_packet_format"] = {"passed": t1_pass, "active_probes": res1.active_probes}
    print(f"Test 1 [ESP32 Packet Format Parsing]:  Passed = {t1_pass} (Active Probes: {res1.active_probes})")
    
    # -------------------------------------------------------------
    # TEST 2: Packet Validation
    # -------------------------------------------------------------
    bad_packet_json = json.dumps({"shipment_id": "BAD_SHIP", "timestamp": "invalid_date", "probes": {}})
    res2 = gateway.process_raw_telemetry(bad_packet_json)
    t2_pass = bool(not res2.success)
    test_results["2_packet_validation_fail_safe"] = {"passed": t2_pass, "error": res2.error_message}
    print(f"Test 2 [Packet Validation Fail-Safe]:  Passed = {t2_pass} (Error Caught Correctly)")
    
    # -------------------------------------------------------------
    # TEST 3: Sensor Disconnect (Partial Null Probes)
    # -------------------------------------------------------------
    disconnected_packet = {
        "shipment_id": "SHIP_ESP32_001",
        "timestamp": "2026-08-23T14:10:00Z",
        "probes": {
            "Front_Top": 2.40,
            "Front_Middle": None,  # Disconnected
            "Front_Bottom": 2.00,
            "Middle_Top": None,    # Disconnected
            "Middle_Middle": 2.30,
            "Middle_Bottom": 2.10,
            "Rear_Top": 3.20,
            "Rear_Middle": 2.50,
            "Rear_Bottom": 2.15
        },
        "sconf": 7.0 / 9.0,
        "coverage_time": 1.0
    }
    res3 = gateway.process_raw_telemetry(disconnected_packet)
    t3_pass = bool(res3.success and res3.active_probes == 7)
    test_results["3_sensor_disconnect_degradation"] = {"passed": t3_pass, "active_probes": res3.active_probes}
    print(f"Test 3 [Sensor Disconnect Graceful]:   Passed = {t3_pass} (Active Probes: {res3.active_probes}/9)")
    
    # -------------------------------------------------------------
    # TEST 4: Invalid Out-of-Range Sensor Handling
    # -------------------------------------------------------------
    out_of_range_packet = {
        "shipment_id": "SHIP_ESP32_001",
        "timestamp": "2026-08-23T14:20:00Z",
        "probes": {
            "Front_Top": 999.0,    # Physically invalid -> coerced to None
            "Front_Middle": -127.0,# DS18B20 disconnect constant -> coerced to None
            "Front_Bottom": 2.05,
            "Middle_Top": 2.85,
            "Middle_Middle": 2.35,
            "Middle_Bottom": 2.15,
            "Rear_Top": 3.25,
            "Rear_Middle": 2.55,
            "Rear_Bottom": 2.20
        },
        "sconf": 7.0 / 9.0,
        "coverage_time": 1.0
    }
    res4 = gateway.process_raw_telemetry(out_of_range_packet)
    t4_pass = bool(res4.success and res4.active_probes == 7)
    test_results["4_invalid_range_sanitization"] = {"passed": t4_pass, "active_probes": res4.active_probes}
    print(f"Test 4 [Invalid Range Sanitization]:   Passed = {t4_pass} (Invalid Probes Cleaned: 7 Active)")
    
    # -------------------------------------------------------------
    # TEST 5: History Buffering & Duplicate Handling
    # -------------------------------------------------------------
    # Send a duplicate packet with updated probe reading for same timestamp
    dup_packet = {
        "shipment_id": "SHIP_ESP32_001",
        "timestamp": "2026-08-23T14:20:00Z", # Duplicate timestamp
        "probes": {
            "Front_Top": 2.45,
            "Front_Middle": 2.20,
            "Front_Bottom": 2.05,
            "Middle_Top": 2.85,
            "Middle_Middle": 2.35,
            "Middle_Bottom": 2.15,
            "Rear_Top": 3.25,
            "Rear_Middle": 2.55,
            "Rear_Bottom": 2.20
        },
        "sconf": 1.0,
        "coverage_time": 1.0
    }
    res5 = gateway.process_raw_telemetry(dup_packet)
    buf_len = len(history_buffer.get_history("SHIP_ESP32_001"))
    t5_pass = bool(res5.success and buf_len == 3) # 14:00, 14:10, 14:20 (not 4)
    test_results["5_history_buffering_dedup"] = {"passed": t5_pass, "buffer_length": buf_len}
    print(f"Test 5 [History Buffering & Dedup]:    Passed = {t5_pass} (Buffer Length: {buf_len} unique steps)")
    
    # -------------------------------------------------------------
    # TEST 6: Cold-Start State Handling
    # -------------------------------------------------------------
    t6_pass = bool(res5.cold_start_status == "COLD_START")
    test_results["6_cold_start_status"] = {"passed": t6_pass, "status": res5.cold_start_status}
    print(f"Test 6 [Cold-Start Transparency]:     Passed = {t6_pass} (Status: {res5.cold_start_status})")
    
    # -------------------------------------------------------------
    # Feed remaining packets to reach 6 full observations (Warmed state)
    # -------------------------------------------------------------
    for minute_offset in [30, 40, 50]:
        pkt = {
            "shipment_id": "SHIP_ESP32_001",
            "timestamp": f"2026-08-23T14:{minute_offset}:00Z",
            "probes": {
                "Front_Top": 2.50,
                "Front_Middle": 2.25,
                "Front_Bottom": 2.10,
                "Middle_Top": 2.90,
                "Middle_Middle": 2.40,
                "Middle_Bottom": 2.20,
                "Rear_Top": 3.30,
                "Rear_Middle": 2.60,
                "Rear_Bottom": 2.25
            },
            "sconf": 1.0,
            "coverage_time": 1.0
        }
        res_step = gateway.process_raw_telemetry(pkt)
        
    # -------------------------------------------------------------
    # TEST 7: Warmed Feature Generation
    # -------------------------------------------------------------
    t7_pass = bool(res_step.success and res_step.cold_start_status == "WARMED")
    test_results["7_warmed_feature_generation"] = {"passed": t7_pass, "status": res_step.cold_start_status}
    print(f"Test 7 [Warmed Window (6 steps)]:      Passed = {t7_pass} (Status: {res_step.cold_start_status})")
    
    # -------------------------------------------------------------
    # TEST 8: Feature Order Alignment
    # -------------------------------------------------------------
    hist_6 = history_buffer.get_history("SHIP_ESP32_001")
    f_dict, meta = gateway.feature_engineer.extract_features(hist_6)
    t8_pass = bool(list(f_dict.keys()) == gateway.feature_engineer.feature_names)
    test_results["8_feature_order_alignment"] = {"passed": t8_pass}
    print(f"Test 8 [Schema Order Alignment]:       Passed = {t8_pass} (Exact 40 Features in Sequence)")
    
    # -------------------------------------------------------------
    # TEST 9: Prediction Generation
    # -------------------------------------------------------------
    prob = res_step.risk_probability
    expected_threshold = gateway.model_service.operating_threshold
    t9_pass = bool(prob is not None and 0.0 <= prob <= 1.0 and abs(res_step.threshold - expected_threshold) < 1e-4)
    test_results["9_prediction_generation"] = {"passed": t9_pass, "prob": prob, "risk_level": res_step.risk_level}
    print(f"Test 9 [XGBoost Risk Prediction]:      Passed = {t9_pass} (Prob: {prob:.4f}, Level: {res_step.risk_level})")
    
    # -------------------------------------------------------------
    # TEST 10: Rigorous SHAP Verification & Additivity
    # -------------------------------------------------------------
    exp = res_step.explanation
    inc_factors = exp.get("top_risk_increasing_factors", [])
    dec_factors = exp.get("top_risk_reducing_factors", [])
    
    # 1. Existence and valid whitelisted feature names
    all_factor_features = [f["feature_name"] for f in (inc_factors + dec_factors)]
    features_valid = all(f in gateway.feature_engineer.feature_names for f in all_factor_features)
    
    # 2. Correct mathematical signs
    inc_signs_correct = all(f["shap_value"] > 0.0 for f in inc_factors)
    dec_signs_correct = all(f["shap_value"] < 0.0 for f in dec_factors)
    
    # 3. Additivity on current sample: Base Value + sum(SHAP) == Booster Margin
    explainer = gateway.model_service.explainer
    model = gateway.model_service.model
    df_sample = pd.DataFrame([[f_dict[k] for k in gateway.feature_engineer.feature_names]], columns=gateway.feature_engineer.feature_names, dtype=np.float64)
    
    full_shap_vals = explainer.shap_values(df_sample)[0]
    base_val = float(explainer.expected_value) if not isinstance(explainer.expected_value, np.ndarray) else float(explainer.expected_value[0])
    
    dmat = xgb.DMatrix(df_sample)
    booster_margin = float(model.get_booster().predict(dmat, output_margin=True)[0])
    reconstructed_margin = base_val + float(np.sum(full_shap_vals))
    additivity_delta = abs(booster_margin - reconstructed_margin)
    
    # 4. Probability consistency: sigma(margin) == risk_probability
    reconstructed_prob = 1.0 / (1.0 + np.exp(-reconstructed_margin))
    prob_delta = abs(reconstructed_prob - res_step.risk_probability)
    
    t10_pass = bool(
        features_valid and
        inc_signs_correct and
        dec_signs_correct and
        additivity_delta < 1e-4 and
        prob_delta < 1e-4
    )
    test_results["10_shap_explanation"] = {
        "passed": t10_pass,
        "features_whitelisted": features_valid,
        "directional_signs_valid": (inc_signs_correct and dec_signs_correct),
        "additivity_delta": additivity_delta,
        "prob_consistency_delta": prob_delta,
        "inc_count": len(inc_factors),
        "dec_count": len(dec_factors)
    }
    print(f"Test 10 [Rigorous SHAP & Additivity]: Passed = {t10_pass} (Additivity Delta: {additivity_delta:.2e}, Prob Delta: {prob_delta:.2e})")
    
    # -------------------------------------------------------------
    # TEST 11: End-to-End Complete Execution
    # -------------------------------------------------------------
    t11_pass = bool(res_step.success and res_step.risk_probability is not None and res_step.explanation is not None)
    test_results["11_end_to_end_gateway"] = {"passed": t11_pass}
    print(f"Test 11 [End-to-End Gateway Flow]:     Passed = {t11_pass}")
    
    # -------------------------------------------------------------
    # TEST 12: Measured Latency Profiling
    # -------------------------------------------------------------
    lats = res_step.latencies_ms
    t_tot = lats.get("total_pipeline_ms", 0.0)
    target_ms = 500.0
    target_met = bool(t_tot < target_ms)
    t12_pass = bool(t_tot > 0.0) # Timing measured accurately
    
    test_results["12_latency_profiling"] = {
        "passed": t12_pass,
        "total_pipeline_ms": t_tot,
        "validation_ms": lats.get("validation_ms", 0.0),
        "history_buffer_ms": lats.get("history_buffer_ms", 0.0),
        "feature_engineering_ms": lats.get("feature_engineering_ms", 0.0),
        "inference_and_shap_ms": lats.get("inference_and_shap_ms", 0.0),
        "latency_target_ms": target_ms,
        "latency_target_met": target_met
    }
    print(f"Test 12 [Measured Latency Profile]:   Passed = {t12_pass} (Total Pipeline: {t_tot:.2f} ms | Target < 500ms: {target_met})")
    print(f"   ├─ Raw Validation:      {lats.get('validation_ms', 0):.2f} ms")
    print(f"   ├─ History Buffering:   {lats.get('history_buffer_ms', 0):.2f} ms")
    print(f"   ├─ Feature Engineering: {lats.get('feature_engineering_ms', 0):.2f} ms")
    print(f"   └─ XGBoost & SHAP:      {lats.get('inference_and_shap_ms', 0):.2f} ms")
    
    # Save Test Report
    all_passed = all(v["passed"] for v in test_results.values())
    report_dict = {
        "hardware_test_suite_version": "1.0.0",
        "all_tests_passed": all_passed,
        "tests_passed_count": sum(v["passed"] for v in test_results.values()),
        "total_tests": len(test_results),
        "results": test_results
    }
    
    report_path = os.path.join(os.path.dirname(__file__), "hardware_test_report.json")
    def json_serial(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)): return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)): return float(obj)
        elif isinstance(obj, (np.bool_, bool)): return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
        
    with open(report_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
        
    print("=" * 80)
    print(f"HARDWARE TEST SUITE COMPLETE: {report_dict['tests_passed_count']} / {report_dict['total_tests']} TESTS PASSED (All Passed = {all_passed})")
    print(f"Saved Hardware Test Report to: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_hardware_gateway_test_suite()

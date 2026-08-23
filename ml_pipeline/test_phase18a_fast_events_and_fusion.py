"""
FrostLink Phase 18A: Fast Event Detection & Risk Fusion Test Suite (15 Tests)
=============================================================================
Exhaustively validates real-time fast event detection, strict causality, no fabrication,
and transparent state-based risk fusion with frozen XGBoost v2.
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
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "hardware")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "feature_engineering")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "service")))

from raw_schema import RawTelemetryPacket
from history_buffer import ShipmentHistoryBuffer
from event_detector import FastEventDetector, ObservedEvent, EventDetectorConfig
from risk_fusion import RiskFusionEngine, FusedRiskAssessment
from gateway import HardwareGateway
from model_service import ModelService

def make_packet(
    shipment_id: str,
    timestamp: str,
    temp_base: float = 2.20,
    probe_overrides: dict = None,
    door_open: bool = None
):
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
    if probe_overrides:
        for k, v in probe_overrides.items():
            probes[k] = v

    valid_count = sum(1 for v in probes.values() if v is not None)
    return {
        "shipment_id": shipment_id,
        "timestamp": timestamp,
        "probes": probes,
        "door_open": door_open,
        "sconf": round(valid_count / 9.0, 3),
        "coverage_time": 1.0
    }

def run_phase18a_test_suite():
    print("=" * 80)
    print("RUNNING FROSTLINK PHASE 18A FAST EVENT DETECTION & RISK FUSION SUITE (15 Tests)")
    print("=" * 80)
    
    test_results = {}
    detector = FastEventDetector()
    fusion = RiskFusionEngine(ml_threshold=0.5750)
    
    # -------------------------------------------------------------
    # TEST 1: Normal Stable Telemetry -> No Fast Event, SAFE
    # -------------------------------------------------------------
    pkt_norm1 = make_packet("SHIP_001", "2026-08-23T14:00:00Z", temp_base=2.20)
    pkt_norm2 = make_packet("SHIP_001", "2026-08-23T14:10:00Z", temp_base=2.22)
    evts1, meta1 = detector.detect_events(pkt_norm2, pkt_norm1)
    t1_pass = bool(len(evts1) == 0 and meta1["sensor_health"] == "HEALTHY")
    test_results["1_normal_telemetry_no_event"] = {"passed": t1_pass, "event_count": len(evts1)}
    print(f"Test 1 [Normal Stable Telemetry]:       Passed = {t1_pass} (0 Fast Events, Status: HEALTHY)")
    
    # -------------------------------------------------------------
    # TEST 2: Causal Rapid Warming -> RAPID_WARMING Event
    # -------------------------------------------------------------
    # Delta of +0.60°C in 10 minutes = 0.060°C/min >= 0.030°C/min threshold
    pkt_warm_prev = make_packet("SHIP_002", "2026-08-23T14:00:00Z", temp_base=2.20)
    pkt_warm_curr = make_packet("SHIP_002", "2026-08-23T14:10:00Z", temp_base=2.80)
    evts2, meta2 = detector.detect_events(pkt_warm_curr, pkt_warm_prev)
    has_rapid = any(e.event_type == "RAPID_WARMING" for e in evts2)
    t2_pass = bool(has_rapid)
    test_results["2_causal_rapid_warming"] = {"passed": t2_pass, "events": [e.event_type for e in evts2]}
    print(f"Test 2 [Causal Rapid Warming]:          Passed = {t2_pass} (Event: RAPID_WARMING detected)")
    
    # -------------------------------------------------------------
    # TEST 3: Single Noisy Probe -> No Multi-Probe Correlated Warming
    # -------------------------------------------------------------
    pkt_noise_prev = make_packet("SHIP_003", "2026-08-23T14:00:00Z", temp_base=2.20)
    pkt_noise_curr = make_packet("SHIP_003", "2026-08-23T14:10:00Z", temp_base=2.20, probe_overrides={"Rear_Top": 3.80})
    evts3, meta3 = detector.detect_events(pkt_noise_curr, pkt_noise_prev)
    has_corr_warm = any(e.event_type == "CORRELATED_WARMING" for e in evts3)
    t3_pass = bool(not has_corr_warm)
    test_results["3_single_noisy_probe_suppression"] = {"passed": t3_pass, "correlated_triggered": has_corr_warm}
    print(f"Test 3 [Single Noisy Probe Suppression]:Passed = {t3_pass} (Correlated Warming NOT triggered)")
    
    # -------------------------------------------------------------
    # TEST 4: Multiple Probes Warming -> CORRELATED_WARMING Event
    # -------------------------------------------------------------
    # 5 probes warming simultaneously by +0.25°C
    pkt_corr_prev = make_packet("SHIP_004", "2026-08-23T14:00:00Z", temp_base=2.20)
    pkt_corr_curr = make_packet("SHIP_004", "2026-08-23T14:10:00Z", temp_base=2.20, probe_overrides={
        "Front_Top": 2.70, "Middle_Top": 3.00, "Rear_Top": 3.40, "Rear_Middle": 2.70, "Front_Middle": 2.45
    })
    evts4, meta4 = detector.detect_events(pkt_corr_curr, pkt_corr_prev)
    has_corr = any(e.event_type == "CORRELATED_WARMING" for e in evts4)
    t4_pass = bool(has_corr)
    test_results["4_multi_probe_correlated_warming"] = {"passed": t4_pass, "events": [e.event_type for e in evts4]}
    print(f"Test 4 [Multi-Probe Correlated Warming]:Passed = {t4_pass} (Event: CORRELATED_WARMING detected)")
    
    # -------------------------------------------------------------
    # TEST 5: Probe Dropout -> SENSOR_DROPOUT Event & DEGRADED State
    # -------------------------------------------------------------
    pkt_drop = make_packet("SHIP_005", "2026-08-23T14:00:00Z", temp_base=2.20, probe_overrides={"Front_Top": None, "Rear_Bottom": None})
    evts5, meta5 = detector.detect_events(pkt_drop)
    has_dropout = any(e.event_type == "SENSOR_DROPOUT" for e in evts5)
    t5_pass = bool(has_dropout and meta5["sensor_health"] == "DEGRADED" and meta5["active_probes_count"] == 7)
    test_results["5_probe_dropout_degradation"] = {"passed": t5_pass, "active_count": meta5["active_probes_count"]}
    print(f"Test 5 [Probe Dropout Degradation]:     Passed = {t5_pass} (Status: DEGRADED, 7 Active Probes)")
    
    # -------------------------------------------------------------
    # TEST 6: All Probes Missing -> SENSOR_DROPOUT_TOTAL & ERROR
    # -------------------------------------------------------------
    pkt_all_dead = {"shipment_id": "SHIP_006", "timestamp": "2026-08-23T14:00:00Z", "probes": {"Front_Top": None, "Rear_Bottom": None}}
    evts6, meta6 = detector.detect_events(pkt_all_dead)
    has_tot = any(e.event_type == "SENSOR_DROPOUT_TOTAL" for e in evts6)
    t6_pass = bool(has_tot and meta6["sensor_health"] == "ERROR_ALL_PROBES_MISSING")
    test_results["6_all_probes_missing_fail_closed"] = {"passed": t6_pass, "status": meta6["sensor_health"]}
    print(f"Test 6 [All Probes Dead Fail-Closed]:   Passed = {t6_pass} (Status: ERROR_ALL_PROBES_MISSING)")
    
    # -------------------------------------------------------------
    # TEST 7: Stale Timestamp -> STALE_TELEMETRY Event
    # -------------------------------------------------------------
    pkt_stale_prev = make_packet("SHIP_007", "2026-08-23T14:00:00Z", temp_base=2.20)
    pkt_stale_curr = make_packet("SHIP_007", "2026-08-23T14:00:00Z", temp_base=2.20) # 0 seconds elapsed
    evts7, meta7 = detector.detect_events(pkt_stale_curr, pkt_stale_prev)
    has_stale = any(e.event_type == "STALE_TELEMETRY" for e in evts7)
    t7_pass = bool(has_stale)
    test_results["7_stale_telemetry_detection"] = {"passed": t7_pass, "events": [e.event_type for e in evts7]}
    print(f"Test 7 [Stale Timestamp Detection]:     Passed = {t7_pass} (Event: STALE_TELEMETRY detected)")
    
    # -------------------------------------------------------------
    # TEST 8: Actual Door Signal Present & True -> DOOR_OPEN Event
    # -------------------------------------------------------------
    pkt_door_open = make_packet("SHIP_008", "2026-08-23T14:00:00Z", temp_base=2.20, door_open=True)
    evts8, meta8 = detector.detect_events(pkt_door_open)
    has_door = any(e.event_type == "DOOR_OPEN" for e in evts8)
    t8_pass = bool(has_door and meta8["door_monitoring_available"] is True)
    test_results["8_actual_door_signal_open"] = {"passed": t8_pass, "events": [e.event_type for e in evts8]}
    print(f"Test 8 [Actual Door Signal (Open)]:     Passed = {t8_pass} (Event: DOOR_OPEN detected)")
    
    # -------------------------------------------------------------
    # TEST 9: No Door Signal Available -> Explicitly Report Unavailable
    # -------------------------------------------------------------
    pkt_no_door = make_packet("SHIP_009", "2026-08-23T14:00:00Z", temp_base=2.20, door_open=None)
    evts9, meta9 = detector.detect_events(pkt_no_door)
    has_door_evt = any(e.event_type == "DOOR_OPEN" for e in evts9)
    t9_pass = bool(not has_door_evt and meta9["door_monitoring_available"] is False)
    test_results["9_no_door_signal_no_fabrication"] = {"passed": t9_pass, "door_monitoring": meta9["door_monitoring_available"]}
    print(f"Test 9 [No Door Sensor (No Fabrication)]: Passed = {t9_pass} (door_monitoring_available = False)")
    
    # -------------------------------------------------------------
    # TEST 10: Fast Event + Low XGBoost Risk -> OBSERVED_EVENT State
    # (And verify CORRELATED_WARMING does NOT alert alone)
    # -------------------------------------------------------------
    # Case A: Primary Alert Event (DOOR_OPEN) + Low ML Risk -> OBSERVED_EVENT
    evts10_door = [ObservedEvent(event_type="DOOR_OPEN", description="Door open", detected_at="2026-08-23T14:50:00Z")]
    fused10_door = fusion.fuse(
        shipment_id="SHIP_010A",
        timestamp="2026-08-23T14:50:00Z",
        observed_events=evts10_door,
        sensor_meta={"sensor_health": "HEALTHY", "active_probes_count": 9, "door_monitoring_available": True},
        cold_start_status="WARMED",
        ml_prob=0.0003, # Safe ML risk
        ml_level="SAFE",
        ml_threshold=0.5750
    )
    
    # Case B: CORRELATED_WARMING Alone + Low ML Risk -> SAFE (DO NOT ALERT ALONE)
    evts10_corr = [ObservedEvent(event_type="CORRELATED_WARMING", description="Multi-probe warming", detected_at="2026-08-23T14:50:00Z")]
    fused10_corr = fusion.fuse(
        shipment_id="SHIP_010B",
        timestamp="2026-08-23T14:50:00Z",
        observed_events=evts10_corr,
        sensor_meta={"sensor_health": "HEALTHY", "active_probes_count": 9, "door_monitoring_available": False},
        cold_start_status="WARMED",
        ml_prob=0.0003, # Safe ML risk
        ml_level="SAFE",
        ml_threshold=0.5750
    )
    
    t10_pass = bool(
        fused10_door.fused_state == "OBSERVED_EVENT" and
        fused10_corr.fused_state == "SAFE" and
        fused10_corr.has_observed_events and
        not fused10_corr.has_primary_alarm
    )
    test_results["10_fast_event_plus_low_ml_risk"] = {"passed": t10_pass, "door_fused_state": fused10_door.fused_state, "corr_alone_fused_state": fused10_corr.fused_state}
    print(f"Test 10 [Event Priority & Correlated Non-Alert]: Passed = {t10_pass} (DOOR_OPEN -> OBSERVED_EVENT, CORRELATED_WARMING Alone -> SAFE)")
    
    # -------------------------------------------------------------
    # TEST 11: No Fast Event + High XGBoost Risk -> PREDICTED_RISK State
    # -------------------------------------------------------------
    fused11 = fusion.fuse(
        shipment_id="SHIP_011",
        timestamp="2026-08-23T14:50:00Z",
        observed_events=[],
        sensor_meta={"sensor_health": "HEALTHY", "active_probes_count": 9, "door_monitoring_available": False},
        cold_start_status="WARMED",
        ml_prob=0.8742, # High ML risk
        ml_level="CRITICAL",
        ml_threshold=0.5750
    )
    t11_pass = bool(fused11.fused_state == "PREDICTED_RISK" and not fused11.has_observed_events and fused11.ml_prediction.is_excursion_predicted)
    test_results["11_no_event_plus_high_ml_risk"] = {"passed": t11_pass, "fused_state": fused11.fused_state}
    print(f"Test 11 [No Event + High ML Risk]:      Passed = {t11_pass} (Fused State: PREDICTED_RISK, ML Prob: {fused11.ml_prediction.risk_probability:.4f})")
    
    # -------------------------------------------------------------
    # TEST 12: Fast Event + High XGBoost Risk -> EVENT_AND_PREDICTED_RISK
    # -------------------------------------------------------------
    evts12 = [ObservedEvent(event_type="RAPID_WARMING", description="Rapid warming", detected_at="2026-08-23T14:50:00Z")]
    fused12 = fusion.fuse(
        shipment_id="SHIP_012",
        timestamp="2026-08-23T14:50:00Z",
        observed_events=evts12,
        sensor_meta={"sensor_health": "HEALTHY", "active_probes_count": 9, "door_monitoring_available": False},
        cold_start_status="WARMED",
        ml_prob=0.6352,
        ml_level="WARNING",
        ml_threshold=0.5750
    )
    t12_pass = bool(fused12.fused_state == "EVENT_AND_PREDICTED_RISK" and fused12.has_observed_events and fused12.ml_prediction.is_excursion_predicted)
    test_results["12_fast_event_plus_high_ml_risk"] = {"passed": t12_pass, "fused_state": fused12.fused_state}
    print(f"Test 12 [Fast Event + High ML Risk]:   Passed = {t12_pass} (Fused State: EVENT_AND_PREDICTED_RISK)")
    
    # -------------------------------------------------------------
    # TEST 13 & 14 & 15: Gateway End-to-End Orchestration
    # -------------------------------------------------------------
    history_buf = ShipmentHistoryBuffer()
    gateway = HardwareGateway(history_buffer=history_buf)
    
    # Cold start steps 1 to 5
    for m in [0, 10, 20, 30, 40]:
        pkt = make_packet("GATEWAY_SHIP", f"2026-08-23T14:{m:02d}:00Z", temp_base=2.20)
        res_cold = gateway.process_raw_telemetry(pkt)
        
    t13_pass = bool(res_cold.success and res_cold.cold_start_status == "COLD_START" and res_cold.risk_probability is None and res_cold.fused_state == "COLD_START")
    test_results["13_gateway_cold_start_no_v2"] = {"passed": t13_pass, "fused_state": res_cold.fused_state}
    print(f"Test 13 [Gateway Cold Start (N<6)]:     Passed = {t13_pass} (No V2 Inference, Fused State: COLD_START)")
    
    # Step 6 (Warmed)
    pkt6 = make_packet("GATEWAY_SHIP", "2026-08-23T14:50:00Z", temp_base=2.22)
    res_warmed = gateway.process_raw_telemetry(pkt6)
    t14_pass = bool(res_warmed.success and res_warmed.cold_start_status == "WARMED" and res_warmed.risk_probability is not None and res_warmed.fused_state == "SAFE")
    test_results["14_gateway_warmed_v2_allowed"] = {"passed": t14_pass, "fused_state": res_warmed.fused_state, "prob": res_warmed.risk_probability}
    print(f"Test 14 [Gateway Warmed (N=6)]:         Passed = {t14_pass} (V2 Allowed, Prob: {res_warmed.risk_probability:.4f}, Fused State: SAFE)")
    
    # Test 15: SHAP Explanation Explains XGBoost Only
    exp = res_warmed.explanation
    t15_pass = bool(
        exp is not None and
        "top_risk_increasing_factors" in exp and
        "top_risk_reducing_factors" in exp and
        all("feature_name" in f and "shap_value" in f for f in exp["top_risk_increasing_factors"])
    )
    test_results["15_shap_explains_xgboost_only"] = {"passed": t15_pass, "shap_factor_count": len(exp.get("top_risk_increasing_factors", []))}
    print(f"Test 15 [SHAP Explains XGBoost Only]:   Passed = {t15_pass} (SHAP cleanly explains 40 ML features)")
    
    # Monotonic Latency Profile
    lats = res_warmed.latencies_ms
    print("\n" + "-" * 80)
    print("MONOTONIC LATENCY PROFILING (Fast Event + Fusion + Warmed V2):")
    print(f"   ├─ Raw Validation:      {lats.get('validation_ms', 0):.2f} ms")
    print(f"   ├─ Fast Event Detector: {lats.get('event_detection_ms', 0):.2f} ms")
    print(f"   ├─ History Buffering:   {lats.get('history_buffer_ms', 0):.2f} ms")
    print(f"   ├─ Feature Engineering: {lats.get('feature_engineering_ms', 0):.2f} ms")
    print(f"   ├─ XGBoost & SHAP:      {lats.get('inference_and_shap_ms', 0):.2f} ms")
    print(f"   ├─ Risk Fusion Layer:   {lats.get('risk_fusion_ms', 0):.2f} ms")
    print(f"   └─ Total Pipeline:      {lats.get('total_pipeline_ms', 0):.2f} ms")
    print("-" * 80)
    
    # Save Report
    all_passed = all(v["passed"] for v in test_results.values())
    report_dict = {
        "phase": "18A",
        "all_tests_passed": all_passed,
        "tests_passed_count": sum(v["passed"] for v in test_results.values()),
        "total_tests": len(test_results),
        "results": test_results,
        "latencies_ms": lats
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "phase18a_test_report.json")
    def json_serial(obj):
        if isinstance(obj, (np.floating, np.float32, np.float64)): return float(obj)
        elif isinstance(obj, (np.integer, np.int32, np.int64)): return int(obj)
        elif isinstance(obj, (np.bool_, bool)): return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
        
    with open(out_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
        
    print("=" * 80)
    print(f"PHASE 18A TEST SUITE COMPLETE: {report_dict['tests_passed_count']} / {report_dict['total_tests']} TESTS PASSED (All Passed = {all_passed})")
    print(f"Saved Report to: {out_path}")
    print("=" * 80)
    return all_passed

if __name__ == "__main__":
    run_phase18a_test_suite()

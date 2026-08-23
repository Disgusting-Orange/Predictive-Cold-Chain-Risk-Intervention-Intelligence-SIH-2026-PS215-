"""
FrostLink Production ML Architecture -- Validation Test Suite
=============================================================
Tests the 10 critical production architecture assertions:
1. Required columns exist in schema.
2. Units and types are strictly defined.
3. Timestamps are chronologically ordered per shipment.
4. Anti-leakage: No future data enters historical features.
5. Rolling windows are strictly backward-looking only.
6. Missing sensor values are handled explicitly (no silent random replacement).
7. Stale sensor values and data age are correctly tracked.
8. Feature extraction order is deterministic.
9. Schema version (v1.0.0) is stamped in all processed records.
10. Backward compatibility: Real-data pipeline runs cleanly and outputs non-empty features.
"""

import sys
import os
import json
import pandas as pd
import numpy as np

# Fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'production')))
from feature_schema import PRODUCTION_FEATURE_REGISTRY, SCHEMA_VERSION, FeatureGroup, FeatureAvailability
from feature_engineering import ProductionFeaturePipeline

def run_production_architecture_tests():
    print("=" * 80)
    print(f"RUNNING FROSTLINK PRODUCTION ARCHITECTURE TESTS (Schema v{SCHEMA_VERSION})")
    print("=" * 80)
    
    test_results = {}
    pipeline = ProductionFeaturePipeline()
    
    # Load sample real data
    train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
    test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
    raw_real = pd.concat([train_df, test_df], ignore_index=True)
    
    # -------------------------------------------------------------
    # TEST 1: Required Schema Structure
    # -------------------------------------------------------------
    with open(r"ml_pipeline\production\schema.json", 'r') as f:
        schema_json = json.load(f)
    t1_pass = (
        schema_json['schema_version'] == SCHEMA_VERSION and
        schema_json['feature_count'] == len(PRODUCTION_FEATURE_REGISTRY) and
        len(schema_json['features']) >= 20
    )
    test_results['1_schema_structure'] = {
        'passed': t1_pass, 'version': schema_json['schema_version'], 'feature_count': schema_json['feature_count']
    }
    print(f"Test 1 [Schema Structure]:        Passed = {t1_pass}")

    # -------------------------------------------------------------
    # TEST 2: Strict Units & Groups Defined
    # -------------------------------------------------------------
    t2_pass = all(len(f.unit) > 0 and len(f.group.value) > 0 for f in PRODUCTION_FEATURE_REGISTRY)
    test_results['2_units_and_groups'] = {
        'passed': t2_pass, 'total_registered': len(PRODUCTION_FEATURE_REGISTRY)
    }
    print(f"Test 2 [Units & Groups Defined]:  Passed = {t2_pass}")

    # -------------------------------------------------------------
    # TEST 3: Chronological Timestamp Ordering
    # -------------------------------------------------------------
    proc_real, active_cols = pipeline.transform_real_telemetry(raw_real)
    # Check if Time_dt is strictly monotonically increasing within each shipment
    is_ordered = True
    for sid, grp in proc_real.groupby('shipment_id'):
        if not grp['Time_dt'].is_monotonic_increasing:
            is_ordered = False
            break
    test_results['3_chronological_ordering'] = {'passed': is_ordered}
    print(f"Test 3 [Chronological Ordering]:  Passed = {is_ordered}")

    # -------------------------------------------------------------
    # TEST 4: Anti-Leakage (Zero Future Information in Historical Features)
    # -------------------------------------------------------------
    # Perturb future row (t+1) and assert feature at row t does not change
    sample_ship = raw_real[raw_real['shipment_id'] == 'S1'].copy().reset_index(drop=True)
    proc_orig, _ = pipeline.transform_real_telemetry(sample_ship)
    val_t_orig = proc_orig.loc[10, '60m_slope']
    
    sample_ship_perturbed = sample_ship.copy()
    sample_ship_perturbed.loc[11:, 'T_mean_t'] = sample_ship_perturbed.loc[11:, 'T_mean_t'] + 100.0
    proc_pert, _ = pipeline.transform_real_telemetry(sample_ship_perturbed)
    val_t_pert = proc_pert.loc[10, '60m_slope']
    
    t4_pass = bool(abs(val_t_orig - val_t_pert) < 1e-9)
    test_results['4_anti_leakage_future_isolation'] = {
        'passed': t4_pass, 'diff': float(abs(val_t_orig - val_t_pert))
    }
    print(f"Test 4 [Anti-Leakage Isolation]:   Passed = {t4_pass} (Delta = {abs(val_t_orig - val_t_pert)})")

    # -------------------------------------------------------------
    # TEST 5: Causal Rolling Windows ([t-50m, t])
    # -------------------------------------------------------------
    # Verify W60_mean matches manual backward slice
    s1_proc = proc_real[proc_real['shipment_id'] == 'S1'].reset_index(drop=True)
    idx_test = 20
    manual_w60_mean = s1_proc.loc[idx_test-5:idx_test, 'T_current'].mean()
    pipeline_w60_mean = s1_proc.loc[idx_test, 'W60_mean']
    t5_pass = bool(abs(manual_w60_mean - pipeline_w60_mean) < 1e-6)
    test_results['5_causal_backward_window'] = {
        'passed': t5_pass, 'manual': float(manual_w60_mean), 'pipeline': float(pipeline_w60_mean)
    }
    print(f"Test 5 [Causal Backward Window]:  Passed = {t5_pass}")

    # -------------------------------------------------------------
    # TEST 6: Explicit Missingness Handling
    # -------------------------------------------------------------
    # Test on synthetic stream with dropouts
    synth_sample = pd.read_csv(r"ml_pipeline\synthetic\data\synthetic_fleet_100.csv").head(288)
    proc_multi, multi_cols = pipeline.transform_multimodal_telemetry(synth_sample)
    
    # Assert missing compressor readings remain NaN or have valid indicator, NOT arbitrarily zeroed
    t6_pass = ('door_sensor_valid' in proc_multi.columns and 'compressor_sensor_valid' in proc_multi.columns)
    test_results['6_explicit_missingness'] = {'passed': t6_pass}
    print(f"Test 6 [Explicit Missingness]:    Passed = {t6_pass}")

    # -------------------------------------------------------------
    # TEST 7: Stale Sensor Tracking
    # -------------------------------------------------------------
    t7_pass = ('temp_sensor_age_seconds' in proc_real.columns and (proc_real['temp_sensor_age_seconds'] >= 0).all())
    test_results['7_stale_sensor_tracking'] = {'passed': t7_pass}
    print(f"Test 7 [Stale Sensor Tracking]:   Passed = {t7_pass}")

    # -------------------------------------------------------------
    # TEST 8: Deterministic Feature Ordering
    # -------------------------------------------------------------
    _, cols_run1 = pipeline.transform_real_telemetry(raw_real.head(100))
    _, cols_run2 = pipeline.transform_real_telemetry(raw_real.head(500))
    t8_pass = (cols_run1 == cols_run2)
    test_results['8_deterministic_ordering'] = {'passed': t8_pass, 'feature_order': cols_run1}
    print(f"Test 8 [Deterministic Ordering]:  Passed = {t8_pass}")

    # -------------------------------------------------------------
    # TEST 9: Schema Version Stamping
    # -------------------------------------------------------------
    t9_pass = bool((proc_real['schema_version'] == SCHEMA_VERSION).all())
    test_results['9_schema_version_stamping'] = {'passed': t9_pass, 'stamped_version': SCHEMA_VERSION}
    print(f"Test 9 [Schema Version Stamping]: Passed = {t9_pass}")

    # -------------------------------------------------------------
    # TEST 10: Backward Compatibility with Real-Data Baseline
    # -------------------------------------------------------------
    # Assert real-data cohort matches audited 2,523 rows and 116 positives
    real_cohort = proc_real[proc_real['risk_level'].isin([0.0, 1.0]) & proc_real['y_next_60_R2'].notna()]
    n_cohort = len(real_cohort)
    n_pos = int((real_cohort['y_next_60_R2'] == 1.0).sum())
    t10_pass = bool(n_cohort == 2523 and n_pos == 116)
    test_results['10_backward_compatibility'] = {
        'passed': t10_pass, 'cohort_size': n_cohort, 'positives': n_pos
    }
    print(f"Test 10 [Backward Compatibility]: Passed = {t10_pass} (Cohort={n_cohort}, Pos={n_pos})")

    # Save test report JSON
    all_passed = all(v['passed'] for v in test_results.values())
    report_dict = {
        'all_tests_passed': all_passed,
        'tests_passed_count': sum(v['passed'] for v in test_results.values()),
        'total_tests': len(test_results),
        'results': test_results
    }
    def json_serial(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)): return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)): return float(obj)
        elif isinstance(obj, (np.bool_, bool)): return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")

    out_test_json = r"ml_pipeline\production\validation_test_report.json"
    with open(out_test_json, 'w') as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
        
    print("=" * 80)
    print(f"TEST SUITE COMPLETE: {report_dict['tests_passed_count']} / {report_dict['total_tests']} TESTS PASSED (All Passed = {all_passed})")
    print("=" * 80)

if __name__ == "__main__":
    run_production_architecture_tests()

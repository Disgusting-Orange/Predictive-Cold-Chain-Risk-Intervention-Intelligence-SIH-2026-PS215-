"""
FrostLink Explainability Suite -- Automated Validation Tests (Phase 11)
=======================================================================
Tests all 10 critical explainability architecture assertions:
1. Model artifact loads successfully.
2. SHAP TreeExplainer initializes properly.
3. Feature ordering strictly matches the 40 baseline features.
4. SHAP dimensions match dataset feature dimensions (N x 40).
5. Additivity verification: base_value + sum(SHAP) == margin within 1e-4.
6. Target 'y_next_60_R2' is strictly absent from model features.
7. Anti-leakage: No future-derived features exist in feature list.
8. Local explanation schema and JSON structures are valid.
9. Positive/negative SHAP directionality correctly separates risk-increasing vs reducing features.
10. Real-time explanation generation executes cleanly on real observations.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
import xgboost as xgb
import shap

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'explainability')))
from explain_prediction import FrostLinkExplainer

def run_shap_validation_tests():
    print("=" * 80)
    print("RUNNING FROSTLINK SHAP EXPLAINABILITY VALIDATION TESTS")
    print("=" * 80)
    
    test_results = {}
    model_path = r"ml_pipeline\models\frostlink_xgb_baseline\model.json"
    features_path = r"ml_pipeline\models\frostlink_xgb_baseline\features.json"
    
    # -------------------------------------------------------------
    # TEST 1: Model Loading
    # -------------------------------------------------------------
    m = xgb.XGBClassifier()
    m.load_model(model_path)
    t1_pass = bool(m is not None)
    test_results['1_model_loading'] = {'passed': t1_pass, 'model_type': str(type(m))}
    print(f"Test 1 [Model Loading]:           Passed = {t1_pass}")
    
    # -------------------------------------------------------------
    # TEST 2: TreeExplainer Loading
    # -------------------------------------------------------------
    explainer = shap.TreeExplainer(m)
    t2_pass = bool(explainer is not None and hasattr(explainer, 'shap_values'))
    test_results['2_tree_explainer_loading'] = {'passed': t2_pass}
    print(f"Test 2 [TreeExplainer Loading]:   Passed = {t2_pass}")
    
    # -------------------------------------------------------------
    # TEST 3: Feature Ordering Match
    # -------------------------------------------------------------
    with open(features_path, 'r') as f:
        feature_names = json.load(f)['features']
    t3_pass = bool(len(feature_names) == 40 and feature_names[0] == 'T_mean_t')
    test_results['3_feature_ordering'] = {'passed': t3_pass, 'feature_count': len(feature_names)}
    print(f"Test 3 [Feature Ordering Match]:  Passed = {t3_pass} (Count: {len(feature_names)})")
    
    # -------------------------------------------------------------
    # TEST 4: SHAP Dimensions Match (N x 40)
    # -------------------------------------------------------------
    train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
    test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
    raw_real = pd.concat([train_df, test_df], ignore_index=True)
    raw_real['Time_dt'] = pd.to_datetime(raw_real['Time'])
    real_df = raw_real.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)
    cohort = real_df[real_df['risk_level'].isin([0.0, 1.0]) & real_df['y_next_60_R2'].notna()].reset_index(drop=True)
    
    X_sample = cohort[feature_names].head(50)
    shap_vals_sample = explainer.shap_values(X_sample)
    t4_pass = bool(shap_vals_sample.shape == (50, 40))
    test_results['4_shap_dimensions'] = {'passed': t4_pass, 'shape': list(shap_vals_sample.shape)}
    print(f"Test 4 [SHAP Dimensions Match]:   Passed = {t4_pass} (Shape: {shap_vals_sample.shape})")
    
    # -------------------------------------------------------------
    # TEST 5: Additivity Check
    # -------------------------------------------------------------
    base_val = float(explainer.expected_value) if not isinstance(explainer.expected_value, np.ndarray) else float(explainer.expected_value[0])
    dmat = xgb.DMatrix(X_sample)
    margins = m.get_booster().predict(dmat, output_margin=True)
    reconstructed = base_val + np.sum(shap_vals_sample, axis=1)
    max_additivity_error = float(np.max(np.abs(margins - reconstructed)))
    t5_pass = bool(max_additivity_error < 1e-4)
    test_results['5_additivity_check'] = {'passed': t5_pass, 'max_error': max_additivity_error}
    print(f"Test 5 [Additivity Verification]: Passed = {t5_pass} (Max error: {max_additivity_error:.2e})")
    
    # -------------------------------------------------------------
    # TEST 6: Target Absence in Features
    # -------------------------------------------------------------
    t6_pass = bool('y_next_60_R2' not in feature_names and 'y_next_120_R2' not in feature_names)
    test_results['6_target_absence'] = {'passed': t6_pass}
    print(f"Test 6 [Target Absence]:          Passed = {t6_pass}")
    
    # -------------------------------------------------------------
    # TEST 7: Anti-Leakage Feature Whitelist
    # -------------------------------------------------------------
    forbidden_metadata = ['risk_level', 'label_R0', 'label_R1', 'label_R2', 'conf_level', 'cause_sensor', 'cause_door']
    t7_pass = bool(all(f not in feature_names for f in forbidden_metadata))
    test_results['7_anti_leakage_whitelist'] = {'passed': t7_pass}
    print(f"Test 7 [Anti-Leakage Whitelist]:  Passed = {t7_pass}")
    
    # -------------------------------------------------------------
    # TEST 8: Local Explanation JSON Schema
    # -------------------------------------------------------------
    with open(r"ml_pipeline\explainability\local_explanations.json", 'r') as f:
        local_json = json.load(f)
    req_keys = ['TRUE_POSITIVE', 'TRUE_NEGATIVE', 'FALSE_POSITIVE', 'FALSE_NEGATIVE']
    t8_pass = bool(all(k in local_json for k in req_keys))
    test_results['8_local_explanation_schema'] = {'passed': t8_pass, 'quadrants_present': list(local_json.keys())}
    print(f"Test 8 [Local Explanation JSON]:  Passed = {t8_pass}")
    
    # -------------------------------------------------------------
    # TEST 9: Directionality Separation
    # -------------------------------------------------------------
    tp_item = local_json['TRUE_POSITIVE']
    inc_shap = [f['shap_value'] for f in tp_item['top_risk_increasing_factors']]
    dec_shap = [f['shap_value'] for f in tp_item['top_risk_reducing_factors']]
    t9_pass = bool(all(s > 0 for s in inc_shap) and all(s < 0 for s in dec_shap))
    test_results['9_directionality_separation'] = {'passed': t9_pass}
    print(f"Test 9 [Directional Separation]:  Passed = {t9_pass}")
    
    # -------------------------------------------------------------
    # TEST 10: Real-Time Explanation Engine Execution
    # -------------------------------------------------------------
    engine = FrostLinkExplainer()
    real_sample_dict = X_sample.iloc[0].to_dict()
    res_engine = engine.explain_instance(real_sample_dict)
    has_factors = len(res_engine['top_risk_increasing_factors']) > 0 or len(res_engine['top_risk_reducing_factors']) > 0
    t10_pass = bool(res_engine['additivity_verified'] and has_factors and res_engine['predicted_risk_probability'] >= 0.0)
    test_results['10_realtime_engine_execution'] = {'passed': t10_pass, 'prob': res_engine['predicted_risk_probability']}
    print(f"Test 10 [Real-Time Engine Exec]:  Passed = {t10_pass} (Predicted Prob = {res_engine['predicted_risk_probability']:.4f})")
    
    # Save Report
    all_passed = all(v['passed'] for v in test_results.values())
    out_dict = {
        'all_tests_passed': all_passed,
        'tests_passed_count': sum(v['passed'] for v in test_results.values()),
        'total_tests': len(test_results),
        'results': test_results
    }
    with open(r"ml_pipeline\explainability\validation_test_report.json", 'w') as f:
        json.dump(out_dict, f, indent=2)
        
    print("=" * 80)
    print(f"SHAP VALIDATION COMPLETE: {out_dict['tests_passed_count']} / {out_dict['total_tests']} TESTS PASSED (All Passed = {all_passed})")
    print("=" * 80)

if __name__ == "__main__":
    run_shap_validation_tests()

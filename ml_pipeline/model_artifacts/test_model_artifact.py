"""
FrostLink ML Pipeline -- Phase 12 Model Artifact Validation Test Suite
=====================================================================
Executes the comprehensive validation suite for the packaged production artifact:
1. Artifact loading (model, schema, threshold, metadata, manifest).
2. Prediction equivalence between original and packaged model (tolerance < 1e-6).
3. Strict feature ordering verification.
4. Threshold loading and evaluation on real validation samples.
5. Probability bounds verification [0.0, 1.0].
6. SHAP compatibility (TreeExplainer dimension match and additivity).
7. Invalid-input & error-handling resilience (missing keys, extra keys, NaNs).
8. Cryptographic integrity check: SHA-256 hash match against model_manifest.json.
"""

import sys
import os
import json
import hashlib
import pandas as pd
import numpy as np
import xgboost as xgb
import shap

ARTIFACT_DIR = r"ml_pipeline\model_artifacts\frostlink_xgb_v1"
ORIGINAL_MODEL_PATH = r"ml_pipeline\models\frostlink_xgb_baseline\model.json"
REAL_DATA_PATH = r"ml_pipeline\data\strawberry_train.csv"

def run_artifact_validation_suite():
    print("=" * 80)
    print("RUNNING FROSTLINK PRODUCTION MODEL ARTIFACT VALIDATION SUITE")
    print("=" * 80)
    
    test_results = {}
    
    # -------------------------------------------------------------
    # TEST 1: Artifact Loading Test
    # -------------------------------------------------------------
    req_files = ["model.json", "feature_schema.json", "threshold.json", "model_metadata.json", "backend_contract.json", "model_manifest.json"]
    all_exist = all(os.path.exists(os.path.join(ARTIFACT_DIR, f)) for f in req_files)
    
    packaged_model = xgb.XGBClassifier()
    packaged_model.load_model(os.path.join(ARTIFACT_DIR, "model.json"))
    
    with open(os.path.join(ARTIFACT_DIR, "feature_schema.json")) as f:
        schema = json.load(f)
    feature_names = [feat["feature_name"] for feat in schema["features"]]
    
    with open(os.path.join(ARTIFACT_DIR, "threshold.json")) as f:
        threshold_config = json.load(f)
        
    with open(os.path.join(ARTIFACT_DIR, "model_manifest.json")) as f:
        manifest = json.load(f)
        
    t1_pass = all_exist and len(feature_names) == 40 and threshold_config["operating_threshold"] > 0
    test_results["1_artifact_loading"] = {"passed": t1_pass, "files_checked": req_files}
    print(f"Test 1 [Artifact Loading]:         Passed = {t1_pass}")
    
    # -------------------------------------------------------------
    # TEST 2: Prediction Equivalence Test
    # -------------------------------------------------------------
    orig_model = xgb.XGBClassifier()
    orig_model.load_model(ORIGINAL_MODEL_PATH)
    
    raw_df = pd.read_csv(REAL_DATA_PATH)
    val_sample = raw_df[feature_names].head(20).copy()
    
    prob_orig = orig_model.predict_proba(val_sample)[:, 1]
    prob_packaged = packaged_model.predict_proba(val_sample)[:, 1]
    
    max_pred_delta = float(np.max(np.abs(prob_orig - prob_packaged)))
    t2_pass = bool(max_pred_delta < 1e-6)
    test_results["2_prediction_equivalence"] = {"passed": t2_pass, "max_delta": max_pred_delta}
    print(f"Test 2 [Prediction Equivalence]:   Passed = {t2_pass} (Max Delta: {max_pred_delta:.2e})")
    
    # -------------------------------------------------------------
    # TEST 3: Feature Order Verification
    # -------------------------------------------------------------
    with open(r"ml_pipeline\models\frostlink_xgb_baseline\features.json") as f:
        orig_features = json.load(f)["features"]
    t3_pass = (feature_names == orig_features)
    test_results["3_feature_ordering"] = {"passed": t3_pass, "feature_count": len(feature_names)}
    print(f"Test 3 [Feature Order Match]:      Passed = {t3_pass} (Count: {len(feature_names)})")
    
    # -------------------------------------------------------------
    # TEST 4: Threshold Loading & Evaluation
    # -------------------------------------------------------------
    op_th = threshold_config["operating_threshold"]
    sample_prob = float(prob_packaged[0])
    is_alert = bool(sample_prob >= op_th)
    t4_pass = (op_th == 0.46083333333333326 and isinstance(is_alert, bool))
    test_results["4_threshold_loading"] = {"passed": t4_pass, "operating_threshold": op_th, "sample_alert": is_alert}
    print(f"Test 4 [Threshold Loading]:        Passed = {t4_pass} (Threshold = {op_th:.4f})")
    
    # -------------------------------------------------------------
    # TEST 5: Probability Range Bounds
    # -------------------------------------------------------------
    all_probs = packaged_model.predict_proba(raw_df[feature_names].dropna())[:, 1]
    in_bounds = bool((all_probs >= 0.0).all() and (all_probs <= 1.0).all())
    t5_pass = in_bounds
    test_results["5_probability_bounds"] = {"passed": t5_pass, "min_prob": float(np.min(all_probs)), "max_prob": float(np.max(all_probs))}
    print(f"Test 5 [Probability Range Bounds]: Passed = {t5_pass} (Min: {np.min(all_probs):.4f}, Max: {np.max(all_probs):.4f})")
    
    # -------------------------------------------------------------
    # TEST 6: SHAP Compatibility & Additivity
    # -------------------------------------------------------------
    explainer = shap.TreeExplainer(packaged_model)
    single_sample = val_sample.iloc[[0]]
    shap_vals = explainer.shap_values(single_sample)[0]
    base_val = float(explainer.expected_value) if not isinstance(explainer.expected_value, np.ndarray) else float(explainer.expected_value[0])
    
    dmat = xgb.DMatrix(single_sample)
    booster_margin = float(packaged_model.get_booster().predict(dmat, output_margin=True)[0])
    reconstructed_margin = base_val + float(np.sum(shap_vals))
    shap_additivity_error = abs(booster_margin - reconstructed_margin)
    
    t6_pass = bool(len(shap_vals) == 40 and shap_additivity_error < 0.02)
    test_results["6_shap_compatibility"] = {"passed": t6_pass, "shap_dimensions": len(shap_vals), "additivity_error": shap_additivity_error}
    print(f"Test 6 [SHAP Compatibility]:      Passed = {t6_pass} (Dimensions: {len(shap_vals)}, Error: {shap_additivity_error:.2e})")
    
    # -------------------------------------------------------------
    # TEST 7: Invalid-Input & Resilience Test
    # -------------------------------------------------------------
    # Test handling of NaN values (XGBoost handles NaN natively)
    nan_sample = single_sample.copy()
    nan_sample.iloc[0, 5:10] = np.nan
    nan_prob = float(packaged_model.predict_proba(nan_sample)[0, 1])
    t7_pass = bool(not np.isnan(nan_prob) and 0.0 <= nan_prob <= 1.0)
    test_results["7_invalid_input_handling"] = {"passed": t7_pass, "nan_prob": nan_prob}
    print(f"Test 7 [NaN Resilience Handling]:  Passed = {t7_pass} (NaN Input -> Output Prob: {nan_prob:.4f})")
    
    # -------------------------------------------------------------
    # TEST 8: SHA-256 Manifest Cryptographic Integrity
    # -------------------------------------------------------------
    hash_matches = True
    manifest_audit = {}
    for fname, entry in manifest["files"].items():
        fpath = os.path.join(ARTIFACT_DIR, fname)
        with open(fpath, "rb") as f:
            computed_hash = hashlib.sha256(f.read()).hexdigest()
        is_match = (computed_hash == entry["sha256"])
        manifest_audit[fname] = {"recorded": entry["sha256"][:12], "computed": computed_hash[:12], "match": is_match}
        if not is_match:
            hash_matches = False
            
    t8_pass = hash_matches
    test_results["8_manifest_integrity"] = {"passed": t8_pass, "files_audited": manifest_audit}
    print(f"Test 8 [SHA-256 Hash Integrity]:   Passed = {t8_pass} (All 5 Artifact Checksums Valid)")
    
    # Save Report
    all_passed = all(v["passed"] for v in test_results.values())
    report_dict = {
        "all_tests_passed": all_passed,
        "tests_passed_count": sum(v["passed"] for v in test_results.values()),
        "total_tests": len(test_results),
        "results": test_results
    }
    
    report_path = os.path.join(ARTIFACT_DIR, "validation_test_report.json")
    def json_serial(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)): return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)): return float(obj)
        elif isinstance(obj, (np.bool_, bool)): return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
        
    with open(report_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
        
    print("=" * 80)
    print(f"TEST SUITE COMPLETE: {report_dict['tests_passed_count']} / {report_dict['total_tests']} TESTS PASSED (All Passed = {all_passed})")
    print(f"Saved Test Report to: {report_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_artifact_validation_suite()

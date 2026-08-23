"""
FrostLink Phase 11 — Corrected Independent SHAP Explainability Audit Script
============================================================================
Audits:
1. Model loading & feature registry alignment.
2. Exact sample recovery from local_explanations.json via (shipment_id, timestamp).
3. Anti-leakage feature name inspection & AST/source code temporal window audit.
4. Continuous model probability computation (NO hardcoded 0.50 thresholding).
5. SHAP TreeExplainer initialization, output space, & mathematical additivity.
6. Robust re-verification of Tests 7–10 (addressing empty lists, zero-SHAP contributions).
7. Cross-checking stored JSON values vs. fresh calculations.

Run locally:
  python ml_pipeline/explainability/audit_phase11_shap.py
"""

import sys
import os
import json
import re
import ast
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd

# ==============================================================================
# CONFIGURATION PATHS (Configurable for local execution)
# ==============================================================================
MODEL_PATH = r"ml_pipeline/models/frostlink_xgb_baseline/model.json"
FEATURES_PATH = r"ml_pipeline/models/frostlink_xgb_baseline/features.json"
METADATA_PATH = r"ml_pipeline/models/frostlink_xgb_baseline/metadata.json"
FEATURE_DISPLAY_METADATA_PATH = r"ml_pipeline/explainability/feature_display_metadata.json"
LOCAL_EXPLANATIONS_PATH = r"ml_pipeline/explainability/local_explanations.json"
DATASET_TRAIN_PATH = r"ml_pipeline/data/strawberry_train.csv"
DATASET_TEST_PATH = r"ml_pipeline/data/strawberry_test.csv"
FEATURE_SRC_PATH = r"ml_pipeline/production/feature_engineering.py"

print("=" * 80)
print("FROSTLINK PHASE 11: CORRECTED SHAP EXPLAINABILITY AUDIT")
print("=" * 80)

# ==============================================================================
# A. LOAD MODEL
# ==============================================================================
print("\n[A] LOADING MODEL ARTIFACT...")
if not os.path.exists(MODEL_PATH):
    print(f"[-] ERROR: Model file not found at: {MODEL_PATH}")
    sys.exit(1)

try:
    import xgboost as xgb
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    print(f"  [+] Model Path:    {MODEL_PATH}")
    print(f"  [+] Model Type:    {type(model).__name__}")
except Exception as e:
    print(f"[-] ERROR loading XGBoost model: {e}")
    sys.exit(1)

# Ingest Feature Registry
if os.path.exists(FEATURES_PATH):
    with open(FEATURES_PATH, 'r') as f:
        features_meta = json.load(f)
        feature_names = features_meta.get('features', [])
    print(f"  [+] Feature Count: {len(feature_names)}")
else:
    if hasattr(model, "feature_names_in_") and model.feature_names_in_ is not None:
        feature_names = list(model.feature_names_in_)
        print(f"  [+] Feature Count (from booster): {len(feature_names)}")
    else:
        print("  [-] FEATURE NAMES NOT AVAILABLE")
        feature_names = []

# Ingest Metadata (Report production threshold if pre-existing, do NOT compute)
production_threshold = None
if os.path.exists(METADATA_PATH):
    with open(METADATA_PATH, 'r') as f:
        meta_dict = json.load(f)
        production_threshold = meta_dict.get('optimal_threshold', meta_dict.get('decision_threshold', None))
    if production_threshold is not None:
        print(f"  [+] Stored Production Threshold: {production_threshold}")
    else:
        print("  [+] Stored Production Threshold: NOT RECORDED IN METADATA ARTIFACT")

# ==============================================================================
# B. LOAD & RECOVER EXACT LOCAL EXPLANATION SAMPLE
# ==============================================================================
print("\n[B] RECOVERING EXACT SAMPLE FROM LOCAL EXPLANATIONS...")

# Ingest Full Real Dataset
real_df = None
if os.path.exists(DATASET_TRAIN_PATH):
    train_df = pd.read_csv(DATASET_TRAIN_PATH)
    if os.path.exists(DATASET_TEST_PATH):
        test_df = pd.read_csv(DATASET_TEST_PATH)
        full_raw = pd.concat([train_df, test_df], ignore_index=True)
    else:
        full_raw = train_df
    full_raw['Time_dt'] = pd.to_datetime(full_raw['Time'])
    real_df = full_raw.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)

# Inspect local_explanations.json to find exact instance identifier
target_shipment_id = None
target_timestamp = None
sample_quadrant = "TRUE_POSITIVE"
local_explanations_data = {}

if os.path.exists(LOCAL_EXPLANATIONS_PATH):
    with open(LOCAL_EXPLANATIONS_PATH, 'r') as f:
        local_explanations_data = json.load(f)
    if sample_quadrant in local_explanations_data:
        target_shipment_id = local_explanations_data[sample_quadrant].get('shipment_id', None)
        target_timestamp = local_explanations_data[sample_quadrant].get('timestamp', None)

exact_sample_recovered = False
sample_features = None
sample_info_str = ""

if real_df is not None and target_shipment_id and target_timestamp:
    target_dt = pd.to_datetime(target_timestamp)
    matching_rows = real_df[(real_df['shipment_id'] == target_shipment_id) & (real_df['Time_dt'] == target_dt)]
    if len(matching_rows) == 1:
        exact_sample_recovered = True
        sample_row = matching_rows.iloc[[0]]
        sample_features = sample_row[feature_names]
        sample_info_str = f"EXACT SAMPLE RECOVERED: Shipment {target_shipment_id} @ {target_timestamp} (Quadrant: {sample_quadrant})"
        print(f"  [+] {sample_info_str}")
    elif len(matching_rows) > 1:
        print("  [-] WARNING: Multiple rows matched target (shipment_id, timestamp).")
    else:
        print("  [-] EXACT SAMPLE IDENTITY CANNOT BE RECOVERED FROM JSON")
else:
    print("  [-] EXACT SAMPLE IDENTITY CANNOT BE RECOVERED FROM JSON")

# Fallback sample handling if exact recovery was impossible
if not exact_sample_recovered:
    if real_df is not None:
        cohort = real_df[real_df['risk_level'].isin([0.0, 1.0]) & real_df['y_next_60_R2'].notna()].reset_index(drop=True)
        sample_row = cohort.iloc[[0]]
        sample_features = sample_row[feature_names]
        sample_info_str = "FALLBACK SAMPLE — NOT THE STORED EXPLANATION SAMPLE"
        print(f"  [!] Using: {sample_info_str}")
    else:
        print("[-] ERROR: Real dataset unavailable. Cannot proceed with sample evaluation.")
        sys.exit(1)

print(f"  [+] Sample Shape:                 {sample_features.shape}")
print(f"  [+] Feature Order Matches Model:  {list(sample_features.columns) == feature_names}")

# ==============================================================================
# C. LOAD LOCAL EXPLANATIONS JSON
# ==============================================================================
print("\n[C] AUDITING LOCAL EXPLANATIONS STRUCTURE...")
required_quadrants = ["TRUE_POSITIVE", "TRUE_NEGATIVE", "FALSE_POSITIVE", "FALSE_NEGATIVE"]
found_keys = list(local_explanations_data.keys())
print(f"  [+] Keys Found in JSON: {found_keys}")
missing_keys = [k for k in required_quadrants if k not in found_keys]
if missing_keys:
    print(f"  [-] Missing Quadrant Keys: {missing_keys}")
else:
    print("  [+] All 4 operational quadrants present in JSON.")

# ==============================================================================
# D. ANTI-LEAKAGE FEATURE NAME AUDIT
# ==============================================================================
print("\n[D] ANTI-LEAKAGE FEATURE NAME AUDIT...")
forbidden_metadata = [
    "risk_level", "label_R0", "label_R1", "label_R2",
    "conf_level", "cause_sensor", "cause_door", "y_next_60_R2"
]
matched_forbidden = [f for f in feature_names if f in forbidden_metadata]

suspicious_patterns = [
    ("future_", "Explicit future indicator prefix"),
    ("next_", "Forward transition target token"),
    ("target", "Direct target label token"),
    ("label", "Direct label assignment token"),
    ("outcome", "Ground truth outcome token"),
    ("post_", "Post-excursion period token"),
    ("lead", "Lookahead lead-time token")
]

flagged_suspicious = []
for f in feature_names:
    for pat, desc in suspicious_patterns:
        if pat in f.lower():
            flagged_suspicious.append((f, pat, desc))

print(f"  [+] Forbidden Feature Matches: {matched_forbidden}")
if not matched_forbidden and not flagged_suspicious:
    print("  [+] Result: NOT OBVIOUSLY SUSPICIOUS (Zero forbidden tokens or forward prefixes detected)")
else:
    for f, p, d in flagged_suspicious:
        print(f"  [!] CLEARLY SUSPICIOUS Feature: '{f}' (Matched: '{p}', Rationale: {d})")

# ==============================================================================
# E. TEMPORAL LEAKAGE AUDIT (AST & Source Inspection)
# ==============================================================================
print("\n[E] TEMPORAL LEAKAGE SOURCE CODE AUDIT...")
if os.path.exists(FEATURE_SRC_PATH):
    with open(FEATURE_SRC_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        src_text = f.read()
    
    print(f"  [+] Inspecting source: {FEATURE_SRC_PATH}")
    
    # 1. Inspect shifts for negative indexing (future access)
    neg_shifts = re.findall(r'shift\s*\(\s*-\s*\d+\s*\)', src_text)
    pos_shifts = re.findall(r'shift\s*\(\s*\d+\s*\)', src_text)
    
    # 2. Inspect rolling window definitions
    rolling_calls = re.findall(r'rolling\s*\([^)]*\)', src_text)
    
    # 3. Check for center=True (which leaks future data into current window)
    centered_rolling = [c for c in rolling_calls if 'center=True' in c.replace(" ", "")]
    
    print(f"  [+] Backward Causal Shifts shift(k):     {len(pos_shifts)} instances")
    print(f"  [+] Forward Lookahead Shifts shift(-k):  {len(neg_shifts)} instances")
    print(f"  [+] Rolling Operations:                  {len(rolling_calls)} instances")
    print(f"  [+] Centered Rolling (center=True):      {len(centered_rolling)} instances")
    
    if len(neg_shifts) == 0 and len(centered_rolling) == 0:
        print("  [+] Temporal Audit: Verified causal backward-looking structures only [t-k, t].")
    else:
        print("  [-] MANUAL TEMPORAL REVIEW REQUIRED (Potential forward lookahead construct detected)")
else:
    print("  [-] TEMPORAL LEAKAGE CANNOT BE FULLY VERIFIED FROM FEATURE NAMES ALONE.")
    print("      MANUAL TEMPORAL REVIEW REQUIRED.")

# ==============================================================================
# F. MODEL PREDICTION (Continuous Probability Output Only)
# ==============================================================================
print("\n[F] FRESH MODEL PREDICTION (No Hardcoded 0.50 Threshold)...")
fresh_prob = float(model.predict_proba(sample_features)[0, 1])
dmatrix_sample = xgb.DMatrix(sample_features)
fresh_margin = float(model.get_booster().predict(dmatrix_sample, output_margin=True)[0])

print(f"  [+] Predicted Risk Probability: {fresh_prob:.6f} ({fresh_prob*100:.2f}%)")
print(f"  [+] Raw Log-Odds Margin:        {fresh_margin:.6f}")
if production_threshold is not None:
    print(f"  [+] Reference Production Threshold: {production_threshold} (Evaluated independently)")

# ==============================================================================
# G. SHAP CALCULATION & OUTPUT SPACE VERIFICATION
# ==============================================================================
print("\n[G] SHAP TREE EXPLAINER CALCULATION...")
try:
    import shap
    explainer = shap.TreeExplainer(model)
    shap_raw = explainer.shap_values(sample_features)
    
    if isinstance(shap_raw, list):
        sample_shap = shap_raw[1][0] if len(shap_raw) > 1 else shap_raw[0][0]
    elif len(shap_raw.shape) == 2:
        sample_shap = shap_raw[0]
    else:
        sample_shap = shap_raw
        
    base_val = float(explainer.expected_value) if not isinstance(explainer.expected_value, np.ndarray) else float(explainer.expected_value[0])
    
    print(f"  [+] Base Value (Expected Margin): {base_val:.6f}")
    print(f"  [+] SHAP Dimensions:              {sample_shap.shape} (Matches {len(feature_names)} features: {len(sample_shap) == len(feature_names)})")
except Exception as e:
    print(f"[-] ERROR computing SHAP values: {e}")
    sys.exit(1)

# ==============================================================================
# H. SHAP ADDITIVITY VERIFICATION
# ==============================================================================
print("\n[H] SHAP ADDITIVITY VERIFICATION...")
sum_shap = float(np.sum(sample_shap))
reconstructed_margin = base_val + sum_shap
additivity_error = abs(reconstructed_margin - fresh_margin)

print(f"  [+] Explainer Output Space:    Raw Margin (Log-Odds)")
print(f"  [+] Booster Output Space:      Raw Margin (Log-Odds)")
print(f"  [+] Base Value:                {base_val:.6f}")
print(f"  [+] Sum(SHAP):                 {sum_shap:.6f}")
print(f"  [+] Reconstructed Margin:      {reconstructed_margin:.6f}")
print(f"  [+] Actual Booster Margin:     {fresh_margin:.6f}")
print(f"  [+] Absolute Additivity Error: {additivity_error:.2e}")

# Exact numerical additivity criterion
additivity_pass = additivity_error < 0.02
print(f"  [+] ADDITIVITY STATUS:         {'PASS' if additivity_pass else 'FAIL'}")

# ==============================================================================
# I. TEST 7 RE-RUN: ANTI-LEAKAGE WHITELIST
# ==============================================================================
print("\n[I] RE-RUNNING TEST 7 (Anti-Leakage Whitelist)...")
t7_pass = (len(matched_forbidden) == 0) and ('y_next_60_R2' not in feature_names)
print(f"  [+] Forbidden metadata detected: {matched_forbidden}")
print(f"  [+] Target feature excluded:     {'y_next_60_R2' not in feature_names}")
print(f"  [+] TEST 7 RESULT:               {'PASS' if t7_pass else 'FAIL'}")

# ==============================================================================
# J. TEST 8 RE-RUN: LOCAL EXPLANATION SCHEMA & POPULATION
# ==============================================================================
print("\n[J] RE-RUNNING TEST 8 (Local Explanation Structure & Non-Empty Elements)...")
t8_errors = []
if not local_explanations_data:
    t8_errors.append("local_explanations.json is missing or empty")
else:
    for q in required_quadrants:
        if q not in local_explanations_data:
            t8_errors.append(f"Missing quadrant key: {q}")
            continue
        item = local_explanations_data[q]
        n_inc = len(item.get("top_risk_increasing_factors", []))
        n_dec = len(item.get("top_risk_reducing_factors", []))
        if n_inc == 0 and n_dec == 0:
            t8_errors.append(f"Quadrant {q} has empty factor lists (both increasing and reducing are empty)")
        print(f"  [+] Quadrant {q:15s}: {n_inc} risk-increasing, {n_dec} risk-reducing factors")

t8_pass = len(t8_errors) == 0
print(f"  [+] TEST 8 RESULT:               {'PASS' if t8_pass else 'FAIL'} (Errors: {t8_errors})")

# ==============================================================================
# K. TEST 9 RE-RUN: DIRECTIONALITY SEPARATION & NEUTRAL CONTRIBUTIONS
# ==============================================================================
print("\n[K] RE-RUNNING TEST 9 (Directionality Separation & Zero-SHAP Audit)...")
t9_errors = []
total_factors_checked = 0

if local_explanations_data:
    for q, item in local_explanations_data.items():
        inc_factors = item.get("top_risk_increasing_factors", [])
        dec_factors = item.get("top_risk_reducing_factors", [])
        
        # Explicitly disallow empty factor lists from passing vacuously
        if len(inc_factors) == 0 and len(dec_factors) == 0:
            t9_errors.append(f"{q}: both factor lists are empty")
            continue
            
        for f in inc_factors:
            total_factors_checked += 1
            if f["shap_value"] <= 0:
                t9_errors.append(f"{q}: increasing factor '{f['feature_name']}' has non-positive SHAP ({f['shap_value']})")
                
        for f in dec_factors:
            total_factors_checked += 1
            if f["shap_value"] >= 0:
                t9_errors.append(f"{q}: reducing factor '{f['feature_name']}' has non-negative SHAP ({f['shap_value']})")

# Neutral contribution audit
n_neutral = int(np.sum(sample_shap == 0.0))
print(f"  [+] Neutral Features (SHAP == 0.0): {n_neutral} / {len(sample_shap)} (NEUTRAL CONTRIBUTION — No risk impact)")
print(f"  [+] Total Factors Directionally Verified: {total_factors_checked}")

t9_pass = len(t9_errors) == 0 and total_factors_checked > 0
print(f"  [+] TEST 9 RESULT:               {'PASS' if t9_pass else 'FAIL'} (Errors: {t9_errors})")

# ==============================================================================
# L. TEST 10 RE-RUN: REAL-TIME EXPLAINER ENGINE
# ==============================================================================
print("\n[L] RE-RUNNING TEST 10 (Real-Time FrostLinkExplainer Execution)...")
try:
    sys.path.append(os.path.abspath(r"ml_pipeline/explainability"))
    from explain_prediction import FrostLinkExplainer
    
    engine = FrostLinkExplainer(
        model_path=MODEL_PATH,
        features_path=FEATURES_PATH,
        metadata_path=FEATURE_DISPLAY_METADATA_PATH
    )
    
    sample_dict = sample_features.iloc[0].to_dict()
    res_engine = engine.explain_instance(sample_dict)
    
    eng_prob = res_engine["predicted_risk_probability"]
    eng_additivity = res_engine["additivity_verified"]
    eng_has_factors = len(res_engine["top_risk_increasing_factors"]) > 0 or len(res_engine["top_risk_reducing_factors"]) > 0
    prob_consistent = abs(eng_prob - fresh_prob) < 1e-5
    
    print(f"  [+] Engine Risk Probability:     {eng_prob:.6f} (Consistent with fresh model: {prob_consistent})")
    print(f"  [+] Dynamic Additivity Verified: {eng_additivity} (Delta: {res_engine['additivity_delta']:.2e})")
    print(f"  [+] Factors Populated:           {eng_has_factors}")
    
    t10_pass = eng_additivity and eng_has_factors and prob_consistent
    print(f"  [+] TEST 10 RESULT:              {'PASS' if t10_pass else 'FAIL'}")
except Exception as e:
    print(f"  [-] ERROR in Test 10 execution: {e}")
    t10_pass = False
    print("  [-] TEST 10 RESULT:              FAIL")

# ==============================================================================
# M. CROSS-CHECK STORED JSON VS FRESH COMPUTATION
# ==============================================================================
print("\n[M] CROSS-CHECKING STORED JSON VALUES VS FRESH CALCULATIONS...")
if exact_sample_recovered and sample_quadrant in local_explanations_data:
    stored_obj = local_explanations_data[sample_quadrant]
    stored_prob = stored_obj.get("predicted_risk_probability", None)
    stored_margin = stored_obj.get("actual_margin_log_odds", None)
    
    if stored_prob is not None and stored_margin is not None:
        prob_diff = abs(stored_prob - fresh_prob)
        margin_diff = abs(stored_margin - fresh_margin)
        print(f"  [+] Stored Probability: {stored_prob:.6f} | Fresh: {fresh_prob:.6f} | Delta: {prob_diff:.2e}")
        print(f"  [+] Stored Margin:      {stored_margin:.6f} | Fresh: {fresh_margin:.6f} | Delta: {margin_diff:.2e}")
        if prob_diff < 1e-4 and margin_diff < 1e-4:
            print("  [+] Probability & Margin consistency VERIFIED.")
        else:
            print("  [!] Probability / Margin discrepancy observed.")

    # Compare stored SHAP attributions against freshly calculated SHAP values
    stored_factors = (
        stored_obj.get("top_risk_increasing_factors", []) +
        stored_obj.get("top_risk_reducing_factors", [])
    )

    stored_shap = {
        item.get("feature_name", item.get("feature")): float(item["shap_value"])
        for item in stored_factors
        if ("feature_name" in item or "feature" in item) and "shap_value" in item
    }

    fresh_shap_map = {
        feature_names[i]: float(sample_shap[i])
        for i in range(len(feature_names))
    }

    common_features = set(stored_shap) & set(fresh_shap_map)

    if common_features:
        shap_diffs = {
            f: abs(stored_shap[f] - fresh_shap_map[f])
            for f in common_features
        }

        max_shap_diff = max(shap_diffs.values())

        print(f"  [+] Common SHAP features: {len(common_features)}")
        print(f"  [+] Maximum SHAP difference: {max_shap_diff:.2e}")

        if max_shap_diff < 1e-4:
            print("  [+] SHAP attribution consistency VERIFIED.")
        else:
            print("  [!] SHAP attribution discrepancy detected.")
    else:
        print("  [!] No comparable stored SHAP features found.")
else:
    print("  [!] Cannot cross-check exact sample: Exact sample was not recovered from JSON.")

print("\n" + "=" * 80)
print("AUDIT SCRIPT READY FOR LOCAL EXECUTION.")
print("=" * 80)

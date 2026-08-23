"""
FrostLink ML Pipeline -- SHAP Explainability Engine (Phase 11)
=============================================================
Calculates:
1. Global TreeExplainer SHAP values on real-world Strawberry telemetry.
2. Global feature importance rankings (mean absolute SHAP).
3. Summary bar and beeswarm diagnostic plots.
4. Local instance explanations for TP, TN, FP, and FN observations.
5. Strict mathematical additivity verification.
"""

import sys
import os
import json
import warnings
warnings.filterwarnings('ignore')

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import xgboost as xgb
import shap

# 1. Paths & Directory Setup
EXPLAIN_DIR = r"ml_pipeline\explainability"
MODEL_DIR = r"ml_pipeline\models\frostlink_xgb_baseline"
os.makedirs(EXPLAIN_DIR, exist_ok=True)

# 2. Ingest Model & Feature Metadata
print("=" * 80)
print("STEP 1: INGESTING SERIALIZED BASELINE MODEL & REAL TELEMETRY")
print("=" * 80)

model_path = os.path.join(MODEL_DIR, "model.json")
features_path = os.path.join(MODEL_DIR, "features.json")
metadata_path = os.path.join(MODEL_DIR, "metadata.json")

with open(features_path, 'r') as f:
    FEATURE_NAMES = json.load(f)['features']

with open(metadata_path, 'r') as f:
    META = json.load(f)

print(f"Loaded Feature Registry: {len(FEATURE_NAMES)} features.")
print(f"Model Baseline: {META.get('model_name', 'frostlink_xgb_baseline')}")

# Load XGBoost Model
model = xgb.XGBClassifier()
model.load_model(model_path)

# Ingest Real Strawberry Telemetry
train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
raw_real = pd.concat([train_df, test_df], ignore_index=True)
raw_real['Time_dt'] = pd.to_datetime(raw_real['Time'])

real_df = raw_real.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)
TARGET_COL = 'y_next_60_R2'

# Filter strictly to the audited early-warning evaluation population (risk_level in [0, 1])
cohort = real_df[real_df['risk_level'].isin([0.0, 1.0]) & real_df[TARGET_COL].notna()].copy().reset_index(drop=True)
X_cohort = cohort[FEATURE_NAMES]
y_cohort = cohort[TARGET_COL].values

# Verify Target Absence & Feature Integrity
assert TARGET_COL not in FEATURE_NAMES, "CRITICAL ERROR: Target column found in feature matrix!"
assert len(FEATURE_NAMES) == 40, f"Expected 40 features, found {len(FEATURE_NAMES)}"
print(f"Cohort Shape: {X_cohort.shape} ({len(X_cohort)} observations, {len(FEATURE_NAMES)} features)")
print(f"Positive Transition Labels (y=1): {(y_cohort == 1).sum()} / {len(y_cohort)} (Base rate: {(y_cohort == 1).mean()*100:.2f}%)")

# Predict Model Probabilities & Raw Margin Output
probs = model.predict_proba(X_cohort)[:, 1]
cohort['pred_prob'] = probs
cohort['pred_binary'] = (probs >= 0.50).astype(int)

# ============================================================
# STEP 2: SHAP TREE EXPLAINER INITIALIZATION
# ============================================================
print("\n" + "=" * 80)
print("STEP 2: INITIALIZING SHAP TREE EXPLAINER ON REAL COHORT")
print("=" * 80)

# Initialize TreeExplainer (outputs margin / log-odds values for strict linear additivity)
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_cohort)

# Base value (expected margin)
base_value = explainer.expected_value
if isinstance(base_value, np.ndarray):
    base_value = float(base_value[0])
else:
    base_value = float(base_value)

print(f"SHAP TreeExplainer Initialized. Base Value (Expected Margin Log-Odds): {base_value:.4f}")
print(f"SHAP Values Matrix Shape: {shap_values.shape}")

# ============================================================
# STEP 3: GLOBAL FEATURE IMPORTANCE (Mean Absolute SHAP)
# ============================================================
print("\n" + "=" * 80)
print("STEP 3: COMPUTING GLOBAL MEAN ABSOLUTE SHAP IMPORTANCE")
print("=" * 80)

mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
importance_df = pd.DataFrame({
    'rank': np.arange(1, len(FEATURE_NAMES) + 1),
    'feature': FEATURE_NAMES,
    'mean_abs_shap': mean_abs_shap,
    'xgb_gain_importance': model.feature_importances_
}).sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)
importance_df['rank'] = np.arange(1, len(FEATURE_NAMES) + 1)

csv_imp_path = os.path.join(EXPLAIN_DIR, "global_feature_importance.csv")
importance_df.to_csv(csv_imp_path, index=False)
print(f"Saved Global Feature Importance to: {csv_imp_path}")

print("\n--- TOP 15 FEATURES BY GLOBAL SHAP IMPORTANCE ---")
print("Rank | Feature Name                 | Mean |SHAP| | XGBoost Gain")
print("---------------------------------------------------------------")
for _, r in importance_df.head(15).iterrows():
    print(f" {r['rank']:2d}  | {r['feature']:28s} |   {r['mean_abs_shap']:.5f}  |   {r['xgb_gain_importance']:.5f}")

# ============================================================
# STEP 4: GENERATE SHAP PLOTS
# ============================================================
print("\n" + "=" * 80)
print("STEP 4: GENERATING SHAP SUMMARY & BEESWARM DIAGNOSTIC PLOTS")
print("=" * 80)

# 1. Summary Bar Plot
plt.figure(figsize=(10, 10))
shap.summary_plot(shap_values, X_cohort, plot_type="bar", show=False, max_display=20)
plt.title("FrostLink Real-Data XGBoost: Top 20 Global SHAP Feature Importances", fontsize=12, pad=15)
plt.xlabel("Mean |SHAP Value| (Average Impact on Model Risk Output)", fontsize=10)
plt.tight_layout()
bar_plot_path = os.path.join(EXPLAIN_DIR, "shap_summary_bar.png")
plt.savefig(bar_plot_path, dpi=150)
plt.close()
print(f"Saved SHAP Summary Bar Plot: {bar_plot_path}")

# 2. Beeswarm Plot
plt.figure(figsize=(11, 10))
shap.summary_plot(shap_values, X_cohort, show=False, max_display=20)
plt.title("FrostLink Real-Data XGBoost: SHAP Beeswarm Directional Distribution", fontsize=12, pad=15)
plt.xlabel("SHAP Value (Impact on Log-Odds of Excursion)", fontsize=10)
plt.tight_layout()
beeswarm_plot_path = os.path.join(EXPLAIN_DIR, "shap_beeswarm.png")
plt.savefig(beeswarm_plot_path, dpi=150)
plt.close()
print(f"Saved SHAP Beeswarm Plot:    {beeswarm_plot_path}")

# ============================================================
# STEP 5: LOCAL INSTANCE EXPLANATIONS & ADDITIVITY VERIFICATION
# ============================================================
print("\n" + "=" * 80)
print("STEP 5: LOCAL EXPLANATIONS & MATHEMATICAL ADDITIVITY VERIFICATION")
print("=" * 80)

# Load Display Metadata
with open(os.path.join(EXPLAIN_DIR, "feature_display_metadata.json"), 'r') as f:
    DISPLAY_META = json.load(f)['features']

# Identify representative instances: TP, TN, FP, FN
cohort['true_label'] = y_cohort
tp_candidates = cohort[(cohort['true_label'] == 1) & (cohort['pred_binary'] == 1)]
tn_candidates = cohort[(cohort['true_label'] == 0) & (cohort['pred_binary'] == 0)]
fp_candidates = cohort[(cohort['true_label'] == 0) & (cohort['pred_binary'] == 1)]
fn_candidates = cohort[(cohort['true_label'] == 1) & (cohort['pred_binary'] == 0)]

print(f"Cohort Instances Available -> TP: {len(tp_candidates)}, TN: {len(tn_candidates)}, FP: {len(fp_candidates)}, FN: {len(fn_candidates)}")

# Select high-confidence representative sample from each quadrant
idx_tp = int(tp_candidates.sort_values('pred_prob', ascending=False).index[0])
idx_tn = int(tn_candidates.sort_values('pred_prob', ascending=True).index[0])
idx_fp = int(fp_candidates.sort_values('pred_prob', ascending=False).index[0])
idx_fn = int(fn_candidates.sort_values('pred_prob', ascending=True).index[0])

selected_instances = {
    'TRUE_POSITIVE': {'idx': idx_tp, 'desc': 'True Positive: True impending excursion correctly alerted.'},
    'TRUE_NEGATIVE': {'idx': idx_tn, 'desc': 'True Negative: Safe baseline correctly classified without alarm.'},
    'FALSE_POSITIVE': {'idx': idx_fp, 'desc': 'False Positive: Alert fired on non-excursion transition.'},
    'FALSE_NEGATIVE': {'idx': idx_fn, 'desc': 'False Negative: Impending excursion missed by model.'}
}

local_explanations_output = {}

# Compute margins for additivity check
dmat = xgb.DMatrix(X_cohort)
margins = model.get_booster().predict(dmat, output_margin=True)

for case_type, case_info in selected_instances.items():
    idx = case_info['idx']
    row_features = X_cohort.iloc[idx]
    row_shap = shap_values[idx]
    
    actual_margin = float(margins[idx])
    reconstructed_margin = float(base_value + np.sum(row_shap))
    additivity_error = abs(actual_margin - reconstructed_margin)
    assert additivity_error < 1e-4, f"Additivity failure for {case_type}: error = {additivity_error}"
    
    prob = float(probs[idx])
    y_true = int(y_cohort[idx])
    y_pred = int(cohort.loc[idx, 'pred_binary'])
    shipment_id = str(cohort.loc[idx, 'shipment_id'])
    timestamp_str = str(cohort.loc[idx, 'Time_dt'])
    
    # Sort top risk-increasing and risk-reducing features
    feature_contributions = []
    for f_name, f_val, s_val in zip(FEATURE_NAMES, row_features, row_shap):
        f_meta = DISPLAY_META.get(f_name, {})
        feature_contributions.append({
            'feature_name': f_name,
            'display_name': f_meta.get('display_name', f_name),
            'unit': f_meta.get('unit', ''),
            'observed_value': float(f_val),
            'shap_value': float(s_val),
            'abs_shap': abs(float(s_val)),
            'feature_group': f_meta.get('feature_group', '')
        })
        
    contrib_df = pd.DataFrame(feature_contributions)
    risk_increasing = contrib_df[contrib_df['shap_value'] > 0].sort_values('shap_value', ascending=False).head(5).to_dict('records')
    risk_reducing = contrib_df[contrib_df['shap_value'] < 0].sort_values('shap_value', ascending=True).head(5).to_dict('records')
    
    local_explanations_output[case_type] = {
        'case_description': case_info['desc'],
        'shipment_id': shipment_id,
        'timestamp': timestamp_str,
        'true_label': y_true,
        'predicted_binary': y_pred,
        'predicted_risk_probability': prob,
        'base_value_log_odds': base_value,
        'actual_margin_log_odds': actual_margin,
        'reconstructed_margin_log_odds': reconstructed_margin,
        'additivity_error': additivity_error,
        'top_risk_increasing_factors': risk_increasing,
        'top_risk_reducing_factors': risk_reducing
    }
    
    print(f"\n================================================================================")
    print(f"CASE: {case_type} | Shipment: {shipment_id} @ {timestamp_str}")
    print(f"True Label: {y_true} | Predicted Probability: {prob:.4f} (Margin: {actual_margin:.4f}) | Additivity Error: {additivity_error:.2e}")
    print(f"================================================================================")
    print("Top Factors Increasing Predicted Excursion Risk:")
    for item in risk_increasing[:3]:
        print(f"  (+) {item['display_name']} ({item['feature_name']}) = {item['observed_value']:.3f} {item['unit']} -> SHAP: +{item['shap_value']:.4f}")
    print("Top Factors Reducing Predicted Excursion Risk:")
    for item in risk_reducing[:3]:
        print(f"  (-) {item['display_name']} ({item['feature_name']}) = {item['observed_value']:.3f} {item['unit']} -> SHAP: {item['shap_value']:.4f}")

out_local_json = os.path.join(EXPLAIN_DIR, "local_explanations.json")
with open(out_local_json, 'w') as f:
    json.dump(local_explanations_output, f, indent=2)
print(f"\nSaved Local Explanations JSON: {out_local_json}")

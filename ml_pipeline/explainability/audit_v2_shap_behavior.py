"""
FrostLink XGBoost v2 SHAP & Behavioral Audit Pipeline -- Phase 16D
===================================================================
Executes exhaustive global & local explainability and scenario behavioral audits
on the frozen XGBoost v2 model and untouched test set.
"""

import sys
import os
import json
import time
import numpy as np
import pandas as pd
import xgboost as xgb
import shap

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "feature_engineering")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service")))

from feature_engineer import FrostLinkFeatureEngineer

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "synthetic", "data"))
V2_ARTIFACT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model_artifacts", "frostlink_xgb_v2"))
EXPLAIN_DIR = os.path.abspath(os.path.dirname(__file__))

def run_v2_shap_behavior_audit():
    print("=" * 80)
    print("FROSTLINK PHASE 16D: XGBOOST V2 SHAP & BEHAVIORAL AUDIT")
    print("=" * 80)
    
    # 1. Load Model & Threshold
    fe = FrostLinkFeatureEngineer()
    feature_names = fe.feature_names
    
    model = xgb.XGBClassifier()
    model.load_model(os.path.join(V2_ARTIFACT_DIR, "model.json"))
    
    with open(os.path.join(V2_ARTIFACT_DIR, "threshold.json")) as f:
        thresh_data = json.load(f)
    threshold = float(thresh_data["f1_optimal_threshold"])
    print(f"[+] Loaded frozen XGBoost v2 model. Validation Decision Threshold = {threshold:.4f}")
    
    # 2. Load & Featurize Test Set
    test_raw = pd.read_csv(os.path.join(DATA_DIR, "synthetic_test.csv"))
    print(f"[+] Extracting features on untouched Test Set ({len(test_raw['shipment_id'].unique())} shipments, {len(test_raw):,} rows)...")
    
    shipment_dfs = []
    for s_id, s_df in test_raw.groupby("shipment_id"):
        s_df = s_df.sort_values("step_index").reset_index(drop=True)
        feats_df = fe.extract_features_dataframe(s_df)
        meta_cols = ["shipment_id", "Time", "step_index", "scenario_name", "risk_level", "y_next_60_R2", "eta_to_R2_60", "ambient_temp", "door_open", "cooling_state", "true_core_temp"]
        combined = pd.concat([s_df[meta_cols], feats_df], axis=1)
        shipment_dfs.append(combined)
        
    test_full = pd.concat(shipment_dfs, ignore_index=True)
    test_cohort = test_full[test_full["risk_level"].isin([0.0, 1.0]) & test_full["y_next_60_R2"].notna()].reset_index(drop=True)
    
    X_test = test_cohort[feature_names].values.astype(np.float64)
    y_test = test_cohort["y_next_60_R2"].values.astype(int)
    
    # 3. Model Inference & Probabilities
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= threshold).astype(int)
    test_cohort["prob_v2"] = test_probs
    test_cohort["pred_v2"] = test_preds
    
    # -------------------------------------------------------------
    # 1. GLOBAL SHAP IMPORTANCE
    # -------------------------------------------------------------
    print("\n[1] COMPUTING GLOBAL SHAP IMPORTANCE (Untouched Test Cohort, 9,948 Rows)...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)
    base_value = float(explainer.expected_value) if not isinstance(explainer.expected_value, np.ndarray) else float(explainer.expected_value[0])
    
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    total_shap_mass = np.sum(mean_abs_shap)
    
    sorted_indices = np.argsort(-mean_abs_shap)
    global_importance = []
    
    print("-" * 75)
    print(f"{'Rank':<5} | {'Feature Name':<30} | {'Mean |SHAP|':<15} | {'Importance Share'}")
    print("-" * 75)
    for rank, idx in enumerate(sorted_indices, 1):
        feat_name = feature_names[idx]
        val = float(mean_abs_shap[idx])
        share = (val / total_shap_mass * 100.0) if total_shap_mass > 0 else 0.0
        global_importance.append({
            "rank": rank,
            "feature_name": feat_name,
            "mean_abs_shap": val,
            "importance_share_pct": share
        })
        if rank <= 15 or rank >= 38:
            print(f"{rank:<5} | {feat_name:<30} | {val:<15.6f} | {share:>6.2f}%")
        elif rank == 16:
            print(f"{'...':<5} | {'[Features 16 to 37 truncated for console]':<30} | {'...':<15} | {'...'}")
    print("-" * 75)
    
    def json_serial(obj):
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        raise TypeError(f"Type {type(obj)} not serializable")

    # Save Global Importance JSON
    glob_out_path = os.path.join(V2_ARTIFACT_DIR, "global_shap_importance.json")
    with open(glob_out_path, "w") as f:
        json.dump({"base_value_margin": base_value, "features_ranked": global_importance}, f, indent=2, default=json_serial)
    print(f"[+] Saved Global SHAP Importance to: {glob_out_path}")
    
    # -------------------------------------------------------------
    # 2 & 3. LOCAL SHAP EXPLANATIONS & ADDITIVITY PROOF
    # -------------------------------------------------------------
    print("\n[2 & 3] LOCAL SHAP EXPLANATIONS & MATHEMATICAL ADDITIVITY (TP, TN, FP, FN):")
    
    tp_idx = np.where((y_test == 1) & (test_preds == 1))[0][0]
    tn_idx = np.where((y_test == 0) & (test_preds == 0))[0][0]
    fp_idx = np.where((y_test == 0) & (test_preds == 1))[0][0]
    fn_idx = np.where((y_test == 1) & (test_preds == 0))[0][0]
    
    case_indices = {"A. True Positive (TP)": tp_idx, "B. True Negative (TN)": tn_idx, "C. False Positive (FP)": fp_idx, "D. False Negative (FN)": fn_idx}
    local_reports = {}
    
    for case_label, c_idx in case_indices.items():
        row_meta = test_cohort.iloc[c_idx]
        sample_x = X_test[c_idx:c_idx+1]
        sample_shap = shap_values[c_idx]
        sample_prob = float(test_probs[c_idx])
        sample_pred = int(test_preds[c_idx])
        sample_true = int(y_test[c_idx])
        
        # Additivity
        dmat = xgb.DMatrix(sample_x, feature_names=feature_names)
        booster_margin = float(model.get_booster().predict(dmat, output_margin=True)[0])
        reconstructed_margin = base_value + float(np.sum(sample_shap))
        additivity_delta = abs(booster_margin - reconstructed_margin)
        reconstructed_prob = 1.0 / (1.0 + np.exp(-reconstructed_margin))
        prob_delta = abs(reconstructed_prob - sample_prob)
        
        # Top Factors
        increasing_idx = np.where(sample_shap > 0)[0]
        increasing_sorted = increasing_idx[np.argsort(-sample_shap[increasing_idx])]
        top_inc = [{"feature": feature_names[i], "value": float(sample_x[0, i]), "shap": float(sample_shap[i])} for i in increasing_sorted[:3]]
        
        decreasing_idx = np.where(sample_shap < 0)[0]
        decreasing_sorted = decreasing_idx[np.argsort(sample_shap[decreasing_idx])]
        top_dec = [{"feature": feature_names[i], "value": float(sample_x[0, i]), "shap": float(sample_shap[i])} for i in decreasing_sorted[:3]]
        
        print(f"\n--- {case_label} [Shipment: {row_meta['shipment_id']} | Scenario: {row_meta['scenario_name']} | Time: {row_meta['Time']}] ---")
        print(f"    Label: {sample_true} | Pred: {sample_pred} | Risk Prob: {sample_prob:.4f} (Threshold: {threshold:.4f})")
        print(f"    Additivity Delta: {additivity_delta:.2e} | Prob Consistency Delta: {prob_delta:.2e}")
        print(f"    Top Risk-Increasing Factors:")
        for f in top_inc:
            print(f"      * {f['feature']:<25} (Observed: {f['value']:>7.3f}) -> SHAP = {f['shap']:>+7.4f}")
        print(f"    Top Risk-Reducing Factors:")
        for f in top_dec:
            print(f"      * {f['feature']:<25} (Observed: {f['value']:>7.3f}) -> SHAP = {f['shap']:>+7.4f}")
            
        local_reports[case_label] = {
            "shipment_id": row_meta["shipment_id"],
            "scenario": row_meta["scenario_name"],
            "time": row_meta["Time"],
            "true_label": sample_true,
            "prediction": sample_pred,
            "probability": sample_prob,
            "threshold": threshold,
            "additivity_delta": additivity_delta,
            "prob_delta": prob_delta,
            "top_increasing": top_inc,
            "top_reducing": top_dec
        }

    # -------------------------------------------------------------
    # 4 & 5. BEHAVIORAL SCENARIO AUDIT
    # -------------------------------------------------------------
    print("\n[4 & 5] BEHAVIORAL SCENARIO AUDIT (All 13 Scenarios on Test Cohort):")
    print("-" * 115)
    print(f"{'Scenario Name':<35} | {'Ships':<5} | {'Pos Win':<8} | {'Pred Win':<8} | {'Mean Prob':<10} | {'Max Prob':<10} | {'FP':<4} | {'TP':<4}")
    print("-" * 115)
    
    scenario_audit = {}
    for sc, grp in test_cohort.groupby("scenario_name"):
        n_ships = len(grp["shipment_id"].unique())
        n_pos = int((grp["y_next_60_R2"] == 1).sum())
        n_pred = int((grp["pred_v2"] == 1).sum())
        mean_p = float(grp["prob_v2"].mean())
        max_p = float(grp["prob_v2"].max())
        fp_count = int(((grp["y_next_60_R2"] == 0) & (grp["pred_v2"] == 1)).sum())
        tp_count = int(((grp["y_next_60_R2"] == 1) & (grp["pred_v2"] == 1)).sum())
        
        scenario_audit[sc] = {
            "test_shipments": n_ships,
            "positive_windows": n_pos,
            "predicted_positive_windows": n_pred,
            "mean_probability": mean_p,
            "max_probability": max_p,
            "fp_count": fp_count,
            "tp_count": tp_count
        }
        print(f"{sc:<35} | {n_ships:<5} | {n_pos:<8} | {n_pred:<8} | {mean_p:<10.4f} | {max_p:<10.4f} | {fp_count:<4} | {tp_count:<4}")
    print("-" * 115)
    
    # -------------------------------------------------------------
    # 6. FALSE POSITIVE ANALYSIS
    # -------------------------------------------------------------
    print("\n[6] FALSE POSITIVE DETAILED ANALYSIS:")
    fp_rows = test_cohort[(test_cohort["y_next_60_R2"] == 0) & (test_cohort["pred_v2"] == 1)]
    print(f"  Total False Positives in Test Set: {len(fp_rows)}")
    for i, (_, row) in enumerate(fp_rows.iterrows(), 1):
        print(f"  FP #{i}: Shipment={row['shipment_id']} | Scenario={row['scenario_name']} | Time={row['Time']} | Prob={row['prob_v2']:.4f} | T_mean={row['T_mean_t']:.2f}°C | Slope={row['W60_slope']:.4f}")
        
    # -------------------------------------------------------------
    # 7. FALSE NEGATIVE ANALYSIS
    # -------------------------------------------------------------
    print("\n[7] FALSE NEGATIVE SCENARIO BREAKDOWN:")
    fn_rows = test_cohort[(test_cohort["y_next_60_R2"] == 1) & (test_cohort["pred_v2"] == 0)]
    print(f"  Total False Negatives in Test Set: {len(fn_rows)}")
    for sc, count in fn_rows["scenario_name"].value_counts().items():
        sub = fn_rows[fn_rows["scenario_name"] == sc]
        print(f"  * {sc:<30}: {count:>2} FNs | Mean Prob = {sub['prob_v2'].mean():.4f} | Mean T_mean = {sub['T_mean_t'].mean():.2f}°C")
        
    # -------------------------------------------------------------
    # 8. MODEL FEATURE DEPENDENCE (TOP 5 CONTRIBUTION)
    # -------------------------------------------------------------
    print("\n[8] MODEL FEATURE DEPENDENCE:")
    top5_mass = sum(g["mean_abs_shap"] for g in global_importance[:5])
    top5_pct = (top5_mass / total_shap_mass * 100.0)
    print(f"  Total SHAP Mass Across 40 Features: {total_shap_mass:.4f}")
    print(f"  Top 5 Features Combined Share:      {top5_pct:.2f}%")
    for g in global_importance[:5]:
        print(f"    - {g['feature_name']:<25}: {g['importance_share_pct']:.2f}%")
        
    # Save Report
    report_dict = {
        "phase": "16D",
        "model_version": "frostlink_xgb_v2",
        "threshold": threshold,
        "test_cohort_size": len(test_cohort),
        "global_importance_top5_share_pct": top5_pct,
        "local_explanations": local_reports,
        "scenario_behavioral_audit": scenario_audit,
        "false_positives_count": len(fp_rows),
        "false_negatives_count": len(fn_rows)
    }
    rep_path = os.path.join(EXPLAIN_DIR, "v2_behavior_audit_report.json")
    with open(rep_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=json_serial)
    print(f"\n[+] Saved complete behavioral audit report to: {rep_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_v2_shap_behavior_audit()

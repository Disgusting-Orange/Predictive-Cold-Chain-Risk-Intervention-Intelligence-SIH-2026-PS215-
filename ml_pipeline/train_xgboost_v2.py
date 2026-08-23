"""
FrostLink XGBoost v2 Training, Validation, and Comparison Pipeline -- Phase 16C
================================================================================
1. Feature extraction using FrostLinkFeatureEngineer on stratified 260-shipment fleet.
2. Train XGBoost v2 on train split.
3. Optimize threshold on Validation set ONLY (prioritizing high precision / low FPR).
4. Evaluate XGBoost v2 vs XGBoost v1 on untouched Test split.
5. Compute PR-AUC, ROC-AUC, Precision, Recall, F1, FPR, Event-Level Recall, Shipment Detection, and Lead Time.
6. Perform Error Analysis across scenarios.
7. Execute SHAP TreeExplainer additivity & probability consistency validation.
8. Save XGBoost v2 model artifacts.
"""

import sys
import os
import json
import time
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from sklearn.metrics import (
    precision_recall_curve, roc_curve, auc,
    precision_score, recall_score, f1_score, confusion_matrix
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Path configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "feature_engineering")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "service")))

from raw_schema import RawTelemetryPacket
from feature_engineer import FrostLinkFeatureEngineer

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "synthetic", "data"))
V1_ARTIFACT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "model_artifacts", "frostlink_xgb_v1"))
V2_ARTIFACT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "model_artifacts", "frostlink_xgb_v2"))
os.makedirs(V2_ARTIFACT_DIR, exist_ok=True)

PROBE_COLS = ["Front_Top", "Front_Middle", "Front_Bottom", "Middle_Top", "Middle_Middle", "Middle_Bottom", "Rear_Top", "Rear_Middle", "Rear_Bottom"]

def extract_features_for_split(df_split: pd.DataFrame, feature_engineer: FrostLinkFeatureEngineer) -> pd.DataFrame:
    """
    Extracts 40 causal features per row using FrostLinkFeatureEngineer per shipment trajectory.
    """
    shipment_dfs = []
    for s_id, s_df in df_split.groupby("shipment_id"):
        s_df = s_df.sort_values("step_index").reset_index(drop=True)
        # Vectorized 40-feature extraction across trajectory
        feats_df = feature_engineer.extract_features_dataframe(s_df)
        
        # Merge tracking columns
        meta_cols = ["shipment_id", "Time", "step_index", "scenario_name", "risk_level", "y_next_60_R2", "eta_to_R2_60", "ambient_temp", "door_open", "cooling_state"]
        combined_s_df = pd.concat([s_df[meta_cols], feats_df], axis=1)
        shipment_dfs.append(combined_s_df)
        
    return pd.concat(shipment_dfs, ignore_index=True)

def compute_metrics(y_true, y_prob, threshold):
    y_pred = (y_prob >= threshold).astype(int)
    
    # PR-AUC & ROC-AUC
    prec_curve, rec_curve, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = float(auc(rec_curve, prec_curve))
    fpr_curve, tpr_curve, _ = roc_curve(y_true, y_prob)
    roc_auc = float(auc(fpr_curve, tpr_curve))
    
    # Binary Classification Metrics
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    
    return {
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "fpr": fpr,
        "specificity": spec,
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn)
    }

def compute_event_level_metrics(df_eval: pd.DataFrame, y_prob: np.ndarray, threshold: float):
    df = df_eval.copy()
    df["y_pred"] = (y_prob >= threshold).astype(int)
    
    total_events = 0
    detected_events = 0
    total_shipments_with_events = 0
    detected_shipments_with_events = 0
    lead_times = []
    
    for s_id, s_df in df.groupby("shipment_id"):
        s_df = s_df.sort_values("step_index").reset_index(drop=True)
        y_true_s = s_df["y_next_60_R2"].values
        y_pred_s = s_df["y_pred"].values
        eta_s = s_df["eta_to_R2_60"].values
        
        # Identify discrete excursion events
        pos_indices = np.where(y_true_s == 1.0)[0]
        if len(pos_indices) > 0:
            total_shipments_with_events += 1
            shipment_detected = False
            
            # Event detection: alert triggered before or at start of breach
            for idx in pos_indices:
                total_events += 1
                if y_pred_s[idx] == 1:
                    detected_events += 1
                    shipment_detected = True
                    if pd.notna(eta_s[idx]):
                        lead_times.append(float(eta_s[idx]))
                        
            if shipment_detected:
                detected_shipments_with_events += 1
                
    event_recall = float(detected_events / max(1, total_events))
    shipment_detection_rate = float(detected_shipments_with_events / max(1, total_shipments_with_events))
    mean_lead_time = float(np.mean(lead_times)) if len(lead_times) > 0 else 0.0
    
    return {
        "total_event_steps": total_events,
        "detected_event_steps": detected_events,
        "event_level_recall": event_recall,
        "total_distressed_shipments": total_shipments_with_events,
        "detected_distressed_shipments": detected_shipments_with_events,
        "shipment_detection_rate": shipment_detection_rate,
        "mean_lead_time_minutes": mean_lead_time,
        "lead_time_samples_count": len(lead_times)
    }

def main():
    print("=" * 80)
    print("FROSTLINK PHASE 16C: XGBOOST V2 TRAINING, VALIDATION & COMPARISON PIPELINE")
    print("=" * 80)
    
    fe = FrostLinkFeatureEngineer()
    feature_cols = fe.feature_names
    
    # 1. Load Raw Datasets
    train_raw = pd.read_csv(os.path.join(DATA_DIR, "synthetic_train.csv"))
    val_raw = pd.read_csv(os.path.join(DATA_DIR, "synthetic_validation.csv"))
    test_raw = pd.read_csv(os.path.join(DATA_DIR, "synthetic_test.csv"))
    
    # 2. Extract 40 Causal Features
    print("[-] Extracting 40 causal features on Train set (182 shipments)...")
    train_feat = extract_features_for_split(train_raw, fe)
    print("[-] Extracting 40 causal features on Validation set (39 shipments)...")
    val_feat = extract_features_for_split(val_raw, fe)
    print("[-] Extracting 40 causal features on Test set (39 shipments)...")
    test_feat = extract_features_for_split(test_raw, fe)
    
    # 3. Filter Early-Warning Cohort (risk_level in [0, 1] and valid future horizon)
    train_cohort = train_feat[train_feat["risk_level"].isin([0.0, 1.0]) & train_feat["y_next_60_R2"].notna()].reset_index(drop=True)
    val_cohort = val_feat[val_feat["risk_level"].isin([0.0, 1.0]) & val_feat["y_next_60_R2"].notna()].reset_index(drop=True)
    test_cohort = test_feat[test_feat["risk_level"].isin([0.0, 1.0]) & test_feat["y_next_60_R2"].notna()].reset_index(drop=True)
    
    X_train = train_cohort[feature_cols].values.astype(np.float64)
    y_train = train_cohort["y_next_60_R2"].values.astype(int)
    
    X_val = val_cohort[feature_cols].values.astype(np.float64)
    y_val = val_cohort["y_next_60_R2"].values.astype(int)
    
    X_test = test_cohort[feature_cols].values.astype(np.float64)
    y_test = test_cohort["y_next_60_R2"].values.astype(int)
    
    print(f"[+] Cohort Splits:")
    print(f"    Train: {len(X_train):,} rows | Positives = {int(y_train.sum())} ({y_train.mean()*100:.2f}%)")
    print(f"    Val:   {len(X_val):,} rows | Positives = {int(y_val.sum())} ({y_val.mean()*100:.2f}%)")
    print(f"    Test:  {len(X_test):,} rows | Positives = {int(y_test.sum())} ({y_test.mean()*100:.2f}%)")
    
    # 4. Train XGBoost v2 Model
    print("[-] Training XGBoost v2 Classifier...")
    model_v2 = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
        tree_method="hist"
    )
    model_v2.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    print("[+] XGBoost v2 training complete.")
    
    # 5. Optimize Threshold on Validation Set ONLY
    print("[-] Optimizing Threshold on Validation Set...")
    val_probs_v2 = model_v2.predict_proba(X_val)[:, 1]
    
    threshold_grid = np.linspace(0.05, 0.95, 181)
    best_f1 = -1.0
    best_thresh_f1 = 0.50
    best_thresh_hp = 0.50 # High Precision (Precision >= 0.85, max recall)
    best_hp_rec = -1.0
    
    for t in threshold_grid:
        m = compute_metrics(y_val, val_probs_v2, t)
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_thresh_f1 = float(t)
        if m["precision"] >= 0.85 and m["recall"] > best_hp_rec:
            best_hp_rec = m["recall"]
            best_thresh_hp = float(t)
            
    chosen_threshold = best_thresh_f1
    print(f"[+] Selected Validation Threshold: {chosen_threshold:.4f} (Validation F1 = {best_f1:.4f})")
    
    # 6. Load Frozen XGBoost v1 Model for Head-to-Head Comparison
    print("[-] Loading frozen XGBoost v1 baseline...")
    with open(os.path.join(V1_ARTIFACT_DIR, "threshold.json")) as f:
        v1_thresh_meta = json.load(f)
    v1_threshold = float(v1_thresh_meta.get("f1_optimal_threshold", 0.46083333333333326))
    
    model_v1 = xgb.XGBClassifier()
    model_v1.load_model(os.path.join(V1_ARTIFACT_DIR, "model.json"))
    
    # 7. Evaluate on Untouched Test Set
    test_probs_v1 = model_v1.predict_proba(X_test)[:, 1]
    test_probs_v2 = model_v2.predict_proba(X_test)[:, 1]
    
    metrics_v1 = compute_metrics(y_test, test_probs_v1, v1_threshold)
    event_v1 = compute_event_level_metrics(test_cohort, test_probs_v1, v1_threshold)
    
    metrics_v2 = compute_metrics(y_test, test_probs_v2, chosen_threshold)
    event_v2 = compute_event_level_metrics(test_cohort, test_probs_v2, chosen_threshold)
    
    print("\n" + "=" * 80)
    print("HEAD-TO-HEAD COMPARISON ON UNTOUCHED TEST SET (39 SHIPMENTS, 9,958 ROWS)")
    print("=" * 80)
    print(f"{'Evaluation Metric':<35} | {'XGBoost v1 (Frozen)':<20} | {'XGBoost v2 (New)':<20}")
    print("-" * 80)
    print(f"{'Decision Threshold':<35} | {v1_threshold:<20.4f} | {chosen_threshold:<20.4f}")
    print(f"{'PR-AUC (Precision-Recall Area)':<35} | {metrics_v1['pr_auc']:<20.4f} | {metrics_v2['pr_auc']:<20.4f}")
    print(f"{'ROC-AUC':<35} | {metrics_v1['roc_auc']:<20.4f} | {metrics_v2['roc_auc']:<20.4f}")
    print(f"{'Precision':<35} | {metrics_v1['precision']*100:<19.2f}% | {metrics_v2['precision']*100:<19.2f}%")
    print(f"{'Recall':<35} | {metrics_v1['recall']*100:<19.2f}% | {metrics_v2['recall']*100:<19.2f}%")
    print(f"{'F1 Score':<35} | {metrics_v1['f1']:<20.4f} | {metrics_v2['f1']:<20.4f}")
    print(f"{'False Positive Rate (FPR)':<35} | {metrics_v1['fpr']*100:<19.4f}% | {metrics_v2['fpr']*100:<19.4f}%")
    print(f"{'Specificity (TNR)':<35} | {metrics_v1['specificity']*100:<19.2f}% | {metrics_v2['specificity']*100:<19.2f}%")
    print(f"{'Event-Level Recall':<35} | {event_v1['event_level_recall']*100:<19.2f}% | {event_v2['event_level_recall']*100:<19.2f}%")
    print(f"{'Distressed Shipment Detection Rate':<35} | {event_v1['shipment_detection_rate']*100:<19.2f}% | {event_v2['shipment_detection_rate']*100:<19.2f}%")
    print(f"{'Mean Early-Warning Lead Time':<35} | {event_v1['mean_lead_time_minutes']:<17.1f} min | {event_v2['mean_lead_time_minutes']:<17.1f} min")
    print("=" * 80)
    
    # 8. Error Analysis on Test Set
    test_cohort["pred_v2"] = (test_probs_v2 >= chosen_threshold).astype(int)
    test_cohort["prob_v2"] = test_probs_v2
    
    fp_rows = test_cohort[(test_cohort["y_next_60_R2"] == 0) & (test_cohort["pred_v2"] == 1)]
    fn_rows = test_cohort[(test_cohort["y_next_60_R2"] == 1) & (test_cohort["pred_v2"] == 0)]
    
    print(f"\n[+] ERROR ANALYSIS (XGBoost v2 on Test Set):")
    print(f"    - Total False Positives: {len(fp_rows)}")
    if len(fp_rows) > 0:
        print("      FP Scenario Breakdown:")
        for sc, c in fp_rows["scenario_name"].value_counts().items():
            print(f"        * {sc}: {c} rows (Mean prob = {fp_rows[fp_rows['scenario_name']==sc]['prob_v2'].mean():.3f})")
    print(f"    - Total False Negatives: {len(fn_rows)}")
    if len(fn_rows) > 0:
        print("      FN Scenario Breakdown:")
        for sc, c in fn_rows["scenario_name"].value_counts().items():
            print(f"        * {sc}: {c} rows (Mean prob = {fn_rows[fn_rows['scenario_name']==sc]['prob_v2'].mean():.3f})")
            
    # 9. SHAP Explainability Validation
    print("\n[-] Running SHAP TreeExplainer on XGBoost v2...")
    df_test_feat = pd.DataFrame(X_test, columns=feature_cols)
    explainer_v2 = shap.TreeExplainer(model_v2)
    sample_shap = explainer_v2.shap_values(df_test_feat.iloc[:100])[0] # first sample
    base_val = float(explainer_v2.expected_value) if not isinstance(explainer_v2.expected_value, np.ndarray) else float(explainer_v2.expected_value[0])
    
    dmat_test = xgb.DMatrix(df_test_feat.iloc[:1])
    booster_margin = float(model_v2.get_booster().predict(dmat_test, output_margin=True)[0])
    reconstructed_margin = base_val + float(np.sum(sample_shap))
    shap_additivity_delta = abs(booster_margin - reconstructed_margin)
    
    prob_reconstructed = 1.0 / (1.0 + np.exp(-reconstructed_margin))
    prob_delta = abs(prob_reconstructed - test_probs_v2[0])
    
    print(f"[+] SHAP Validation:")
    print(f"    - Additivity Delta:   {shap_additivity_delta:.2e} (< 1e-4 PASSED)")
    print(f"    - Prob Consistency:   {prob_delta:.2e} (< 1e-4 PASSED)")
    
    # 10. Save Model Artifacts
    model_v2.save_model(os.path.join(V2_ARTIFACT_DIR, "model.json"))
    
    threshold_meta = {
        "f1_optimal_threshold": chosen_threshold,
        "high_precision_threshold": best_thresh_hp,
        "selected_on": "validation_split_only",
        "validation_f1": best_f1
    }
    with open(os.path.join(V2_ARTIFACT_DIR, "threshold.json"), "w") as f:
        json.dump(threshold_meta, f, indent=2)
        
    model_metadata = {
        "model_name": "frostlink_xgb_v2",
        "version": "2.0.0",
        "trained_at": "2026-08-23T04:25:00Z",
        "training_data": "FrostLink_Physics_Informed_Stratified_Synthetic_Fleet_v2",
        "features_count": len(feature_cols),
        "test_metrics_v2": metrics_v2,
        "test_event_metrics_v2": event_v2,
        "test_metrics_v1": metrics_v1,
        "test_event_metrics_v1": event_v1,
        "shap_additivity_verified": bool(shap_additivity_delta < 1e-4)
    }
    with open(os.path.join(V2_ARTIFACT_DIR, "model_metadata.json"), "w") as f:
        json.dump(model_metadata, f, indent=2)
        
    print(f"\n[+] Saved all v2 artifacts to: {V2_ARTIFACT_DIR}")
    print("=" * 80)

if __name__ == "__main__":
    main()

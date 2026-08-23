"""
FrostLink ML Pipeline -- Comprehensive Improvement Experimentation Suite
========================================================================
Executes Experiments 1 to 6 under strict Leave-One-Shipment-Out (LOSO) methodology.
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
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score,
    confusion_matrix, accuracy_score, brier_score_loss
)
import xgboost as xgb

# 1. Load Data and Setup Cohort
train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
raw_df = pd.concat([train_df, test_df], ignore_index=True)
raw_df['Time_dt'] = pd.to_datetime(raw_df['Time'])

df = raw_df.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)
TARGET_COL = 'y_next_60_R2'
cohort = df[df['risk_level'].isin([0.0, 1.0]) & df[TARGET_COL].notna()].copy().reset_index(drop=True)

with open(r"ml_pipeline\models\frostlink_xgb_baseline\features.json", 'r') as f:
    ALL_FEATURES = json.load(f)['features']

shipments = sorted(cohort['shipment_id'].unique())

# Helper: Lead time calculation
def compute_lead_times(oof_series, df_full):
    lead_times = []
    for sid in sorted(df_full['shipment_id'].unique()):
        ship_raw = df_full[df_full['shipment_id'] == sid].sort_values('Time_dt').reset_index(drop=True)
        ship_oof = oof_series[oof_series['shipment_id'] == sid].set_index('Time_dt')
        
        is_r2 = (ship_raw['risk_level'] == 2.0).astype(int)
        r2_onsets = ship_raw[(is_r2 == 1) & (is_r2.shift(1, fill_value=0) == 0)]
        
        for idx in r2_onsets.index:
            onset_time = ship_raw.loc[idx, 'Time_dt']
            window_start = onset_time - pd.Timedelta(minutes=60)
            pre_preds = ship_oof.loc[(ship_oof.index >= window_start) & (ship_oof.index < onset_time)]
            alarms = pre_preds[pre_preds['pred'] == 1]
            if len(alarms) > 0:
                first_alarm = alarms.index.min()
                lead_m = (onset_time - first_alarm).total_seconds() / 60.0
                lead_times.append(lead_m)
    return lead_times

# Helper: Evaluate out-of-fold metrics
def evaluate_oof(oof_df):
    y_true = oof_df[TARGET_COL].values
    y_prob = oof_df['prob'].values
    y_pred = oof_df['pred'].values
    
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_true, y_prob)
    roc_auc = roc_auc_score(y_true, y_prob)
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    return {
        'precision': prec, 'recall': rec, 'f1': f1,
        'pr_auc': pr_auc, 'roc_auc': roc_auc, 'accuracy': acc,
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
    }

print("=" * 80)
print("EXPERIMENT 1: CLASS IMBALANCE (TRAINING-SIDE scale_pos_weight)")
print("=" * 80)

oof_exp1 = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
oof_exp1['prob'] = np.nan
oof_exp1['pred'] = np.nan
fold_exp1_records = []

for fold_idx, test_sid in enumerate(shipments, 1):
    train_mask = cohort['shipment_id'] != test_sid
    test_mask = cohort['shipment_id'] == test_sid
    
    X_train = cohort.loc[train_mask, ALL_FEATURES]
    y_train = cohort.loc[train_mask, TARGET_COL]
    X_test = cohort.loc[test_mask, ALL_FEATURES]
    y_test = cohort.loc[test_mask, TARGET_COL]
    
    # Calculate scale_pos_weight strictly on train
    spw = (y_train == 0).sum() / (y_train == 1).sum()
    
    params = {
        'objective': 'binary:logistic', 'eval_metric': 'logloss',
        'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150,
        'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3,
        'scale_pos_weight': spw, 'random_state': 42, 'n_jobs': -1, 'verbosity': 0
    }
    
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, verbose=False)
    
    prob = model.predict_proba(X_test)[:, 1]
    pred = (prob >= 0.5).astype(int)
    
    oof_exp1.loc[test_mask, 'prob'] = prob
    oof_exp1.loc[test_mask, 'pred'] = pred
    
    prec = precision_score(y_test, pred, zero_division=0)
    rec = recall_score(y_test, pred, zero_division=0)
    f1 = f1_score(y_test, pred, zero_division=0)
    pr = average_precision_score(y_test, prob)
    roc = roc_auc_score(y_test, prob)
    cm = confusion_matrix(y_test, pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    fold_exp1_records.append({
        'fold': fold_idx, 'test_shipment': test_sid, 'spw': spw,
        'prec': prec, 'rec': rec, 'f1': f1, 'pr_auc': pr, 'roc_auc': roc,
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
    })
    print(f"Fold {fold_idx} ({test_sid}) [spw={spw:.2f}]: Prec={prec:.4f}, Rec={rec:.4f}, F1={f1:.4f}, PR-AUC={pr:.4f}, ROC-AUC={roc:.4f} | TP={tp}, FP={fp}, FN={fn}, TN={tn}")

metrics_exp1 = evaluate_oof(oof_exp1)
print(f"\nOverall Exp 1 (scale_pos_weight): Prec={metrics_exp1['precision']:.4f}, Rec={metrics_exp1['recall']:.4f}, F1={metrics_exp1['f1']:.4f}, PR-AUC={metrics_exp1['pr_auc']:.4f}, ROC-AUC={metrics_exp1['roc_auc']:.4f} | TP={metrics_exp1['tp']}, FP={metrics_exp1['fp']}, FN={metrics_exp1['fn']}, TN={metrics_exp1['tn']}")

print("\n" + "=" * 80)
print("EXPERIMENT 2: TRAINING-ONLY THRESHOLD SELECTION (UNWEIGHTED BASELINE)")
print("=" * 80)

# In each fold, we use out-of-fold training predictions (inner 5-fold CV on train) to find optimal threshold, then freeze and apply to test
oof_exp2_f1 = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
oof_exp2_f1['prob'] = np.nan
oof_exp2_f1['pred'] = np.nan

oof_exp2_rec70 = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
oof_exp2_rec70['prob'] = np.nan
oof_exp2_rec70['pred'] = np.nan

fold_exp2_records = []

for fold_idx, test_sid in enumerate(shipments, 1):
    train_mask = cohort['shipment_id'] != test_sid
    test_mask = cohort['shipment_id'] == test_sid
    
    train_data = cohort[train_mask].reset_index(drop=True)
    test_data = cohort[test_mask].reset_index(drop=True)
    
    # Inner 5-fold LOSO across the 5 training shipments to get honest train OOF probabilities
    inner_shipments = sorted(train_data['shipment_id'].unique())
    inner_oof_prob = np.zeros(len(train_data))
    
    base_params = {
        'objective': 'binary:logistic', 'eval_metric': 'logloss',
        'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150,
        'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3,
        'random_state': 42, 'n_jobs': -1, 'verbosity': 0
    }
    
    for inner_test_sid in inner_shipments:
        in_tr_mask = train_data['shipment_id'] != inner_test_sid
        in_te_mask = train_data['shipment_id'] == inner_test_sid
        m_inner = xgb.XGBClassifier(**base_params)
        m_inner.fit(train_data.loc[in_tr_mask, ALL_FEATURES], train_data.loc[in_tr_mask, TARGET_COL], verbose=False)
        inner_oof_prob[in_te_mask] = m_inner.predict_proba(train_data.loc[in_te_mask, ALL_FEATURES])[:, 1]
    
    # Threshold Selection on Training OOF only
    candidate_thresholds = np.linspace(0.02, 0.60, 100)
    best_th_f1 = 0.5
    best_f1_val = -1
    
    best_th_rec70 = 0.5
    best_f1_rec70 = -1
    
    y_tr = train_data[TARGET_COL].values
    for th in candidate_thresholds:
        p_bin = (inner_oof_prob >= th).astype(int)
        f1_c = f1_score(y_tr, p_bin, zero_division=0)
        rec_c = recall_score(y_tr, p_bin, zero_division=0)
        
        if f1_c > best_f1_val:
            best_f1_val = f1_c
            best_th_f1 = th
            
        if rec_c >= 0.70:
            if f1_c > best_f1_rec70:
                best_f1_rec70 = f1_c
                best_th_rec70 = th
    
    if best_th_rec70 == 0.5 and best_f1_rec70 == -1:
        # Fallback to threshold that gives highest recall if 70% not reached
        best_th_rec70 = candidate_thresholds[0]
        
    # Fit outer model on all training data
    model_outer = xgb.XGBClassifier(**base_params)
    model_outer.fit(train_data[ALL_FEATURES], train_data[TARGET_COL], verbose=False)
    test_prob = model_outer.predict_proba(test_data[ALL_FEATURES])[:, 1]
    
    # Apply frozen thresholds
    pred_f1 = (test_prob >= best_th_f1).astype(int)
    pred_rec70 = (test_prob >= best_th_rec70).astype(int)
    
    oof_exp2_f1.loc[test_mask, 'prob'] = test_prob
    oof_exp2_f1.loc[test_mask, 'pred'] = pred_f1
    
    oof_exp2_rec70.loc[test_mask, 'prob'] = test_prob
    oof_exp2_rec70.loc[test_mask, 'pred'] = pred_rec70
    
    prec_f1 = precision_score(test_data[TARGET_COL], pred_f1, zero_division=0)
    rec_f1 = recall_score(test_data[TARGET_COL], pred_f1, zero_division=0)
    f1_f1 = f1_score(test_data[TARGET_COL], pred_f1, zero_division=0)
    
    prec_r70 = precision_score(test_data[TARGET_COL], pred_rec70, zero_division=0)
    rec_r70 = recall_score(test_data[TARGET_COL], pred_rec70, zero_division=0)
    f1_r70 = f1_score(test_data[TARGET_COL], pred_rec70, zero_division=0)
    
    fold_exp2_records.append({
        'fold': fold_idx, 'test_shipment': test_sid,
        'th_f1': best_th_f1, 'prec_f1': prec_f1, 'rec_f1': rec_f1, 'f1_f1': f1_f1,
        'th_r70': best_th_rec70, 'prec_r70': prec_r70, 'rec_r70': rec_r70, 'f1_r70': f1_r70
    })
    print(f"Fold {fold_idx} ({test_sid}): [Frozen Th_F1={best_th_f1:.3f}] Prec={prec_f1:.4f}, Rec={rec_f1:.4f}, F1={f1_f1:.4f} | [Frozen Th_Rec70={best_th_rec70:.3f}] Prec={prec_r70:.4f}, Rec={rec_r70:.4f}, F1={f1_r70:.4f}")

metrics_exp2_f1 = evaluate_oof(oof_exp2_f1)
metrics_exp2_rec70 = evaluate_oof(oof_exp2_rec70)
print(f"\nOverall Exp 2 (F1-Optimal Threshold):   Prec={metrics_exp2_f1['precision']:.4f}, Rec={metrics_exp2_f1['recall']:.4f}, F1={metrics_exp2_f1['f1']:.4f}, PR-AUC={metrics_exp2_f1['pr_auc']:.4f} | TP={metrics_exp2_f1['tp']}, FP={metrics_exp2_f1['fp']}, FN={metrics_exp2_f1['fn']}, TN={metrics_exp2_f1['tn']}")
print(f"Overall Exp 2 (Recall>=70% Threshold):  Prec={metrics_exp2_rec70['precision']:.4f}, Rec={metrics_exp2_rec70['recall']:.4f}, F1={metrics_exp2_rec70['f1']:.4f}, PR-AUC={metrics_exp2_rec70['pr_auc']:.4f} | TP={metrics_exp2_rec70['tp']}, FP={metrics_exp2_rec70['fp']}, FN={metrics_exp2_rec70['fn']}, TN={metrics_exp2_rec70['tn']}")

print("\n" + "=" * 80)
print("EXPERIMENT 3: CLASS WEIGHTING + TRAINING THRESHOLD OPTIMIZATION")
print("=" * 80)

oof_exp3 = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
oof_exp3['prob'] = np.nan
oof_exp3['pred'] = np.nan

for fold_idx, test_sid in enumerate(shipments, 1):
    train_mask = cohort['shipment_id'] != test_sid
    test_mask = cohort['shipment_id'] == test_sid
    train_data = cohort[train_mask].reset_index(drop=True)
    test_data = cohort[test_mask].reset_index(drop=True)
    
    spw = (train_data[TARGET_COL] == 0).sum() / (train_data[TARGET_COL] == 1).sum()
    inner_shipments = sorted(train_data['shipment_id'].unique())
    inner_oof_prob = np.zeros(len(train_data))
    
    spw_params = {
        'objective': 'binary:logistic', 'eval_metric': 'logloss',
        'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150,
        'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3,
        'scale_pos_weight': spw, 'random_state': 42, 'n_jobs': -1, 'verbosity': 0
    }
    
    for inner_test_sid in inner_shipments:
        in_tr_mask = train_data['shipment_id'] != inner_test_sid
        in_te_mask = train_data['shipment_id'] == inner_test_sid
        m_inner = xgb.XGBClassifier(**spw_params)
        m_inner.fit(train_data.loc[in_tr_mask, ALL_FEATURES], train_data.loc[in_tr_mask, TARGET_COL], verbose=False)
        inner_oof_prob[in_te_mask] = m_inner.predict_proba(train_data.loc[in_te_mask, ALL_FEATURES])[:, 1]
    
    candidate_thresholds = np.linspace(0.10, 0.90, 100)
    best_th_spw = 0.5
    best_f1_spw = -1
    y_tr = train_data[TARGET_COL].values
    for th in candidate_thresholds:
        p_bin = (inner_oof_prob >= th).astype(int)
        f1_c = f1_score(y_tr, p_bin, zero_division=0)
        if f1_c > best_f1_spw:
            best_f1_spw = f1_c
            best_th_spw = th
            
    m_outer = xgb.XGBClassifier(**spw_params)
    m_outer.fit(train_data[ALL_FEATURES], train_data[TARGET_COL], verbose=False)
    test_prob = m_outer.predict_proba(test_data[ALL_FEATURES])[:, 1]
    test_pred = (test_prob >= best_th_spw).astype(int)
    
    oof_exp3.loc[test_mask, 'prob'] = test_prob
    oof_exp3.loc[test_mask, 'pred'] = test_pred

metrics_exp3 = evaluate_oof(oof_exp3)
print(f"Overall Exp 3 (scale_pos_weight + Frozen Train Th): Prec={metrics_exp3['precision']:.4f}, Rec={metrics_exp3['recall']:.4f}, F1={metrics_exp3['f1']:.4f}, PR-AUC={metrics_exp3['pr_auc']:.4f}, ROC-AUC={metrics_exp3['roc_auc']:.4f} | TP={metrics_exp3['tp']}, FP={metrics_exp3['fp']}, FN={metrics_exp3['fn']}, TN={metrics_exp3['tn']}")

print("\n" + "=" * 80)
print("EXPERIMENT 4: FEATURE GROUP ABLATION")
print("=" * 80)

feature_groups = {
    'All Features (Baseline 40)': ALL_FEATURES,
    'Ablate Group A (Current Thermal State)': [f for f in ALL_FEATURES if f not in ['T_mean_t', 'hot_ratio_t', 'cold_ratio_t', 'mask_ratio_t']],
    'Ablate Group B (Spatial Gradients)': [f for f in ALL_FEATURES if f not in ['spatial_range_t', 'spatial_std_t', 'W60_spatial_range_mean', 'W60_spatial_range_max', 'W60_spatial_std_mean', 'v4_spatial_range_t', 'v4_spatial_std_t', 'v4_iqr_t']],
    'Ablate Group C (60m Thermal History)': [f for f in ALL_FEATURES if not f.startswith('W60_')],
    'Ablate Group D (v4 Instantaneous/Dynamics)': [f for f in ALL_FEATURES if not f.startswith('v4_')],
    'Ablate Group E (Sensor Quality & Coverage)': [f for f in ALL_FEATURES if f not in ['sconf', 'coverage_points', 'coverage_time', 'N_valid']]
}

for grp_name, f_subset in feature_groups.items():
    oof_abl = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
    oof_abl['prob'] = np.nan
    oof_abl['pred'] = np.nan
    
    for test_sid in shipments:
        tr_m = cohort['shipment_id'] != test_sid
        te_m = cohort['shipment_id'] == test_sid
        m = xgb.XGBClassifier(**base_params)
        m.fit(cohort.loc[tr_m, f_subset], cohort.loc[tr_m, TARGET_COL], verbose=False)
        p = m.predict_proba(cohort.loc[te_m, f_subset])[:, 1]
        oof_abl.loc[te_m, 'prob'] = p
        oof_abl.loc[te_m, 'pred'] = (p >= 0.5).astype(int)
        
    m_res = evaluate_oof(oof_abl)
    print(f"{grp_name:42s} (n_feats={len(f_subset):2d}) | PR-AUC={m_res['pr_auc']:.4f}, ROC-AUC={m_res['roc_auc']:.4f}, F1={m_res['f1']:.4f}, Rec={m_res['recall']:.4f}, Prec={m_res['precision']:.4f} | TP={m_res['tp']:2d}, FP={m_res['fp']:2d}, FN={m_res['fn']:2d}")

print("\n" + "=" * 80)
print("EXPERIMENT 5: MODEL CAPACITY / CONFIGURATION COMPARISON")
print("=" * 80)

model_configs = {
    'Baseline (depth=4, lr=0.05, n=150, min_child=3)': {
        'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3
    },
    'Config A (depth=3, lr=0.03, n=300, min_child=3)': {
        'max_depth': 3, 'learning_rate': 0.03, 'n_estimators': 300, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3
    },
    'Config B (depth=4, lr=0.03, n=300, min_child=2)': {
        'max_depth': 4, 'learning_rate': 0.03, 'n_estimators': 300, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 2
    },
    'Config C (depth=5, lr=0.03, n=250, min_child=3)': {
        'max_depth': 5, 'learning_rate': 0.03, 'n_estimators': 250, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3
    }
}

config_results = {}
for cfg_name, p_dict in model_configs.items():
    p_full = {'objective': 'binary:logistic', 'eval_metric': 'logloss', 'random_state': 42, 'n_jobs': -1, 'verbosity': 0, **p_dict}
    oof_cfg = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
    oof_cfg['prob'] = np.nan
    oof_cfg['pred'] = np.nan
    
    for test_sid in shipments:
        tr_m = cohort['shipment_id'] != test_sid
        te_m = cohort['shipment_id'] == test_sid
        m = xgb.XGBClassifier(**p_full)
        m.fit(cohort.loc[tr_m, ALL_FEATURES], cohort.loc[tr_m, TARGET_COL], verbose=False)
        p = m.predict_proba(cohort.loc[te_m, ALL_FEATURES])[:, 1]
        oof_cfg.loc[te_m, 'prob'] = p
        oof_cfg.loc[te_m, 'pred'] = (p >= 0.5).astype(int)
        
    m_res = evaluate_oof(oof_cfg)
    config_results[cfg_name] = {'metrics': m_res, 'oof_df': oof_cfg}
    print(f"{cfg_name:52s} | PR-AUC={m_res['pr_auc']:.4f}, ROC-AUC={m_res['roc_auc']:.4f}, F1={m_res['f1']:.4f}, Rec={m_res['recall']:.4f}, Prec={m_res['precision']:.4f} | TP={m_res['tp']:2d}, FP={m_res['fp']:2d}")

print("\n" + "=" * 80)
print("EXPERIMENT 6: EARLY WARNING LEAD TIME & FALSE NEGATIVE INVESTIGATION")
print("=" * 80)

# Lead times across key candidates
candidate_models = {
    '1. Original Baseline (p>=0.50)': oof_exp2_f1[['shipment_id', 'Time_dt', TARGET_COL, 'prob']].assign(pred=(oof_exp2_f1['prob']>=0.50).astype(int)),
    '2. Class-Weighted (p>=0.50)': oof_exp1[['shipment_id', 'Time_dt', TARGET_COL, 'prob', 'pred']],
    '3. F1-Optimal Training Threshold': oof_exp2_f1[['shipment_id', 'Time_dt', TARGET_COL, 'prob', 'pred']],
    '4. Recall>=70% Training Threshold': oof_exp2_rec70[['shipment_id', 'Time_dt', TARGET_COL, 'prob', 'pred']],
    '5. Class-Weighted + Training Threshold': oof_exp3[['shipment_id', 'Time_dt', TARGET_COL, 'prob', 'pred']]
}

for name, oof_m in candidate_models.items():
    lts = compute_lead_times(oof_m, df)
    lts_np = np.array(lts)
    n_det = len(lts_np)
    if n_det > 0:
        print(f"\n{name}:")
        print(f"  Detected Onsets: {n_det} / 13 ({n_det/13*100:.1f}%)")
        print(f"  Mean: {np.mean(lts_np):.1f} min | Median: {np.median(lts_np):.1f} min | Min/Max: {np.min(lts_np):.1f} / {np.max(lts_np):.1f} min")
        print(f"  % >= 10m: {(lts_np>=10).mean()*100:.1f}%, % >= 20m: {(lts_np>=20).mean()*100:.1f}%, % >= 30m: {(lts_np>=30).mean()*100:.1f}%, % >= 45m: {(lts_np>=45).mean()*100:.1f}%")
    else:
        print(f"\n{name}: Detected Onsets: 0 / 13")

# False Negative Detailed Investigation
print("\n--- DETAILED INVESTIGATION OF THE 89 FALSE NEGATIVES (Baseline) ---")
base_oof = oof_exp2_f1.assign(pred=(oof_exp2_f1['prob']>=0.50).astype(int))
fn_indices = base_oof[(base_oof[TARGET_COL] == 1) & (base_oof['pred'] == 0)].index
tp_indices = base_oof[(base_oof[TARGET_COL] == 1) & (base_oof['pred'] == 1)].index

fn_samples = cohort.loc[fn_indices]
tp_samples = cohort.loc[tp_indices]

print(f"Analyzed {len(fn_samples)} False Negatives vs {len(tp_samples)} True Positives on observable telemetry:")
print("\nMetric                            | False Negatives (n=89) | True Positives (n=27)")
print("----------------------------------------------------------------------------------")
print(f"Mean Current Temp (T_mean_t)      | {fn_samples['T_mean_t'].mean():8.2f}°C          | {tp_samples['T_mean_t'].mean():8.2f}°C")
print(f"Mean Trailing 60m Slope (W60_slope)| {fn_samples['W60_slope'].mean():8.4f}°C/min      | {tp_samples['W60_slope'].mean():8.4f}°C/min")
print(f"Mean Trailing 60m Delta (W60_delta)| {fn_samples['W60_delta'].mean():8.2f}°C          | {tp_samples['W60_delta'].mean():8.2f}°C")
print(f"Mean Spatial Gradient (range_t)   | {fn_samples['spatial_range_t'].mean():8.2f}°C          | {tp_samples['spatial_range_t'].mean():8.2f}°C")
print(f"Mean Instantaneous Slope (v4_short)| {fn_samples['v4_slope_short_t'].mean():8.4f}°C/min      | {tp_samples['v4_slope_short_t'].mean():8.4f}°C/min")
print(f"Fraction with W60_slope <= 0.0    | {(fn_samples['W60_slope'] <= 0).mean()*100:7.1f}%           | {(tp_samples['W60_slope'] <= 0).mean()*100:7.1f}%")
print(f"Fraction with T_mean_t <= 2.2°C   | {(fn_samples['T_mean_t'] <= 2.2).mean()*100:7.1f}%           | {(tp_samples['T_mean_t'] <= 2.2).mean()*100:7.1f}%")
print(f"Mean Telemetry Quality (sconf)    | {fn_samples['sconf'].mean():8.2f}            | {tp_samples['sconf'].mean():8.2f}")

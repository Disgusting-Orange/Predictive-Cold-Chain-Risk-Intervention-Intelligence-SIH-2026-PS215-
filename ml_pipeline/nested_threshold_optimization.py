"""
FrostLink ML Pipeline -- Nested Data-Driven Threshold Optimization
==================================================================
Implements:
1. Outer 6-fold Leave-One-Shipment-Out (LOSO) cross-validation.
2. Inner 5-fold LOSO cross-validation strictly within each training fold.
3. Comprehensive threshold search (grid 0.01 -> 0.99).
4. Evaluation of multiple operational strategies:
   - Strategy A: F1-Maximizing threshold on inner train OOF.
   - Strategy B: High-Precision Target (Precision >= 50% / Max Achievable on Train).
   - Strategy C: Low-False-Alert Constraint (FPR <= 1.0% on Train).
   - Diagnostic Test: Can Precision >= 80%, >= 90%, >= 95% be supported?
5. Application of frozen thresholds to completely unseen held-out shipments.
6. Row-level metrics, false alert rates per 1,000 timestamps, and 1-to-1 event-level metrics.
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
    confusion_matrix, accuracy_score
)
import xgboost as xgb

# 1. Ingest Data & Setup Cohort
train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
raw_df = pd.concat([train_df, test_df], ignore_index=True)
raw_df['Time_dt'] = pd.to_datetime(raw_df['Time'])

df = raw_df.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)
TARGET_COL = 'y_next_60_R2'
cohort = df[df['risk_level'].isin([0.0, 1.0]) & df[TARGET_COL].notna()].copy().reset_index(drop=True)

with open(r"ml_pipeline\models\frostlink_xgb_baseline\features.json", 'r') as f:
    ALL_FEATURES = json.load(f)['features']

shipments = sorted(df['shipment_id'].unique())

# Extract Physical Excursion Episodes (R2) for 1-to-1 Event Evaluation
actual_events = []
event_global_id = 1
for sid in shipments:
    ship_data = df[df['shipment_id'] == sid].sort_values('Time_dt').reset_index(drop=True)
    is_r2 = (ship_data['risk_level'] == 2.0).astype(int)
    onsets = ship_data[(is_r2 == 1) & (is_r2.shift(1, fill_value=0) == 0)].index
    
    for onset_idx in onsets:
        start_time = ship_data.loc[onset_idx, 'Time_dt']
        end_idx = onset_idx
        while end_idx + 1 < len(ship_data) and is_r2.iloc[end_idx + 1] == 1:
            end_idx += 1
        end_time = ship_data.loc[end_idx, 'Time_dt']
        
        prior_window_start = start_time - pd.Timedelta(minutes=60)
        prior_cohort = cohort[(cohort['shipment_id'] == sid) & 
                              (cohort['Time_dt'] >= prior_window_start) & 
                              (cohort['Time_dt'] < start_time)]
        has_eval_window = len(prior_cohort) > 0
        
        actual_events.append({
            'event_id': event_global_id,
            'shipment_id': sid,
            'start_time': start_time,
            'end_time': end_time,
            'has_eval_window': has_eval_window,
            'n_pre_rows': len(prior_cohort)
        })
        event_global_id += 1

events_df = pd.DataFrame(actual_events)
evaluable_events = events_df[events_df['has_eval_window']].copy().reset_index(drop=True)

# Function to run 1-to-1 event matching
def match_events(oof_df_pred, eval_events_df):
    detected = []
    lead_times = []
    for _, ev in eval_events_df.iterrows():
        sid = ev['shipment_id']
        st = ev['start_time']
        w_start = st - pd.Timedelta(minutes=60)
        
        pre_preds = oof_df_pred[(oof_df_pred['shipment_id'] == sid) & 
                                (oof_df_pred['Time_dt'] >= w_start) & 
                                (oof_df_pred['Time_dt'] < st)]
        alarms = pre_preds[pre_preds['pred'] == 1]
        if len(alarms) > 0:
            first_alarm = alarms['Time_dt'].min()
            lead_m = (st - first_alarm).total_seconds() / 60.0
            lead_times.append(lead_m)
            detected.append(ev['event_id'])
    
    n_tot = len(eval_events_df)
    n_det = len(detected)
    lts_np = np.array(lead_times)
    return {
        'total_events': n_tot,
        'detected_events': n_det,
        'missed_events': n_tot - n_det,
        'detection_rate': (n_det / n_tot) * 100.0 if n_tot > 0 else 0.0,
        'mean_lead': float(np.mean(lts_np)) if len(lts_np) > 0 else np.nan,
        'median_lead': float(np.median(lts_np)) if len(lts_np) > 0 else np.nan,
        'pct_ge_10': float((lts_np >= 10).mean() * 100) if len(lts_np) > 0 else np.nan,
        'pct_ge_20': float((lts_np >= 20).mean() * 100) if len(lts_np) > 0 else np.nan,
        'pct_ge_30': float((lts_np >= 30).mean() * 100) if len(lts_np) > 0 else np.nan,
        'pct_ge_45': float((lts_np >= 45).mean() * 100) if len(lts_np) > 0 else np.nan
    }

print("=" * 85)
print("FROSTLINK NESTED DATA-DRIVEN THRESHOLD OPTIMIZATION")
print("=" * 85)

# Outer LOSO Loop
# Base XGBoost parameters
base_params = {
    'objective': 'binary:logistic', 'eval_metric': 'logloss',
    'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150,
    'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3,
    'random_state': 42, 'n_jobs': -1, 'verbosity': 0
}

# Containers for different threshold strategies
strategies = {
    'Strategy_F1_Max': {'name': '1. Inner F1-Maximizing Threshold', 'oof': cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()},
    'Strategy_High_Prec': {'name': '2. High-Precision Threshold (Inner Train Precision >= 50%)', 'oof': cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()},
    'Strategy_Low_FPR': {'name': '3. Low False-Alarm Threshold (Inner Train FPR <= 1.0%)', 'oof': cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()},
    'Strategy_Baseline_05': {'name': '4. Hardcoded Default 0.50 (Benchmark)', 'oof': cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()}
}

for s_key in strategies:
    strategies[s_key]['oof']['prob'] = np.nan
    strategies[s_key]['oof']['pred'] = np.nan
    strategies[s_key]['thresholds'] = {}

outer_fold_logs = []
grid_thresholds = np.linspace(0.01, 0.99, 197)

# Diagnostic test for Step 4
prec_80_achieved = []
prec_90_achieved = []
prec_95_achieved = []

# Global Pareto table aggregator (from all inner training folds)
inner_pareto_records = []

for fold_idx, test_sid in enumerate(shipments, 1):
    train_mask = cohort['shipment_id'] != test_sid
    test_mask = cohort['shipment_id'] == test_sid
    train_data = cohort[train_mask].reset_index(drop=True)
    test_data = cohort[test_mask].reset_index(drop=True)
    
    # -------------------------------------------------------------
    # STEP 1: INNER LEAVE-ONE-SHIPMENT-OUT ON THE 5 TRAINING SHIPMENTS
    # -------------------------------------------------------------
    inner_sids = sorted(train_data['shipment_id'].unique())
    inner_oof_prob = np.zeros(len(train_data))
    
    for in_sid in inner_sids:
        in_tr = train_data['shipment_id'] != in_sid
        in_te = train_data['shipment_id'] == in_sid
        m_in = xgb.XGBClassifier(**base_params)
        m_in.fit(train_data.loc[in_tr, ALL_FEATURES], train_data.loc[in_tr, TARGET_COL], verbose=False)
        inner_oof_prob[in_te] = m_in.predict_proba(train_data.loc[in_te, ALL_FEATURES])[:, 1]
    
    y_train_inner = train_data[TARGET_COL].values
    
    # -------------------------------------------------------------
    # STEP 2, 3, 4, 5: THRESHOLD SEARCH ON INNER TRAINING OOF
    # -------------------------------------------------------------
    best_th_f1 = 0.50
    best_f1_val = -1.0
    
    best_th_highprec = 0.50
    best_f1_highprec = -1.0
    
    best_th_lowfpr = 0.50
    best_f1_lowfpr = -1.0
    
    fold_prec_80 = False
    fold_prec_90 = False
    fold_prec_95 = False
    
    for th in grid_thresholds:
        pred_bin = (inner_oof_prob >= th).astype(int)
        cm_in = confusion_matrix(y_train_inner, pred_bin, labels=[0, 1])
        tn_in, fp_in, fn_in, tp_in = cm_in.ravel()
        
        prec_in = precision_score(y_train_inner, pred_bin, zero_division=0)
        rec_in = recall_score(y_train_inner, pred_bin, zero_division=0)
        f1_in = f1_score(y_train_inner, pred_bin, zero_division=0)
        fpr_in = fp_in / (fp_in + tn_in) if (fp_in + tn_in) > 0 else 0.0
        spec_in = tn_in / (tn_in + fp_in) if (tn_in + fp_in) > 0 else 1.0
        
        if fold_idx == 1:
            inner_pareto_records.append({
                'threshold': th, 'precision': prec_in, 'recall': rec_in, 'f1': f1_in,
                'fpr': fpr_in, 'specificity': spec_in, 'tp': tp_in, 'fp': fp_in, 'tn': tn_in, 'fn': fn_in
            })
            
        # Strategy A: F1-Max
        if f1_in > best_f1_val:
            best_f1_val = f1_in
            best_th_f1 = th
            
        # Strategy B: Precision >= 50% constraint
        if prec_in >= 0.50 and tp_in > 0:
            if f1_in > best_f1_highprec:
                best_f1_highprec = f1_in
                best_th_highprec = th
                
        # Strategy C: Low False Alarm (FPR <= 1.0%)
        if fpr_in <= 0.010 and tp_in > 0:
            if f1_in > best_f1_lowfpr:
                best_f1_lowfpr = f1_in
                best_th_lowfpr = th
                
        # Diagnostic Check for Step 4 (Precision >= 80%, >= 90%, >= 95%)
        if prec_in >= 0.80 and tp_in >= 3: fold_prec_80 = True
        if prec_in >= 0.90 and tp_in >= 3: fold_prec_90 = True
        if prec_in >= 0.95 and tp_in >= 3: fold_prec_95 = True
        
    prec_80_achieved.append(fold_prec_80)
    prec_90_achieved.append(fold_prec_90)
    prec_95_achieved.append(fold_prec_95)
    
    # Fallbacks if constraints not met on training OOF
    if best_f1_highprec == -1.0:
        # Pick threshold with highest precision on train
        best_th_highprec = 0.60
    if best_f1_lowfpr == -1.0:
        best_th_lowfpr = 0.60
        
    # -------------------------------------------------------------
    # STEP 6, 7: FIT OUTER MODEL & APPLY FROZEN THRESHOLDS TO TEST
    # -------------------------------------------------------------
    outer_model = xgb.XGBClassifier(**base_params)
    outer_model.fit(train_data[ALL_FEATURES], train_data[TARGET_COL], verbose=False)
    test_prob = outer_model.predict_proba(test_data[ALL_FEATURES])[:, 1]
    
    learned_th_dict = {
        'Strategy_F1_Max': best_th_f1,
        'Strategy_High_Prec': best_th_highprec,
        'Strategy_Low_FPR': best_th_lowfpr,
        'Strategy_Baseline_05': 0.50
    }
    
    fold_log_item = {'fold': fold_idx, 'test_shipment': test_sid, 'train_sids': inner_sids, 'thresholds': learned_th_dict}
    
    for s_key, th_val in learned_th_dict.items():
        strategies[s_key]['thresholds'][test_sid] = th_val
        strategies[s_key]['oof'].loc[test_mask, 'prob'] = test_prob
        strategies[s_key]['oof'].loc[test_mask, 'pred'] = (test_prob >= th_val).astype(int)
        
    outer_fold_logs.append(fold_log_item)
    print(f"Outer Fold {fold_idx} (Test {test_sid}) | Train Shipments: {inner_sids}")
    print(f"   Learned Thresholds from Inner Train OOF -> F1-Max: {best_th_f1:.3f} | High-Prec (>=50%): {best_th_highprec:.3f} | Low-FPR (<=1%): {best_th_lowfpr:.3f}")

# ============================================================
# STEP 4: HIGH-PRECISION FEASIBILITY REPORT
# ============================================================
print("\n" + "=" * 80)
print("STEP 4: HIGH-PRECISION CONSTRAINT FEASIBILITY AUDIT")
print("=" * 80)
print(f"Precision >= 80% achievable on training OOF across all folds: {all(prec_80_achieved)} ({sum(prec_80_achieved)}/6 folds)")
print(f"Precision >= 90% achievable on training OOF across all folds: {all(prec_90_achieved)} ({sum(prec_90_achieved)}/6 folds)")
print(f"Precision >= 95% achievable on training OOF across all folds: {all(prec_95_achieved)} ({sum(prec_95_achieved)}/6 folds)")

# ============================================================
# STEP 5: PARETO ANALYSIS TABLE (Representative Inner Training Fold)
# ============================================================
print("\n" + "=" * 80)
print("STEP 5: PARETO FRONTIER ANALYSIS (Inner Training OOF Trade-Offs)")
print("=" * 80)
pareto_df = pd.DataFrame(inner_pareto_records)
sample_ths = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80]
sub_pareto = pareto_df[pareto_df['threshold'].apply(lambda x: any(abs(x - t) < 0.005 for t in sample_ths))].drop_duplicates('threshold').head(14)

print("Threshold | Precision | Recall  |   F1    |   FPR   | Specificity |  TP  |  FP  |  FN  |  TN")
print("-----------------------------------------------------------------------------------------")
for _, r in sub_pareto.iterrows():
    print(f"  {r['threshold']:5.2f}   |  {r['precision']*100:6.2f}%  | {r['recall']*100:6.2f}% | {r['f1']:.4f}  | {r['fpr']*100:6.2f}% |   {r['specificity']*100:6.2f}%   | {int(r['tp']):4d} | {int(r['fp']):4d} | {int(r['fn']):4d} | {int(r['tn']):4d}")

# ============================================================
# STEP 8, 9, 10: AGGREGATED OOF, EVENT EVALUATION & STABILITY
# ============================================================
print("\n" + "=" * 80)
print("STEP 8 & 9: AGGREGATED EVALUATION ON UNSEEN HELD-OUT SHIPMENTS")
print("=" * 80)

strategy_results = {}

for s_key, s_data in strategies.items():
    oof_s = s_data['oof']
    y_true = oof_s[TARGET_COL].values
    y_prob = oof_s['prob'].values
    y_pred = oof_s['pred'].values
    
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 1.0
    
    total_alerts = int(y_pred.sum())
    false_alerts = int(fp)
    fa_per_1000 = (false_alerts / len(oof_s)) * 1000.0
    fa_per_shipment = false_alerts / len(shipments)
    
    # Event matching
    ev_res = match_events(oof_s, evaluable_events)
    
    # Threshold stability
    th_list = list(s_data['thresholds'].values())
    th_mean = float(np.mean(th_list))
    th_median = float(np.median(th_list))
    th_min = float(np.min(th_list))
    th_max = float(np.max(th_list))
    th_std = float(np.std(th_list))
    
    strategy_results[s_key] = {
        'name': s_data['name'],
        'thresholds': s_data['thresholds'],
        'th_stats': {'mean': th_mean, 'median': th_median, 'min': th_min, 'max': th_max, 'std': th_std},
        'row_metrics': {
            'precision': prec, 'recall': rec, 'f1': f1, 'accuracy': acc,
            'fpr': fpr, 'specificity': spec, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
        },
        'alert_burden': {
            'total_alerts': total_alerts, 'false_alerts': false_alerts,
            'fa_per_1000': fa_per_1000, 'fa_per_shipment': fa_per_shipment
        },
        'event_metrics': ev_res
    }
    
    print(f"\n>>> {s_data['name']} <<<")
    print(f"  [Learned Thresholds]: Mean={th_mean:.3f}, Median={th_median:.3f}, Range=[{th_min:.3f}, {th_max:.3f}] (Std={th_std:.3f})")
    print(f"  [Per-Fold Thresholds]: {s_data['thresholds']}")
    print(f"  [Row Metrics]:        Precision={prec*100:5.2f}% | Recall={rec*100:5.2f}% | F1={f1:.4f} | FPR={fpr*100:5.2f}% | Spec={spec*100:5.2f}%")
    print(f"  [Confusion]:          TP={tp}, FP={fp}, FN={fn}, TN={tn} (Accuracy={acc*100:5.2f}%)")
    print(f"  [False Alert Burden]: Total False Alerts={false_alerts} ({fa_per_shipment:.1f}/shipment, {fa_per_1000:.1f} per 1000 timestamps)")
    print(f"  [Event Detection]:    Events Detected: {ev_res['detected_events']} / {ev_res['total_events']} ({ev_res['detection_rate']:.1f}%) | Missed: {ev_res['missed_events']}")
    print(f"  [Lead Time]:          Median={ev_res['median_lead']:.1f} min | Mean={ev_res['mean_lead']:.1f} min | >=10m: {ev_res['pct_ge_10']:.1f}% | >=20m: {ev_res['pct_ge_20']:.1f}% | >=30m: {ev_res['pct_ge_30']:.1f}%")

# Save complete threshold optimization results
out_meta_path = r"ml_pipeline\models\frostlink_xgb_baseline\threshold_optimization_results.json"

def json_serial(obj):
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Type {type(obj)} not serializable")

with open(out_meta_path, 'w') as f:
    json.dump(strategy_results, f, indent=2, default=json_serial)

print("\n" + "=" * 85)
print("SAVED DATA-DRIVEN THRESHOLD RESULTS TO:", out_meta_path)
print("=" * 85)

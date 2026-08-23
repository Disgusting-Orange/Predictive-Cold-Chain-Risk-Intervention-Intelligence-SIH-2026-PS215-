"""
FrostLink ML Pipeline -- Low-False-Alert Operating-Point Analysis
=================================================================
Evaluates strict False Positive Rate (FPR) constraints under nested LOSO:
- Constraint 1: FPR <= 0.10%
- Constraint 2: FPR <= 0.25%
- Constraint 3: FPR <= 0.50%
- Constraint 4: FPR <= 1.00%
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
        'min_lead': float(np.min(lts_np)) if len(lts_np) > 0 else np.nan,
        'max_lead': float(np.max(lts_np)) if len(lts_np) > 0 else np.nan,
        'pct_ge_10': float((lts_np >= 10).mean() * 100) if len(lts_np) > 0 else np.nan,
        'pct_ge_20': float((lts_np >= 20).mean() * 100) if len(lts_np) > 0 else np.nan,
        'pct_ge_30': float((lts_np >= 30).mean() * 100) if len(lts_np) > 0 else np.nan,
        'pct_ge_45': float((lts_np >= 45).mean() * 100) if len(lts_np) > 0 else np.nan
    }

base_params = {
    'objective': 'binary:logistic', 'eval_metric': 'logloss',
    'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150,
    'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3,
    'random_state': 42, 'n_jobs': -1, 'verbosity': 0
}

# The 4 FPR Constraints
fpr_targets = {
    'FPR_010': {'name': 'FPR <= 0.10% (Ultra-Low False Alarms)', 'target_fpr': 0.0010},
    'FPR_025': {'name': 'FPR <= 0.25% (Very Low False Alarms)',  'target_fpr': 0.0025},
    'FPR_050': {'name': 'FPR <= 0.50% (Low False Alarms)',       'target_fpr': 0.0050},
    'FPR_100': {'name': 'FPR <= 1.00% (Controlled False Alarms)','target_fpr': 0.0100}
}

for c_key in fpr_targets:
    fpr_targets[c_key]['oof'] = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
    fpr_targets[c_key]['oof']['prob'] = np.nan
    fpr_targets[c_key]['oof']['pred'] = np.nan
    fpr_targets[c_key]['thresholds'] = {}

grid_thresholds = np.linspace(0.01, 0.99, 197)

print("=" * 85)
print("RUNNING NESTED LOSO FPR-CONSTRAINED OPTIMIZATION")
print("=" * 85)

for fold_idx, test_sid in enumerate(shipments, 1):
    train_mask = cohort['shipment_id'] != test_sid
    test_mask = cohort['shipment_id'] == test_sid
    train_data = cohort[train_mask].reset_index(drop=True)
    test_data = cohort[test_mask].reset_index(drop=True)
    
    # Inner 5-fold LOSO strictly within training shipments
    inner_sids = sorted(train_data['shipment_id'].unique())
    inner_oof_prob = np.zeros(len(train_data))
    
    for in_sid in inner_sids:
        in_tr = train_data['shipment_id'] != in_sid
        in_te = train_data['shipment_id'] == in_sid
        m_in = xgb.XGBClassifier(**base_params)
        m_in.fit(train_data.loc[in_tr, ALL_FEATURES], train_data.loc[in_tr, TARGET_COL], verbose=False)
        inner_oof_prob[in_te] = m_in.predict_proba(train_data.loc[in_te, ALL_FEATURES])[:, 1]
        
    y_tr_in = train_data[TARGET_COL].values
    
    # Select threshold for each FPR constraint on inner train OOF
    # We evaluate all grid thresholds, filter to those where train FPR <= target_fpr,
    # and pick the threshold that maximizes Recall / F1 under that constraint.
    learned_thresholds_fold = {}
    
    for c_key, c_info in fpr_targets.items():
        t_fpr = c_info['target_fpr']
        best_th = 0.99 # default to highest threshold if constraint never met
        best_rec = -1.0
        best_f1 = -1.0
        min_seen_fpr = 1.0
        th_for_min_fpr = 0.99
        
        for th in grid_thresholds:
            p_bin = (inner_oof_prob >= th).astype(int)
            cm_in = confusion_matrix(y_tr_in, p_bin, labels=[0, 1])
            tn_in, fp_in, fn_in, tp_in = cm_in.ravel()
            fpr_in = fp_in / (fp_in + tn_in) if (fp_in + tn_in) > 0 else 0.0
            rec_in = recall_score(y_tr_in, p_bin, zero_division=0)
            f1_in = f1_score(y_tr_in, p_bin, zero_division=0)
            
            if fpr_in < min_seen_fpr:
                min_seen_fpr = fpr_in
                th_for_min_fpr = th
                
            if fpr_in <= t_fpr and tp_in > 0:
                if rec_in > best_rec or (rec_in == best_rec and f1_in > best_f1):
                    best_rec = rec_in
                    best_f1 = f1_in
                    best_th = th
                    
        # If no positive detections achieved within constraint, fallback to threshold yielding lowest FPR with positive detections
        if best_rec == -1.0:
            best_th = th_for_min_fpr
            
        learned_thresholds_fold[c_key] = best_th
        
    # Fit outer model on all training data
    outer_model = xgb.XGBClassifier(**base_params)
    outer_model.fit(train_data[ALL_FEATURES], train_data[TARGET_COL], verbose=False)
    test_prob = outer_model.predict_proba(test_data[ALL_FEATURES])[:, 1]
    
    print(f"Fold {fold_idx} (Test {test_sid}) | Train Shipments: {inner_sids}")
    for c_key, c_info in fpr_targets.items():
        th_val = learned_thresholds_fold[c_key]
        c_info['thresholds'][test_sid] = th_val
        c_info['oof'].loc[test_mask, 'prob'] = test_prob
        c_info['oof'].loc[test_mask, 'pred'] = (test_prob >= th_val).astype(int)
        print(f"   -> {c_key} ({c_info['name']}): Learned Threshold = {th_val:.3f}")

# Evaluate Aggregate Results
print("\n" + "=" * 85)
print("AGGREGATE UNSEEN-SHIPMENT RESULTS ACROSS ALL 4 FPR CONSTRAINTS")
print("=" * 85)

final_results = {}

for c_key, c_info in fpr_targets.items():
    oof_c = c_info['oof']
    y_true = oof_c[TARGET_COL].values
    y_prob = oof_c['prob'].values
    y_pred = oof_c['pred'].values
    
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
    fa_per_1000 = (false_alerts / len(oof_c)) * 1000.0
    fa_per_shipment = false_alerts / len(shipments)
    
    # Event matching
    ev_res = match_events(oof_c, evaluable_events)
    
    th_list = list(c_info['thresholds'].values())
    th_mean = float(np.mean(th_list))
    th_median = float(np.median(th_list))
    th_min = float(np.min(th_list))
    th_max = float(np.max(th_list))
    th_std = float(np.std(th_list))
    
    final_results[c_key] = {
        'name': c_info['name'],
        'target_fpr': c_info['target_fpr'],
        'thresholds': c_info['thresholds'],
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
    
    print(f"\n================================================================================")
    print(f"RESULTS FOR {c_info['name']}")
    print(f"================================================================================")
    print(f"  [Learned Thresholds]: Mean={th_mean:.3f}, Median={th_median:.3f}, Min={th_min:.3f}, Max={th_max:.3f}, Std={th_std:.3f}")
    print(f"  [Per-Fold Thresholds]: {c_info['thresholds']}")
    print(f"  [Row Metrics]:        Precision={prec*100:5.2f}% | Recall={rec*100:5.2f}% | F1={f1:.4f} | FPR={fpr*100:5.3f}% | Spec={spec*100:5.2f}%")
    print(f"  [Confusion Matrix]:   TP={tp:3d}, FP={fp:3d}, FN={fn:3d}, TN={tn:4d} (Accuracy={acc*100:5.2f}%)")
    print(f"  [False Alert Burden]: Total Alerts={total_alerts} | False Alerts={false_alerts} ({fa_per_shipment:.1f}/shipment, {fa_per_1000:.2f} per 1,000 timestamps)")
    print(f"  [Physical Events]:    Detected: {ev_res['detected_events']} / {ev_res['total_events']} ({ev_res['detection_rate']:.1f}%) | Missed: {ev_res['missed_events']}")
    print(f"  [Lead Time]:          Median={ev_res['median_lead']:.1f} min | Mean={ev_res['mean_lead']:.1f} min | Range={ev_res['min_lead']:.1f} - {ev_res['max_lead']:.1f} min")
    print(f"                        >=10m: {ev_res['pct_ge_10']:.1f}% | >=20m: {ev_res['pct_ge_20']:.1f}% | >=30m: {ev_res['pct_ge_30']:.1f}% | >=45m: {ev_res['pct_ge_45']:.1f}%")

# Save complete JSON
out_path = r"ml_pipeline\models\frostlink_xgb_baseline\low_false_alert_results.json"
def json_serial(obj):
    if isinstance(obj, (np.integer, np.int64, np.int32)): return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)): return float(obj)
    elif isinstance(obj, np.ndarray): return obj.tolist()
    raise TypeError(f"Type {type(obj)} not serializable")

with open(out_path, 'w') as f:
    json.dump(final_results, f, indent=2, default=json_serial)

print("\n" + "=" * 85)
print("SAVED LOW-FALSE-ALERT RESULTS TO:", out_path)
print("=" * 85)

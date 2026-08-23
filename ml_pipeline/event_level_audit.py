"""
FrostLink ML Pipeline -- Event-Level Early-Warning Audit
========================================================
Authoritative script to:
1. Segment continuous physical excursion episodes (R2) in the raw time series.
2. Group model predictions into alert episodes.
3. Perform strict 1-to-1 matching between alerts and physical events within the 60-minute horizon.
4. Calculate true event-level detection rates and lead-time distributions.
5. Contrast row-level classification metrics vs. event-level detection metrics across all models.
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

# 1. Ingestion & Full Time Series Setup
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

# ============================================================
# STEP 1: IDENTIFY ACTUAL PHYSICAL EXCURSION EPISODES
# ============================================================
print("=" * 80)
print("STEP 1: IDENTIFYING ACTUAL PHYSICAL EXCURSION EPISODES (R2)")
print("=" * 80)

actual_events = []
event_global_id = 1

for sid in shipments:
    ship_data = df[df['shipment_id'] == sid].sort_values('Time_dt').reset_index(drop=True)
    is_r2 = (ship_data['risk_level'] == 2.0).astype(int)
    
    # Identify transitions into R2: current is R2 and previous was NOT R2
    onsets = ship_data[(is_r2 == 1) & (is_r2.shift(1, fill_value=0) == 0)].index
    
    ship_events_count = 0
    for onset_idx in onsets:
        start_time = ship_data.loc[onset_idx, 'Time_dt']
        
        # Find where this R2 episode ends (next non-R2 or end of shipment)
        end_idx = onset_idx
        while end_idx + 1 < len(ship_data) and is_r2.iloc[end_idx + 1] == 1:
            end_idx += 1
        end_time = ship_data.loc[end_idx, 'Time_dt']
        duration_min = (end_time - start_time).total_seconds() / 60.0 + 10.0 # inclusive
        
        # Check if there is prior history in cohort to make an early warning prediction
        # (i.e. was there at least one non-R2 observation in the 60 minutes prior?)
        prior_window_start = start_time - pd.Timedelta(minutes=60)
        prior_cohort_rows = cohort[(cohort['shipment_id'] == sid) & 
                                   (cohort['Time_dt'] >= prior_window_start) & 
                                   (cohort['Time_dt'] < start_time)]
        has_evaluable_pre_window = len(prior_cohort_rows) > 0
        
        event_dict = {
            'event_id': event_global_id,
            'shipment_id': sid,
            'start_idx': onset_idx,
            'end_idx': end_idx,
            'start_time': start_time,
            'end_time': end_time,
            'duration_min': duration_min,
            'n_r2_steps': end_idx - onset_idx + 1,
            'has_evaluable_pre_window': has_evaluable_pre_window,
            'n_pre_window_cohort_rows': len(prior_cohort_rows)
        }
        actual_events.append(event_dict)
        event_global_id += 1
        ship_events_count += 1
        
    print(f"Shipment {sid}: {ship_events_count} unique excursion episodes identified.")

events_df = pd.DataFrame(actual_events)
print(f"\nTOTAL UNIQUE EXCURSION EPISODES ACROSS FLEET: {len(events_df)}")
print(f"Total Unique Episodes with Pre-Onset Evaluated Observations (within 60m): {events_df['has_evaluable_pre_window'].sum()} / {len(events_df)}")

print("\n--- Detailed Breakdown of Evaluated Physical Excursion Episodes ---")
evaluable_events = events_df[events_df['has_evaluable_pre_window']].copy().reset_index(drop=True)
for _, ev in evaluable_events.iterrows():
    print(f"  Event #{ev['event_id']:2d} ({ev['shipment_id']}): Start = {ev['start_time']}, Duration = {ev['duration_min']:5.0f} min ({ev['n_r2_steps']} steps), Pre-onset non-R2 rows = {ev['n_pre_window_cohort_rows']}")


# ============================================================
# STEP 2 & 3: TRAIN MODELS & EXTRACT OUT-OF-FOLD ALERT EPISODES
# ============================================================
print("\n" + "=" * 80)
print("STEP 2 & 3: OUT-OF-FOLD PREDICTIONS & EVENT MATCHING ACROSS 4 MODELS")
print("=" * 80)

model_definitions = {
    '1. Original Baseline': {
        'params': {'objective': 'binary:logistic', 'eval_metric': 'logloss', 'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3, 'random_state': 42, 'n_jobs': -1, 'verbosity': 0},
        'use_spw': False,
        'thresh_mode': 'fixed_0.5'
    },
    '2. Class-Weighted Model': {
        'params': {'objective': 'binary:logistic', 'eval_metric': 'logloss', 'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3, 'random_state': 42, 'n_jobs': -1, 'verbosity': 0},
        'use_spw': True,
        'thresh_mode': 'fixed_0.5'
    },
    '3. Threshold-Optimized Model': {
        'params': {'objective': 'binary:logistic', 'eval_metric': 'logloss', 'max_depth': 4, 'learning_rate': 0.05, 'n_estimators': 150, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3, 'random_state': 42, 'n_jobs': -1, 'verbosity': 0},
        'use_spw': False,
        'thresh_mode': 'train_f1_opt'
    },
    '4. Capacity Config B Model': {
        'params': {'objective': 'binary:logistic', 'eval_metric': 'logloss', 'max_depth': 4, 'learning_rate': 0.03, 'n_estimators': 300, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 2, 'random_state': 42, 'n_jobs': -1, 'verbosity': 0},
        'use_spw': False,
        'thresh_mode': 'fixed_0.5'
    }
}

audit_summary = []

for m_name, m_spec in model_definitions.items():
    oof_m = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
    oof_m['prob'] = np.nan
    oof_m['pred'] = np.nan
    
    # Run LOSO
    for fold_idx, test_sid in enumerate(shipments, 1):
        train_mask = cohort['shipment_id'] != test_sid
        test_mask = cohort['shipment_id'] == test_sid
        train_data = cohort[train_mask].reset_index(drop=True)
        test_data = cohort[test_mask].reset_index(drop=True)
        
        p = dict(m_spec['params'])
        if m_spec['use_spw']:
            spw = (train_data[TARGET_COL] == 0).sum() / (train_data[TARGET_COL] == 1).sum()
            p['scale_pos_weight'] = spw
            
        threshold = 0.50
        if m_spec['thresh_mode'] == 'train_f1_opt':
            inner_sids = sorted(train_data['shipment_id'].unique())
            inner_prob = np.zeros(len(train_data))
            for in_sid in inner_sids:
                in_tr = train_data['shipment_id'] != in_sid
                in_te = train_data['shipment_id'] == in_sid
                m_in = xgb.XGBClassifier(**p)
                m_in.fit(train_data.loc[in_tr, ALL_FEATURES], train_data.loc[in_tr, TARGET_COL], verbose=False)
                inner_prob[in_te] = m_in.predict_proba(train_data.loc[in_te, ALL_FEATURES])[:, 1]
            
            best_th = 0.5
            best_f1 = -1
            for th in np.linspace(0.05, 0.60, 100):
                f1_c = f1_score(train_data[TARGET_COL], (inner_prob >= th).astype(int), zero_division=0)
                if f1_c > best_f1:
                    best_f1 = f1_c
                    best_th = th
            threshold = best_th
            
        model = xgb.XGBClassifier(**p)
        model.fit(train_data[ALL_FEATURES], train_data[TARGET_COL], verbose=False)
        
        test_prob = model.predict_proba(test_data[ALL_FEATURES])[:, 1]
        test_pred = (test_prob >= threshold).astype(int)
        
        oof_m.loc[test_mask, 'prob'] = test_prob
        oof_m.loc[test_mask, 'pred'] = test_pred
        
    # ROW-LEVEL METRICS
    y_true_row = oof_m[TARGET_COL].values
    y_pred_row = oof_m['pred'].values
    y_prob_row = oof_m['prob'].values
    
    row_prec = precision_score(y_true_row, y_pred_row, zero_division=0)
    row_rec = recall_score(y_true_row, y_pred_row, zero_division=0)
    row_f1 = f1_score(y_true_row, y_pred_row, zero_division=0)
    row_prauc = average_precision_score(y_true_row, y_prob_row)
    row_rocauc = roc_auc_score(y_true_row, y_prob_row)
    row_acc = accuracy_score(y_true_row, y_pred_row)
    row_cm = confusion_matrix(y_true_row, y_pred_row, labels=[0, 1])
    tn, fp, fn, tp = row_cm.ravel()
    
    # EVENT-LEVEL MATCHING
    detected_events = []
    missed_events = []
    lead_times = []
    
    for _, ev in evaluable_events.iterrows():
        sid = ev['shipment_id']
        start_time = ev['start_time']
        window_start = start_time - pd.Timedelta(minutes=60)
        
        pre_preds = oof_m[(oof_m['shipment_id'] == sid) & 
                          (oof_m['Time_dt'] >= window_start) & 
                          (oof_m['Time_dt'] < start_time)]
        
        alarms = pre_preds[pre_preds['pred'] == 1]
        
        if len(alarms) > 0:
            first_alarm = alarms['Time_dt'].min()
            lead_m = (start_time - first_alarm).total_seconds() / 60.0
            lead_times.append(lead_m)
            detected_events.append({
                'event_id': ev['event_id'],
                'shipment_id': sid,
                'start_time': start_time,
                'first_alarm_time': first_alarm,
                'lead_time_min': lead_m,
                'n_alarms_in_window': len(alarms)
            })
        else:
            missed_events.append({
                'event_id': ev['event_id'],
                'shipment_id': sid,
                'start_time': start_time
            })
            
    n_eval_events = len(evaluable_events)
    n_detected = len(detected_events)
    n_missed = len(missed_events)
    event_det_rate = (n_detected / n_eval_events) * 100.0 if n_eval_events > 0 else 0.0
    
    lts_np = np.array(lead_times)
    mean_lt = float(np.mean(lts_np)) if len(lts_np) > 0 else np.nan
    median_lt = float(np.median(lts_np)) if len(lts_np) > 0 else np.nan
    min_lt = float(np.min(lts_np)) if len(lts_np) > 0 else np.nan
    max_lt = float(np.max(lts_np)) if len(lts_np) > 0 else np.nan
    
    pct_ge_10 = float((lts_np >= 10).mean() * 100) if len(lts_np) > 0 else np.nan
    pct_ge_20 = float((lts_np >= 20).mean() * 100) if len(lts_np) > 0 else np.nan
    pct_ge_30 = float((lts_np >= 30).mean() * 100) if len(lts_np) > 0 else np.nan
    pct_ge_45 = float((lts_np >= 45).mean() * 100) if len(lts_np) > 0 else np.nan
    
    res = {
        'model_name': m_name,
        # Row-level
        'row_prec': row_prec, 'row_rec': row_rec, 'row_f1': row_f1,
        'row_prauc': row_prauc, 'row_rocauc': row_rocauc, 'row_acc': row_acc,
        'row_tp': tp, 'row_fp': fp, 'row_fn': fn, 'row_tn': tn,
        # Event-level
        'total_actual_events': n_eval_events,
        'detected_events': n_detected,
        'missed_events': n_missed,
        'event_detection_rate': event_det_rate,
        'median_lead_min': median_lt,
        'mean_lead_min': mean_lt,
        'min_lead_min': min_lt,
        'max_lead_min': max_lt,
        'pct_ge_10': pct_ge_10,
        'pct_ge_20': pct_ge_20,
        'pct_ge_30': pct_ge_30,
        'pct_ge_45': pct_ge_45,
        'detected_details': detected_events,
        'missed_details': missed_events
    }
    audit_summary.append(res)

print("\n" + "=" * 80)
print("AUDIT RESULTS SUMMARY ACROSS ALL MODELS")
print("=" * 80)
for r in audit_summary:
    print(f"\n>>> {r['model_name']} <<<")
    print(f"  [ROW-LEVEL]   Recall: {r['row_rec']*100:5.2f}% | Precision: {r['row_prec']*100:5.2f}% | F1: {r['row_f1']:.4f} | PR-AUC: {r['row_prauc']:.4f} | TP={r['row_tp']}, FP={r['row_fp']}, FN={r['row_fn']}")
    print(f"  [EVENT-LEVEL] Detected Events: {r['detected_events']} / {r['total_actual_events']} ({r['event_detection_rate']:.1f}%) | Missed Events: {r['missed_events']}")
    print(f"  [LEAD TIME]   Median: {r['median_lead_min']:.1f} min | Mean: {r['mean_lead_min']:.1f} min | Range: {r['min_lead_min']:.1f} - {r['max_lead_min']:.1f} min")
    print(f"                >=10m: {r['pct_ge_10']:.1f}% | >=20m: {r['pct_ge_20']:.1f}% | >=30m: {r['pct_ge_30']:.1f}% | >=45m: {r['pct_ge_45']:.1f}%")

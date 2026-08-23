"""
FrostLink ML Pipeline -- Phase 3 to 5: Empirical Baseline Implementation
========================================================================
Authoritative, reproducible execution script.
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
from datetime import datetime
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score,
    confusion_matrix, brier_score_loss, accuracy_score
)
import xgboost as xgb

# 1. Ingestion & Deduplication
train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
raw_df = pd.concat([train_df, test_df], ignore_index=True)
raw_df['Time_dt'] = pd.to_datetime(raw_df['Time'])

df = raw_df.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)

# 2. Population & Target
TARGET_COL = 'y_next_60_R2'
cohort = df[df['risk_level'].isin([0.0, 1.0]) & df[TARGET_COL].notna()].copy().reset_index(drop=True)

# 3. Whitelisted Features
FEATURE_NAMES = [
    'T_mean_t', 'spatial_range_t', 'spatial_std_t', 'hot_ratio_t', 'cold_ratio_t', 'mask_ratio_t',
    'W60_T_mean', 'W60_T_std', 'W60_T_min', 'W60_T_max', 'W60_T_range', 'W60_delta', 'W60_slope',
    'W60_spatial_range_mean', 'W60_spatial_range_max', 'W60_spatial_std_mean',
    'W60_hot_ratio_mean', 'W60_hot_ratio_max', 'W60_over_auc_mean', 'W60_over_auc_max',
    'W60_under_auc_mean', 'W60_under_auc_max', 'W60_over_dur_mean', 'W60_under_dur_mean',
    'v4_slope_short_t', 'v4_slope_long_t', 'v4_accel_t', 'v4_shock_t', 'v4_median_t',
    'v4_iqr_t', 'v4_p90_t', 'v4_p95_t', 'v4_over_auc_t', 'v4_under_auc_t', 'v4_over_max_t', 'v4_under_max_t',
    'sconf', 'coverage_points', 'coverage_time', 'N_valid'
]

# 4. LOSO 6-Fold Cross-Validation
shipments = sorted(cohort['shipment_id'].unique())
xgb_params = {
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'max_depth': 4,
    'learning_rate': 0.05,
    'n_estimators': 150,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 3,
    'random_state': 42,
    'n_jobs': -1,
    'verbosity': 0
}

fold_records = []
oof_df = cohort[['shipment_id', 'Time_dt', TARGET_COL]].copy()
oof_df['prob'] = np.nan
oof_df['pred'] = np.nan

for fold_idx, test_sid in enumerate(shipments, 1):
    train_mask = cohort['shipment_id'] != test_sid
    test_mask = cohort['shipment_id'] == test_sid
    
    train_sids = sorted(cohort.loc[train_mask, 'shipment_id'].unique())
    test_sids = [test_sid]
    
    X_train = cohort.loc[train_mask, FEATURE_NAMES]
    y_train = cohort.loc[train_mask, TARGET_COL]
    X_test = cohort.loc[test_mask, FEATURE_NAMES]
    y_test = cohort.loc[test_mask, TARGET_COL]
    
    # Fit model on training shipments only
    model = xgb.XGBClassifier(**xgb_params)
    model.fit(X_train, y_train, verbose=False)
    
    prob = model.predict_proba(X_test)[:, 1]
    pred = (prob >= 0.5).astype(int)
    
    oof_df.loc[test_mask, 'prob'] = prob
    oof_df.loc[test_mask, 'pred'] = pred
    
    # Calculate fold metrics
    prec = precision_score(y_test, pred, zero_division=0)
    rec = recall_score(y_test, pred, zero_division=0)
    f1 = f1_score(y_test, pred, zero_division=0)
    roc = roc_auc_score(y_test, prob) if len(np.unique(y_test)) > 1 else np.nan
    pr = average_precision_score(y_test, prob) if len(np.unique(y_test)) > 1 else np.nan
    acc = accuracy_score(y_test, pred)
    brier = brier_score_loss(y_test, prob)
    cm = confusion_matrix(y_test, pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    train_pos = int(y_train.sum())
    train_neg = int((y_train == 0).sum())
    test_pos = int(y_test.sum())
    test_neg = int((y_test == 0).sum())
    
    fold_records.append({
        'fold': fold_idx,
        'test_shipment': test_sid,
        'train_shipments': train_sids,
        'train_rows': len(X_train),
        'test_rows': len(X_test),
        'train_pos': train_pos,
        'train_neg': train_neg,
        'test_pos': test_pos,
        'test_neg': test_neg,
        'precision': float(prec),
        'recall': float(rec),
        'f1': float(f1),
        'roc_auc': float(roc),
        'pr_auc': float(pr),
        'accuracy': float(acc),
        'brier_score': float(brier),
        'tp': int(tp),
        'fp': int(fp),
        'fn': int(fn),
        'tn': int(tn)
    })

# 5. Overall Out-of-Fold Metrics
y_all = oof_df[TARGET_COL].values
p_all = oof_df['prob'].values
pred_all = oof_df['pred'].values

overall_acc = accuracy_score(y_all, pred_all)
overall_prec = precision_score(y_all, pred_all, zero_division=0)
overall_rec = recall_score(y_all, pred_all, zero_division=0)
overall_f1 = f1_score(y_all, pred_all, zero_division=0)
overall_roc = roc_auc_score(y_all, p_all)
overall_pr = average_precision_score(y_all, p_all)
overall_brier = brier_score_loss(y_all, p_all)
overall_cm = confusion_matrix(y_all, pred_all, labels=[0, 1])
tot_tn, tot_fp, tot_fn, tot_tp = overall_cm.ravel()

# 6. Early-Warning Lead Time Calculation
lead_times = []
for sid in shipments:
    ship_raw = df[df['shipment_id'] == sid].sort_values('Time_dt').reset_index(drop=True)
    ship_oof = oof_df[oof_df['shipment_id'] == sid].set_index('Time_dt')
    
    # Identify R2 onset points
    is_r2 = (ship_raw['risk_level'] == 2.0).astype(int)
    r2_onsets = ship_raw[(is_r2 == 1) & (is_r2.shift(1, fill_value=0) == 0)]
    
    for idx in r2_onsets.index:
        onset_time = ship_raw.loc[idx, 'Time_dt']
        window_start = onset_time - pd.Timedelta(minutes=60)
        pre_preds = ship_oof.loc[(ship_oof.index >= window_start) & (ship_oof.index < onset_time)]
        alarms = pre_preds[pre_preds['prob'] >= 0.5]
        if len(alarms) > 0:
            first_alarm = alarms.index.min()
            lead_m = (onset_time - first_alarm).total_seconds() / 60.0
            lead_times.append(lead_m)

lead_times_np = np.array(lead_times)
mean_lead = float(np.mean(lead_times_np)) if len(lead_times_np) > 0 else np.nan
median_lead = float(np.median(lead_times_np)) if len(lead_times_np) > 0 else np.nan
min_lead = float(np.min(lead_times_np)) if len(lead_times_np) > 0 else np.nan
max_lead = float(np.max(lead_times_np)) if len(lead_times_np) > 0 else np.nan
pct_ge_10 = float((lead_times_np >= 10).mean() * 100) if len(lead_times_np) > 0 else np.nan
pct_ge_20 = float((lead_times_np >= 20).mean() * 100) if len(lead_times_np) > 0 else np.nan
pct_ge_30 = float((lead_times_np >= 30).mean() * 100) if len(lead_times_np) > 0 else np.nan
pct_ge_45 = float((lead_times_np >= 45).mean() * 100) if len(lead_times_np) > 0 else np.nan

# 7. Print Authoritative Results
print("\n" + "=" * 80)
print("FROSTLINK ML PIPELINE -- BASELINE EVALUATION REPORT")
print("=" * 80)

print(f"RAW ROWS:                 {len(raw_df)}")
print(f"DEDUPLICATED ROWS:        {len(df)}")
print(f"FINAL USABLE ROWS:        {len(cohort)}")
print(f"POSITIVE:                 {int(y_all.sum())}")
print(f"NEGATIVE:                 {int((y_all == 0).sum())}")
print(f"POSITIVE RATE:            {float(y_all.mean()*100):.2f}%")
print(f"NUMBER OF SHIPMENTS:      {len(shipments)}")
print(f"NUMBER OF FEATURES:       {len(FEATURE_NAMES)}")

print("\n--- PER FOLD VALIDATION RESULTS ---")
for r in fold_records:
    print(f"Fold {r['fold']} | Test: {r['test_shipment']} (Rows: {r['test_rows']}, Pos: {r['test_pos']}, Neg: {r['test_neg']}) | Train: {r['train_shipments']} (Rows: {r['train_rows']})")
    print(f"       Prec: {r['precision']:.4f}, Rec: {r['recall']:.4f}, F1: {r['f1']:.4f}, PR-AUC: {r['pr_auc']:.4f}, ROC-AUC: {r['roc_auc']:.4f}, Acc: {r['accuracy']:.4f} | TP={r['tp']}, FP={r['fp']}, FN={r['fn']}, TN={r['tn']}")

print("\n--- OVERALL OUT-OF-FOLD METRICS ---")
print(f"PR-AUC:                   {overall_pr:.4f} (Baseline positive rate = {float(y_all.mean()):.4f})")
print(f"ROC-AUC:                  {overall_roc:.4f}")
print(f"PRECISION:                {overall_prec:.4f} ({overall_prec*100:.2f}%)")
print(f"RECALL:                   {overall_rec:.4f} ({overall_rec*100:.2f}%)")
print(f"F1:                       {overall_f1:.4f}")
print(f"ACCURACY:                 {overall_acc:.4f} ({overall_acc*100:.2f}%)")
print(f"CONFUSION MATRIX:         TP={tot_tp}, FP={tot_fp}, FN={tot_fn}, TN={tot_tn}")

print("\n--- EARLY WARNING LEAD TIME ---")
print(f"DETECTED ONSET EVENTS:    {len(lead_times)}")
print(f"MEDIAN LEAD TIME:         {median_lead:.1f} min")
print(f"MEAN LEAD TIME:           {mean_lead:.1f} min")
print(f"% >= 10 MIN:              {pct_ge_10:.1f}%")
print(f"% >= 20 MIN:              {pct_ge_20:.1f}%")
print(f"% >= 30 MIN:              {pct_ge_30:.1f}%")
print(f"% >= 45 MIN:              {pct_ge_45:.1f}%")

# Save outputs
out_dir = r"ml_pipeline\models\frostlink_xgb_baseline"
os.makedirs(out_dir, exist_ok=True)

# Train full model on cohort and save
full_model = xgb.XGBClassifier(**xgb_params)
full_model.fit(cohort[FEATURE_NAMES], cohort[TARGET_COL], verbose=False)
full_model.save_model(os.path.join(out_dir, "model.json"))

with open(os.path.join(out_dir, "features.json"), 'w') as f:
    json.dump({'features': FEATURE_NAMES}, f, indent=2)

with open(os.path.join(out_dir, "metadata.json"), 'w') as f:
    json.dump({
        'model_name': 'FrostLink_XGBoost_Baseline',
        'version': '1.0.0',
        'population': 'Early-Warning Non-Excursion Cohort (risk_level in [0, 1])',
        'target': TARGET_COL,
        'features': FEATURE_NAMES,
        'metrics_oof': {
            'accuracy': overall_acc,
            'precision': overall_prec,
            'recall': overall_rec,
            'f1': overall_f1,
            'pr_auc': overall_pr,
            'roc_auc': overall_roc,
            'brier_score': overall_brier,
            'confusion_matrix': {'tp': int(tot_tp), 'fp': int(tot_fp), 'fn': int(tot_fn), 'tn': int(tot_tn)}
        },
        'lead_time_minutes': {
            'events_detected': len(lead_times),
            'mean': mean_lead,
            'median': median_lead,
            'pct_ge_10': pct_ge_10,
            'pct_ge_20': pct_ge_20,
            'pct_ge_30': pct_ge_30,
            'pct_ge_45': pct_ge_45
        },
        'fold_results': fold_records
    }, f, indent=2)

print("\nModel artifacts and metadata written to:", out_dir)

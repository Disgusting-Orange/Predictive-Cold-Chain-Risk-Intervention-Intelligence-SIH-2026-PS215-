"""
FrostLink ML Pipeline -- Synthetic Augmentation Experiment (Phase 9)
====================================================================
Executes:
1. Target and Feature Alignment between Real Strawberry and Synthetic Fleet.
2. Model A: Real Only (Baseline).
3. Model B: Synthetic Only (Trained on synthetic, evaluated on REAL test).
4. Model C: Hybrid (Real + Synthetic at 0.25x, 0.50x, 1.0x, 2.0x ratios).
5. Nested LOSO threshold selection on training data.
6. 1-to-1 Event-level detection rate and lead-time analysis.
7. Scenario-held-out out-of-distribution generalization test.
8. Feature importance sanity check.
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

# ============================================================
# 1. LOAD & PREPARE REAL DATASET
# ============================================================
print("=" * 80)
print("STEP 1: LOADING & ALIGNING REAL & SYNTHETIC DATASETS")
print("=" * 80)

train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
raw_real = pd.concat([train_df, test_df], ignore_index=True)
raw_real['Time_dt'] = pd.to_datetime(raw_real['Time'])

real_df = raw_real.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)
TARGET_COL = 'y_next_60_R2'

# Real non-excursion cohort
real_cohort = real_df[real_df['risk_level'].isin([0.0, 1.0]) & real_df[TARGET_COL].notna()].copy().reset_index(drop=True)
real_shipments = sorted(real_df['shipment_id'].unique())

# ============================================================
# 2. LOAD & PREPARE SYNTHETIC DATASET
# ============================================================
synth_raw = pd.read_csv(r"ml_pipeline\synthetic\data\synthetic_fleet_100.csv")
synth_raw['Time_dt'] = pd.to_datetime(synth_raw['Time'])
synth_raw = synth_raw.sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)

# Synthetic non-excursion cohort (risk_level in [0, 1] and target non-null)
synth_cohort = synth_raw[synth_raw['risk_level'].isin([0.0, 1.0]) & synth_raw[TARGET_COL].notna()].copy().reset_index(drop=True)
synth_shipments = sorted(synth_raw['shipment_id'].unique())

print(f"Real Cohort:      {len(real_cohort)} rows across {len(real_shipments)} shipments (Positives: {(real_cohort[TARGET_COL]==1).sum()})")
print(f"Synthetic Cohort: {len(synth_cohort)} rows across {len(synth_shipments)} shipments (Positives: {(synth_cohort[TARGET_COL]==1).sum()})")

# ============================================================
# 3. FEATURE ALIGNMENT
# ============================================================
# Construct aligned thermal & temporal features for both datasets
# In Real data: T_mean_t is the primary cargo temperature
# In Synthetic data: observed_temp is the primary cargo temperature

# Compute 60-min backward rolling features on synthetic data to match real W60_* features
def compute_aligned_features(df_input, temp_col):
    df_out = df_input.copy()
    grouped = df_out.groupby('shipment_id')
    
    # 60m backward rolling window (6 steps of 10 min, including current step t)
    # W60_mean, W60_min, W60_max, W60_std, W60_delta, W60_slope
    df_out['feat_T_current'] = df_out[temp_col]
    df_out['feat_W60_mean'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).mean())
    df_out['feat_W60_min'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).min())
    df_out['feat_W60_max'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).max())
    df_out['feat_W60_std'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).std().fillna(0.0))
    df_out['feat_W60_range'] = df_out['feat_W60_max'] - df_out['feat_W60_min']
    
    # 60m Delta: T(t) - T(t-50m)
    df_out['feat_W60_delta'] = grouped[temp_col].transform(lambda x: x - x.shift(5).fillna(x.iloc[0]))
    # 60m Slope: Delta / 50 min
    df_out['feat_W60_slope'] = df_out['feat_W60_delta'] / 50.0
    
    # 10m instantaneous delta and slope
    df_out['feat_10m_delta'] = grouped[temp_col].transform(lambda x: x.diff().fillna(0.0))
    df_out['feat_10m_slope'] = df_out['feat_10m_delta'] / 10.0
    
    # 20m instantaneous acceleration: slope(t) - slope(t-10m)
    df_out['feat_accel'] = grouped['feat_10m_slope'].transform(lambda x: x.diff().fillna(0.0))
    
    feature_cols = [
        'feat_T_current', 'feat_W60_mean', 'feat_W60_min', 'feat_W60_max',
        'feat_W60_std', 'feat_W60_range', 'feat_W60_delta', 'feat_W60_slope',
        'feat_10m_delta', 'feat_10m_slope', 'feat_accel'
    ]
    return df_out, feature_cols

real_proc, ALIGNED_FEATURES = compute_aligned_features(real_df, 'T_mean_t')
synth_proc, _ = compute_aligned_features(synth_raw, 'observed_temp')

real_cohort_proc = real_proc[real_proc['risk_level'].isin([0.0, 1.0]) & real_proc[TARGET_COL].notna()].copy().reset_index(drop=True)
synth_cohort_proc = synth_proc[synth_proc['risk_level'].isin([0.0, 1.0]) & synth_proc[TARGET_COL].notna()].copy().reset_index(drop=True)

print(f"Aligned Features ({len(ALIGNED_FEATURES)}): {ALIGNED_FEATURES}")

# ============================================================
# 4. PHYSICAL EVENT EXTRACTION FOR 1-TO-1 EVENT MATCHING
# ============================================================
actual_events = []
event_global_id = 1
for sid in real_shipments:
    ship_data = real_df[real_df['shipment_id'] == sid].sort_values('Time_dt').reset_index(drop=True)
    is_r2 = (ship_data['risk_level'] == 2.0).astype(int)
    onsets = ship_data[(is_r2 == 1) & (is_r2.shift(1, fill_value=0) == 0)].index
    
    for onset_idx in onsets:
        start_time = ship_data.loc[onset_idx, 'Time_dt']
        end_idx = onset_idx
        while end_idx + 1 < len(ship_data) and is_r2.iloc[end_idx + 1] == 1:
            end_idx += 1
        end_time = ship_data.loc[end_idx, 'Time_dt']
        
        prior_window_start = start_time - pd.Timedelta(minutes=60)
        prior_cohort = real_cohort_proc[(real_cohort_proc['shipment_id'] == sid) & 
                                        (real_cohort_proc['Time_dt'] >= prior_window_start) & 
                                        (real_cohort_proc['Time_dt'] < start_time)]
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

# ============================================================
# 5. EXPERIMENT RUNNER: MODEL A, B, C (Various Ratios)
# ============================================================
print("\n" + "=" * 80)
print("STEP 2: RUNNING MODELS A, B, AND HYBRID C EXPERIMENTS")
print("=" * 80)

# Experiment configurations
experiments = {
    'Model_A_Real_Only': {'name': 'Model A: Real Only (Ratio 0.0x)', 'synth_ratio': 0.0},
    'Model_C_Hybrid_025': {'name': 'Model C: Hybrid (0.25x Synthetic)', 'synth_ratio': 0.25},
    'Model_C_Hybrid_050': {'name': 'Model C: Hybrid (0.50x Synthetic)', 'synth_ratio': 0.50},
    'Model_C_Hybrid_100': {'name': 'Model C: Hybrid (1.00x Synthetic)', 'synth_ratio': 1.00},
    'Model_C_Hybrid_200': {'name': 'Model C: Hybrid (2.00x Synthetic)', 'synth_ratio': 2.00},
    'Model_B_Synth_Only': {'name': 'Model B: Synthetic Only (Trained on 100% Synth, Tested on Real)', 'synth_ratio': 'only'}
}

results_manifest = {}

for exp_key, exp_info in experiments.items():
    oof_pred_df = real_cohort_proc[['shipment_id', 'Time_dt', TARGET_COL]].copy()
    oof_pred_df['prob'] = np.nan
    oof_pred_df['pred'] = np.nan
    per_fold_thresholds = {}
    
    # Outer LOSO Loop over the 6 real shipments
    for fold_idx, test_sid in enumerate(real_shipments, 1):
        real_tr_mask = real_cohort_proc['shipment_id'] != test_sid
        real_te_mask = real_cohort_proc['shipment_id'] == test_sid
        
        real_train = real_cohort_proc[real_tr_mask].reset_index(drop=True)
        real_test = real_cohort_proc[real_te_mask].reset_index(drop=True)
        
        # Build training set for this fold
        if exp_info['synth_ratio'] == 'only':
            # Model B: Trained solely on synthetic data
            X_train = synth_cohort_proc[ALIGNED_FEATURES]
            y_train = synth_cohort_proc[TARGET_COL]
        else:
            ratio = exp_info['synth_ratio']
            if ratio == 0.0:
                # Model A: Real only
                X_train = real_train[ALIGNED_FEATURES]
                y_train = real_train[TARGET_COL]
            else:
                # Model C: Real + stratified synthetic sample
                n_real_train = len(real_train)
                n_synth_sample = int(n_real_train * ratio)
                # Sample balanced across synthetic shipments
                synth_sample = synth_cohort_proc.sample(n=n_synth_sample, random_state=42 + fold_idx, replace=False)
                
                comb_train = pd.concat([real_train, synth_sample], ignore_index=True)
                X_train = comb_train[ALIGNED_FEATURES]
                y_train = comb_train[TARGET_COL]
                
        # Inner validation on training data to learn threshold (F1-max strategy)
        # For real training data: inner 5-fold LOSO across the 5 real training shipments
        inner_sids = sorted(real_train['shipment_id'].unique())
        inner_oof_prob = np.zeros(len(real_train))
        
        for in_sid in inner_sids:
            in_tr_m = real_train['shipment_id'] != in_sid
            in_te_m = real_train['shipment_id'] == in_sid
            
            if exp_info['synth_ratio'] == 'only':
                # Inner model uses synthetic data
                m_in = xgb.XGBClassifier(**base_params)
                m_in.fit(synth_cohort_proc[ALIGNED_FEATURES], synth_cohort_proc[TARGET_COL], verbose=False)
                inner_oof_prob[in_te_m] = m_in.predict_proba(real_train.loc[in_te_m, ALIGNED_FEATURES])[:, 1]
            elif exp_info['synth_ratio'] == 0.0:
                m_in = xgb.XGBClassifier(**base_params)
                m_in.fit(real_train.loc[in_tr_m, ALIGNED_FEATURES], real_train.loc[in_tr_m, TARGET_COL], verbose=False)
                inner_oof_prob[in_te_m] = m_in.predict_proba(real_train.loc[in_te_m, ALIGNED_FEATURES])[:, 1]
            else:
                n_in_tr = in_tr_m.sum()
                n_s_in = int(n_in_tr * exp_info['synth_ratio'])
                s_sample_in = synth_cohort_proc.sample(n=n_s_in, random_state=42 + fold_idx, replace=False)
                c_in_tr = pd.concat([real_train[in_tr_m], s_sample_in], ignore_index=True)
                m_in = xgb.XGBClassifier(**base_params)
                m_in.fit(c_in_tr[ALIGNED_FEATURES], c_in_tr[TARGET_COL], verbose=False)
                inner_oof_prob[in_te_m] = m_in.predict_proba(real_train.loc[in_te_m, ALIGNED_FEATURES])[:, 1]
                
        # Find F1-maximizing threshold on inner real train OOF
        best_th = 0.50
        best_f1 = -1.0
        y_real_tr = real_train[TARGET_COL].values
        for th in np.linspace(0.05, 0.90, 171):
            p_bin = (inner_oof_prob >= th).astype(int)
            f1_c = f1_score(y_real_tr, p_bin, zero_division=0)
            if f1_c > best_f1:
                best_f1 = f1_c
                best_th = th
                
        per_fold_thresholds[test_sid] = float(best_th)
        
        # Fit final model on full training set
        model = xgb.XGBClassifier(**base_params)
        model.fit(X_train, y_train, verbose=False)
        
        test_prob = model.predict_proba(real_test[ALIGNED_FEATURES])[:, 1]
        test_pred = (test_prob >= best_th).astype(int)
        
        oof_pred_df.loc[real_te_mask, 'prob'] = test_prob
        oof_pred_df.loc[real_te_mask, 'pred'] = test_pred
        
    # Evaluate aggregate out-of-fold metrics on real test shipments
    y_true_all = oof_pred_df[TARGET_COL].values
    y_prob_all = oof_pred_df['prob'].values
    y_pred_all = oof_pred_df['pred'].values
    
    prec = precision_score(y_true_all, y_pred_all, zero_division=0)
    rec = recall_score(y_true_all, y_pred_all, zero_division=0)
    f1 = f1_score(y_true_all, y_pred_all, zero_division=0)
    pr_auc = average_precision_score(y_true_all, y_prob_all)
    roc_auc = roc_auc_score(y_true_all, y_prob_all)
    acc = accuracy_score(y_true_all, y_pred_all)
    cm = confusion_matrix(y_true_all, y_pred_all, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 1.0
    
    fa_total = int(fp)
    fa_per_shipment = fa_total / len(real_shipments)
    fa_per_1000 = (fa_total / len(oof_pred_df)) * 1000.0
    
    # 1-to-1 Physical Event Matching
    ev_res = match_events(oof_pred_df, evaluable_events)
    
    # Feature Importances for sanity check
    # Fit one model on full real + synthetic for inspection
    sample_model = xgb.XGBClassifier(**base_params)
    sample_model.fit(X_train, y_train, verbose=False)
    feat_imp = dict(zip(ALIGNED_FEATURES, [float(x) for x in sample_model.feature_importances_]))
    
    res_entry = {
        'name': exp_info['name'],
        'synth_ratio': exp_info['synth_ratio'],
        'thresholds': per_fold_thresholds,
        'mean_threshold': float(np.mean(list(per_fold_thresholds.values()))),
        'metrics': {
            'pr_auc': pr_auc, 'roc_auc': roc_auc, 'precision': prec, 'recall': rec, 'f1': f1,
            'fpr': fpr, 'specificity': spec, 'accuracy': acc, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn
        },
        'alert_burden': {
            'total_alerts': int(y_pred_all.sum()), 'false_alerts': fa_total,
            'fa_per_shipment': fa_per_shipment, 'fa_per_1000': fa_per_1000
        },
        'event_metrics': ev_res,
        'feature_importances': feat_imp
    }
    results_manifest[exp_key] = res_entry
    
    print(f"\n>>> {exp_info['name']} <<<")
    print(f"  [Row Metrics]:        PR-AUC={pr_auc:.4f} | ROC-AUC={roc_auc:.4f} | Prec={prec*100:5.2f}% | Rec={rec*100:5.2f}% | F1={f1:.4f} | FPR={fpr*100:5.2f}%")
    print(f"  [Confusion Matrix]:   TP={tp:2d}, FP={fp:2d}, FN={fn:2d}, TN={tn:4d}")
    print(f"  [False Alert Burden]: Total FA={fa_total} ({fa_per_shipment:.1f}/shipment, {fa_per_1000:.1f} per 1k)")
    print(f"  [Physical Events]:    Detected: {ev_res['detected_events']} / {ev_res['total_events']} ({ev_res['detection_rate']:.1f}%) | Missed: {ev_res['missed_events']}")
    print(f"  [Lead Time]:          Median={ev_res['median_lead']:.1f} min | Mean={ev_res['mean_lead']:.1f} min | >=30m: {ev_res['pct_ge_30']:.1f}%")

# ============================================================
# 6. SCENARIO-HELD-OUT GENERALIZATION TEST
# ============================================================
print("\n" + "=" * 80)
print("STEP 3: SCENARIO-HELD-OUT GENERALIZATION TEST (On Synthetic Domain)")
print("=" * 80)

# Split synthetic fleet into Seen Scenarios vs Unseen Scenarios
train_scenarios = [
    'SCENARIO_1_NORMAL',
    'SCENARIO_2_HOT_AMBIENT_HEALTHY',
    'SCENARIO_3_TRAFFIC_HEALTHY',
    'SCENARIO_4_DOOR_OPENING',
    'SCENARIO_5_COMPRESSOR_DEGRADATION',
    'SCENARIO_6_COMPRESSOR_FAILURE',
    'SCENARIO_7_POWER_INTERRUPTION'
]
test_scenarios = [
    'SCENARIO_8_DOOR_HOT_AMBIENT',
    'SCENARIO_9_TRAFFIC_HOT_HEALTHY',
    'SCENARIO_10_TRAFFIC_HOT_DEGRADED',
    'SCENARIO_11_RECOVERY',
    'SCENARIO_12_COMBINED_FAILURE'
]

synth_train_data = synth_cohort_proc[synth_cohort_proc['scenario_name'].isin(train_scenarios)].reset_index(drop=True)
synth_test_data = synth_cohort_proc[synth_cohort_proc['scenario_name'].isin(test_scenarios)].reset_index(drop=True)

m_scenario_transfer = xgb.XGBClassifier(**base_params)
m_scenario_transfer.fit(synth_train_data[ALIGNED_FEATURES], synth_train_data[TARGET_COL], verbose=False)

synth_test_prob = m_scenario_transfer.predict_proba(synth_test_data[ALIGNED_FEATURES])[:, 1]
synth_test_pred = (synth_test_prob >= 0.50).astype(int)

st_prauc = average_precision_score(synth_test_data[TARGET_COL], synth_test_prob)
st_rocauc = roc_auc_score(synth_test_data[TARGET_COL], synth_test_prob)
st_prec = precision_score(synth_test_data[TARGET_COL], synth_test_pred, zero_division=0)
st_rec = recall_score(synth_test_data[TARGET_COL], synth_test_pred, zero_division=0)
st_f1 = f1_score(synth_test_data[TARGET_COL], synth_test_pred, zero_division=0)

scenario_transfer_results = {
    'train_scenarios': train_scenarios,
    'test_scenarios': test_scenarios,
    'n_train_rows': len(synth_train_data),
    'n_test_rows': len(synth_test_data),
    'pr_auc': st_prauc,
    'roc_auc': st_rocauc,
    'precision': st_prec,
    'recall': st_rec,
    'f1': st_f1
}

print(f"Trained on {len(train_scenarios)} Scenarios (N={len(synth_train_data)}) -> Tested on {len(test_scenarios)} Unseen Scenarios (N={len(synth_test_data)})")
print(f"Scenario-Held-Out Transfer Performance: PR-AUC={st_prauc:.4f}, ROC-AUC={st_rocauc:.4f}, Prec={st_prec*100:.2f}%, Rec={st_rec*100:.2f}%, F1={st_f1:.4f}")

# Save full results JSON
full_output = {
    'aligned_features': ALIGNED_FEATURES,
    'models_comparison': results_manifest,
    'scenario_held_out_generalization': scenario_transfer_results
}

out_json_path = r"ml_pipeline\synthetic\synthetic_augmentation_results.json"
def json_serial(obj):
    if isinstance(obj, (np.integer, np.int64, np.int32)): return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)): return float(obj)
    elif isinstance(obj, np.ndarray): return obj.tolist()
    raise TypeError(f"Type {type(obj)} not serializable")

with open(out_json_path, 'w') as f:
    json.dump(full_output, f, indent=2, default=json_serial)

print(f"\nSaved synthetic augmentation experiment results to: {out_json_path}")

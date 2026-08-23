"""
Extract Real Data Statistics from Strawberry Dataset
=====================================================
Calculates empirical distributions for temperature, slopes, sampling intervals,
and risk state transitions from the deduplicated Strawberry dataset.
Saves to ml_pipeline/synthetic/real_data_statistics.json.
"""

import sys
import os
import json
import pandas as pd
import numpy as np

os.makedirs(r"ml_pipeline\synthetic", exist_ok=True)
os.makedirs(r"ml_pipeline\synthetic\data", exist_ok=True)

# 1. Ingest Data
train_df = pd.read_csv(r"ml_pipeline\data\strawberry_train.csv")
test_df = pd.read_csv(r"ml_pipeline\data\strawberry_test.csv")
raw_df = pd.concat([train_df, test_df], ignore_index=True)
raw_df['Time_dt'] = pd.to_datetime(raw_df['Time'])

df = raw_df.drop_duplicates(subset=['shipment_id', 'Time_dt']).sort_values(['shipment_id', 'Time_dt']).reset_index(drop=True)

# 2. Extract Statistics
n_rows = len(df)
n_shipments = df['shipment_id'].nunique()

# Temperature (T_mean_t)
t_mean_series = df['T_mean_t'].dropna()
t_stats = {
    'mean': float(t_mean_series.mean()),
    'std': float(t_mean_series.std()),
    'min': float(t_mean_series.min()),
    'max': float(t_mean_series.max()),
    'median': float(t_mean_series.median()),
    'p25': float(t_mean_series.quantile(0.25)),
    'p75': float(t_mean_series.quantile(0.75)),
    'p01': float(t_mean_series.quantile(0.01)),
    'p99': float(t_mean_series.quantile(0.99))
}

# 10-min Step Delta and Slope
df['dt_min'] = df.groupby('shipment_id')['Time_dt'].diff().dt.total_seconds() / 60.0
df['dT'] = df.groupby('shipment_id')['T_mean_t'].diff()
df['slope_deg_per_min'] = df['dT'] / df['dt_min']

valid_steps = df[df['dt_min'] == 10.0].copy()
delta_stats = {
    'mean_10m_delta': float(valid_steps['dT'].mean()),
    'std_10m_delta': float(valid_steps['dT'].std()),
    'min_10m_delta': float(valid_steps['dT'].min()),
    'max_10m_delta': float(valid_steps['dT'].max()),
    'p05_10m_delta': float(valid_steps['dT'].quantile(0.05)),
    'p95_10m_delta': float(valid_steps['dT'].quantile(0.95)),
    'mean_slope': float(valid_steps['slope_deg_per_min'].mean()),
    'std_slope': float(valid_steps['slope_deg_per_min'].std()),
    'p05_slope': float(valid_steps['slope_deg_per_min'].quantile(0.05)),
    'p95_slope': float(valid_steps['slope_deg_per_min'].quantile(0.95))
}

# Sampling interval distribution
sampling_stats = {
    'median_interval_min': float(df['dt_min'].dropna().median()),
    'pct_exact_10m': float((df['dt_min'] == 10.0).mean() * 100),
    'min_interval_min': float(df['dt_min'].dropna().min()),
    'max_interval_min': float(df['dt_min'].dropna().max())
}

# Risk State (risk_level) Distribution & Durations
risk_counts = df['risk_level'].value_counts(dropna=False).to_dict()
risk_pcts = (df['risk_level'].value_counts(normalize=True, dropna=False) * 100).to_dict()

# Calculate episode durations for R0, R1, R2
durations = {'R0': [], 'R1': [], 'R2': []}
for sid in df['shipment_id'].unique():
    ship_data = df[df['shipment_id'] == sid].sort_values('Time_dt').reset_index(drop=True)
    current_state = ship_data.loc[0, 'risk_level']
    current_len = 1
    for i in range(1, len(ship_data)):
        st = ship_data.loc[i, 'risk_level']
        if st == current_state:
            current_len += 1
        else:
            if current_state == 0.0: durations['R0'].append(current_len * 10)
            elif current_state == 1.0: durations['R1'].append(current_len * 10)
            elif current_state == 2.0: durations['R2'].append(current_len * 10)
            current_state = st
            current_len = 1
    if current_state == 0.0: durations['R0'].append(current_len * 10)
    elif current_state == 1.0: durations['R1'].append(current_len * 10)
    elif current_state == 2.0: durations['R2'].append(current_len * 10)

duration_stats = {
    'R0_episodes_count': len(durations['R0']),
    'R0_mean_duration_min': float(np.mean(durations['R0'])) if durations['R0'] else 0.0,
    'R0_median_duration_min': float(np.median(durations['R0'])) if durations['R0'] else 0.0,
    'R1_episodes_count': len(durations['R1']),
    'R1_mean_duration_min': float(np.mean(durations['R1'])) if durations['R1'] else 0.0,
    'R1_median_duration_min': float(np.median(durations['R1'])) if durations['R1'] else 0.0,
    'R2_episodes_count': len(durations['R2']),
    'R2_mean_duration_min': float(np.mean(durations['R2'])) if durations['R2'] else 0.0,
    'R2_median_duration_min': float(np.median(durations['R2'])) if durations['R2'] else 0.0
}

# Per-shipment trajectory stats
shipment_stats = {}
for sid in sorted(df['shipment_id'].unique()):
    s_df = df[df['shipment_id'] == sid]
    shipment_stats[sid] = {
        'row_count': len(s_df),
        'duration_hours': float((s_df['Time_dt'].max() - s_df['Time_dt'].min()).total_seconds() / 3600.0),
        'temp_mean': float(s_df['T_mean_t'].mean()),
        'temp_min': float(s_df['T_mean_t'].min()),
        'temp_max': float(s_df['T_mean_t'].max()),
        'temp_std': float(s_df['T_mean_t'].std())
    }

real_data_stats = {
    'source_dataset': 'strawberry_train.csv + strawberry_test.csv (deduplicated)',
    'total_rows': n_rows,
    'total_shipments': n_shipments,
    'temperature_stats': t_stats,
    'step_change_and_slope_stats': delta_stats,
    'sampling_interval_stats': sampling_stats,
    'risk_distribution_pct': {str(k): float(v) for k, v in risk_pcts.items()},
    'episode_duration_stats': duration_stats,
    'per_shipment_summary': shipment_stats
}

with open(r"ml_pipeline\synthetic\real_data_statistics.json", 'w') as f:
    json.dump(real_data_stats, f, indent=2)

print("Saved real data statistics to ml_pipeline/synthetic/real_data_statistics.json")

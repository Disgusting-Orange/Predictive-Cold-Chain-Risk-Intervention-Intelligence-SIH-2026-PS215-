"""
FrostLink ML Pipeline -- Phase 0+1: Data Audit Script
=====================================================
Downloads and inspects both primary and secondary datasets.
Produces a comprehensive audit report.

NO MODEL TRAINING. NO MODIFICATIONS TO EXISTING CODE.
"""

import sys
import os

# Fix Windows encoding issues
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

import pandas as pd
import numpy as np
import json
from datetime import datetime

print("=" * 70)
print("FROSTLINK ML PIPELINE — DATA AUDIT")
print(f"Timestamp: {datetime.now().isoformat()}")
print("=" * 70)

# ============================================================
# 1. NIGERIA COLD CHAIN DATASET (PRIMARY)
# ============================================================
print("\n\n" + "=" * 70)
print("DATASET 1: Nigeria Transport & Logistics Cold Chain Monitoring")
print("Source: electricsheepafrica/nigerian_transport_and_logistics_cold_chain")
print("=" * 70)

try:
    from datasets import load_dataset
    print("\nLoading Nigeria dataset from HuggingFace...")
    nigeria_ds = load_dataset(
        "electricsheepafrica/nigerian_transport_and_logistics_cold_chain",
        split="train"
    )
    nigeria_df = nigeria_ds.to_pandas()
    print(f"[OK] Loaded successfully: {len(nigeria_df)} rows")
except Exception as e:
    print(f"[FAIL] Failed to load Nigeria dataset: {e}")
    nigeria_df = None

if nigeria_df is not None:
    print("\n--- BASIC SHAPE ---")
    print(f"Rows: {len(nigeria_df)}")
    print(f"Columns: {len(nigeria_df.columns)}")
    
    print("\n--- COLUMN NAMES ---")
    for i, col in enumerate(nigeria_df.columns):
        print(f"  {i+1:3d}. {col}")
    
    print("\n--- DATA TYPES ---")
    for col in nigeria_df.columns:
        print(f"  {col:30s} → {nigeria_df[col].dtype}")
    
    print("\n--- MISSING VALUES ---")
    missing = nigeria_df.isnull().sum()
    missing_pct = (missing / len(nigeria_df) * 100).round(2)
    for col in nigeria_df.columns:
        if missing[col] > 0:
            print(f"  {col:30s} → {missing[col]:8d} ({missing_pct[col]:.2f}%)")
    total_missing = missing.sum()
    if total_missing == 0:
        print("  No missing values found.")
    
    print("\n--- DUPLICATE ROWS ---")
    n_dup = nigeria_df.duplicated().sum()
    print(f"  Exact duplicate rows: {n_dup}")
    
    print("\n--- UNIQUE VALUES (KEY COLUMNS) ---")
    for col in nigeria_df.columns:
        n_unique = nigeria_df[col].nunique()
        if n_unique <= 50 or col in ['trip_id', 'excursion', 'door_open']:
            print(f"  {col:30s} → {n_unique} unique values")
    
    print("\n--- TRIP ANALYSIS ---")
    if 'trip_id' in nigeria_df.columns:
        n_trips = nigeria_df['trip_id'].nunique()
        print(f"  Total unique trips: {n_trips}")
        trip_sizes = nigeria_df.groupby('trip_id').size()
        print(f"  Rows per trip — min: {trip_sizes.min()}, max: {trip_sizes.max()}, "
              f"mean: {trip_sizes.mean():.1f}, median: {trip_sizes.median():.1f}")
    
    print("\n--- TIMESTAMP ANALYSIS ---")
    if 'timestamp' in nigeria_df.columns:
        ts_col = pd.to_datetime(nigeria_df['timestamp'], errors='coerce')
        print(f"  Earliest: {ts_col.min()}")
        print(f"  Latest:   {ts_col.max()}")
        print(f"  Parse failures: {ts_col.isna().sum()}")
        
        # Sampling frequency per trip
        if 'trip_id' in nigeria_df.columns:
            sample_trip = nigeria_df['trip_id'].value_counts().index[0]
            trip_ts = pd.to_datetime(
                nigeria_df[nigeria_df['trip_id'] == sample_trip]['timestamp'],
                errors='coerce'
            ).sort_values()
            diffs = trip_ts.diff().dropna()
            if len(diffs) > 0:
                print(f"  Sample trip '{sample_trip}':")
                print(f"    Sampling interval — median: {diffs.median()}, mean: {diffs.mean()}")
    
    print("\n--- TARGET CANDIDATES ---")
    if 'excursion' in nigeria_df.columns:
        exc_counts = nigeria_df['excursion'].value_counts()
        print(f"  'excursion' column distribution:")
        for val, cnt in exc_counts.items():
            pct = cnt / len(nigeria_df) * 100
            print(f"    {val}: {cnt} ({pct:.2f}%)")
    
    print("\n--- NUMERICAL SUMMARY ---")
    num_cols = nigeria_df.select_dtypes(include=[np.number]).columns.tolist()
    if num_cols:
        print(nigeria_df[num_cols].describe().round(4).to_string())
    
    print("\n--- GPS ANALYSIS ---")
    for col in ['lat', 'lon']:
        if col in nigeria_df.columns:
            print(f"  {col}: min={nigeria_df[col].min():.4f}, "
                  f"max={nigeria_df[col].max():.4f}, "
                  f"mean={nigeria_df[col].mean():.4f}")
    
    print("\n--- DOOR STATE ANALYSIS ---")
    if 'door_open' in nigeria_df.columns:
        door_counts = nigeria_df['door_open'].value_counts()
        print(f"  Door open distribution:")
        for val, cnt in door_counts.items():
            pct = cnt / len(nigeria_df) * 100
            print(f"    {val}: {cnt} ({pct:.2f}%)")
    
    # Save to CSV for later use
    output_path = r"c:\Kamalesh\College\Hackathons\SIH 2026\ml_pipeline\data\nigeria_cold_chain.csv"
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nigeria_df.to_csv(output_path, index=False)
    print(f"\n[OK] Saved to: {output_path}")

# ============================================================
# 2. STRAWBERRY COLD CHAIN DATASET (SECONDARY)
# ============================================================
print("\n\n" + "=" * 70)
print("DATASET 2: Strawberry Cold Chain Transportation")
print("Source: NifferLi/Cold-Chain-Transportation-Strawberry")
print("=" * 70)

try:
    from datasets import load_dataset
    print("\nLoading Strawberry dataset from HuggingFace...")
    strawberry_train = load_dataset(
        "NifferLi/Cold-Chain-Transportation-Strawberry",
        split="train"
    )
    strawberry_test = load_dataset(
        "NifferLi/Cold-Chain-Transportation-Strawberry",
        split="test"
    )
    strawberry_train_df = strawberry_train.to_pandas()
    strawberry_test_df = strawberry_test.to_pandas()
    print(f"[OK] Loaded: train={len(strawberry_train_df)} rows, test={len(strawberry_test_df)} rows")
except Exception as e:
    print(f"[FAIL] Failed to load Strawberry dataset: {e}")
    strawberry_train_df = None
    strawberry_test_df = None

if strawberry_train_df is not None:
    straw_df = pd.concat([strawberry_train_df, strawberry_test_df], ignore_index=True)
    
    print(f"\n--- BASIC SHAPE (combined) ---")
    print(f"Rows: {len(straw_df)}")
    print(f"Columns: {len(straw_df.columns)}")
    
    print("\n--- COLUMN NAMES ---")
    for i, col in enumerate(straw_df.columns):
        print(f"  {i+1:3d}. {col}")
    
    print("\n--- DATA TYPES ---")
    for col in straw_df.columns:
        print(f"  {col:30s} → {straw_df[col].dtype}")
    
    print("\n--- MISSING VALUES ---")
    missing = straw_df.isnull().sum()
    missing_pct = (missing / len(straw_df) * 100).round(2)
    for col in straw_df.columns:
        if missing[col] > 0:
            print(f"  {col:30s} → {missing[col]:8d} ({missing_pct[col]:.2f}%)")
    total_missing = missing.sum()
    if total_missing == 0:
        print("  No missing values found.")
    
    print("\n--- SHIPMENT ANALYSIS ---")
    if 'shipment_id' in straw_df.columns:
        n_ship = straw_df['shipment_id'].nunique()
        print(f"  Total unique shipments: {n_ship}")
        ship_sizes = straw_df.groupby('shipment_id').size()
        print(f"  Rows per shipment — min: {ship_sizes.min()}, max: {ship_sizes.max()}, "
              f"mean: {ship_sizes.mean():.1f}")
    
    print("\n--- TARGET CANDIDATES ---")
    target_cols = [c for c in straw_df.columns if c.startswith('label_') or c.startswith('risk_')]
    for col in target_cols:
        print(f"\n  '{col}' distribution:")
        val_counts = straw_df[col].value_counts().sort_index()
        for val, cnt in val_counts.items():
            pct = cnt / len(straw_df) * 100
            print(f"    {val}: {cnt} ({pct:.2f}%)")
    
    print("\n--- TEMPERATURE SENSOR COLUMNS ---")
    temp_cols = [c for c in straw_df.columns if any(
        x in c for x in ['Front_', 'Middle_', 'Rear_']
    ) and 'mask_' not in c]
    if temp_cols:
        print(f"  Sensor columns: {temp_cols}")
        print(straw_df[temp_cols].describe().round(4).to_string())
    
    print("\n--- NUMERICAL SUMMARY ---")
    num_cols = straw_df.select_dtypes(include=[np.number]).columns.tolist()
    if num_cols:
        print(straw_df[num_cols].describe().round(4).to_string())
    
    # Save
    train_path = r"c:\Kamalesh\College\Hackathons\SIH 2026\ml_pipeline\data\strawberry_train.csv"
    test_path = r"c:\Kamalesh\College\Hackathons\SIH 2026\ml_pipeline\data\strawberry_test.csv"
    strawberry_train_df.to_csv(train_path, index=False)
    strawberry_test_df.to_csv(test_path, index=False)
    print(f"\n[OK] Saved train to: {train_path}")
    print(f"[OK] Saved test to:  {test_path}")

print("\n\n" + "=" * 70)
print("DATA AUDIT COMPLETE")
print("=" * 70)


"""
Freezes XGBoost v2 artifacts and computes SHA-256 integrity hashes.
"""
import os
import json
import hashlib
import shutil

V1_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "frostlink_xgb_v1"))
V2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "frostlink_xgb_v2"))

shutil.copyfile(os.path.join(V1_DIR, "feature_schema.json"), os.path.join(V2_DIR, "feature_schema.json"))

backend_contract = {
    "model_name": "frostlink_xgb_v2",
    "version": "2.0.0",
    "required_feature_count": 40,
    "input_schema_version": "1.0.0",
    "decision_threshold": 0.5750,
    "prediction_horizon_minutes": 60,
    "features_order_contract": [
        "T_mean_t", "spatial_range_t", "spatial_std_t", "hot_ratio_t", "cold_ratio_t",
        "mask_ratio_t", "W60_T_mean", "W60_T_std", "W60_T_min", "W60_T_max",
        "W60_T_range", "W60_delta", "W60_slope", "W60_spatial_range_mean", "W60_spatial_range_max",
        "W60_spatial_std_mean", "W60_hot_ratio_mean", "W60_hot_ratio_max", "W60_over_auc_mean", "W60_over_auc_max",
        "W60_under_auc_mean", "W60_under_auc_max", "W60_over_dur_mean", "W60_under_dur_mean", "v4_slope_short_t",
        "v4_slope_long_t", "v4_accel_t", "v4_shock_t", "v4_median_t", "v4_iqr_t",
        "v4_p90_t", "v4_p95_t", "v4_over_auc_t", "v4_under_auc_t", "v4_over_max_t",
        "v4_under_max_t", "sconf", "coverage_points", "coverage_time", "N_valid"
    ]
}
with open(os.path.join(V2_DIR, "backend_contract.json"), "w") as f:
    json.dump(backend_contract, f, indent=2)

manifest = {}
for fname in ["model.json", "threshold.json", "feature_schema.json", "model_metadata.json", "backend_contract.json"]:
    fpath = os.path.join(V2_DIR, fname)
    with open(fpath, "rb") as f:
        manifest[fname] = hashlib.sha256(f.read()).hexdigest()

with open(os.path.join(V2_DIR, "model_manifest.json"), "w") as f:
    json.dump({"manifest_version": "1.0.0", "hashes": manifest}, f, indent=2)

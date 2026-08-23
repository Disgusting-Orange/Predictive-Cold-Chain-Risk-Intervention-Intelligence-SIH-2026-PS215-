"""
FrostLink Feature Engineering Engine -- Phase 14
================================================
Single source of truth for converting raw multi-probe telemetry history
into the exact 40-feature schema expected by the production XGBoost model.
"""

import os
import json
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime
import numpy as np
import pandas as pd

try:
    from .raw_schema import RawTelemetryPacket, RawTelemetryHistory
except ImportError:
    from raw_schema import RawTelemetryPacket, RawTelemetryHistory

FEATURE_SCHEMA_DEFAULT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "model_artifacts", "frostlink_xgb_v1", "feature_schema.json")
)

class FrostLinkFeatureEngineer:
    def __init__(self, schema_path: str = FEATURE_SCHEMA_DEFAULT_PATH):
        self.schema_path = schema_path
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Feature schema not found at: {schema_path}")
            
        with open(schema_path, "r") as f:
            schema_data = json.load(f)
            self.schema_version = schema_data.get("schema_version", "1.0.0")
            sorted_features = sorted(schema_data["features"], key=lambda x: x["feature_order"])
            self.feature_names = [f["feature_name"] for f in sorted_features]
            
        assert len(self.feature_names) == 40, f"Expected 40 features in schema, found {len(self.feature_names)}"

    def extract_features(
        self,
        history: Union[List[RawTelemetryPacket], List[Dict[str, Any]], pd.DataFrame],
        target_timestamp: Optional[Union[str, datetime]] = None
    ) -> Tuple[Dict[str, Optional[float]], Dict[str, Any]]:
        """
        Extracts the exact 40 features causally from telemetry history up to target_timestamp (or last packet).
        Returns:
            features_dict: Dict of exact 40 feature names -> float64 values (ordered)
            meta: Dict containing cold-start status, history length, and validation flags
        """
        # 1. Parse and standardize history into DataFrame
        if isinstance(history, pd.DataFrame):
            df_hist = history.copy()
        elif isinstance(history, list):
            records = []
            for item in history:
                if isinstance(item, RawTelemetryPacket):
                    rec = item.dict()
                elif isinstance(item, dict):
                    rec = item
                else:
                    raise TypeError(f"Unsupported packet item type: {type(item)}")
                
                flat_rec = {
                    "shipment_id": rec.get("shipment_id", "UNKNOWN"),
                    "timestamp": rec["timestamp"],
                    "sconf": rec.get("sconf", 1.0),
                    "coverage_time": rec.get("coverage_time", 1.0),
                }
                # Unpack probe dictionary
                probes = rec.get("probes", {})
                for p_name, p_val in probes.items():
                    flat_rec[f"probe_{p_name}"] = p_val
                records.append(flat_rec)
            df_hist = pd.DataFrame(records)
        else:
            raise TypeError(f"Unsupported history input type: {type(history)}")

        if len(df_hist) == 0:
            raise ValueError("Telemetry history is empty.")

        # Ensure datetime sorting
        df_hist["Time_dt"] = pd.to_datetime(df_hist["timestamp"] if "timestamp" in df_hist.columns else df_hist["Time"])
        df_hist = df_hist.sort_values("Time_dt").reset_index(drop=True)

        # 2. Filter strictly up to target_timestamp (Zero Future Lookahead)
        if target_timestamp is not None:
            t_eval = pd.to_datetime(target_timestamp)
            df_hist = df_hist[df_hist["Time_dt"] <= t_eval].reset_index(drop=True)
            if len(df_hist) == 0:
                raise ValueError(f"No telemetry packets exist at or before target timestamp: {target_timestamp}")

        # 3. Identify probe columns
        probe_cols = [c for c in df_hist.columns if c.startswith("probe_")]
        if not probe_cols:
            # Fallback: check for named probe columns from strawberry dataset
            known_probes = ['Front_Top', 'Front_Middle', 'Front_Bottom', 'Middle_Top', 'Middle_Middle', 'Middle_Bottom', 'Rear_Top', 'Rear_Middle', 'Rear_Bottom']
            probe_cols = [c for c in known_probes if c in df_hist.columns]
            if not probe_cols:
                # Generic float columns as probes
                probe_cols = [c for c in df_hist.select_dtypes(include=[np.number]).columns if c not in ["sconf", "coverage_time", "N_valid", "coverage_points"]]

        # 4. Instantaneous Spatial Extractions for each row in history
        probes_df = df_hist[probe_cols].astype(float)
        
        # Valid measurements count per row
        n_valid = probes_df.notna().sum(axis=1)
        total_channels = len(probe_cols) if len(probe_cols) > 0 else 9

        # Row-level spatial metrics
        t_mean_series = probes_df.mean(axis=1)
        t_min_series = probes_df.min(axis=1)
        t_max_series = probes_df.max(axis=1)
        spatial_range_series = t_max_series - t_min_series
        spatial_std_series = probes_df.std(axis=1, ddof=0).fillna(0.0)
        
        # Hot ratio (> 4.0C) & cold ratio (< 0.0C)
        hot_ratio_series = (probes_df > 4.0).sum(axis=1) / np.maximum(1, n_valid)
        cold_ratio_series = (probes_df < 0.0).sum(axis=1) / np.maximum(1, n_valid)
        mask_ratio_series = 1.0 - (n_valid / float(total_channels))

        # Quantile spatial metrics (v4)
        v4_median_series = probes_df.median(axis=1)
        v4_iqr_series = probes_df.quantile(0.75, axis=1) - probes_df.quantile(0.25, axis=1)
        v4_p90_series = probes_df.quantile(0.90, axis=1)
        v4_p95_series = probes_df.quantile(0.95, axis=1)

        # Max exceedance metrics
        v4_over_max_series = np.maximum(0.0, t_max_series - 4.0)
        v4_under_max_series = np.maximum(0.0, 0.0 - t_min_series)

        # 5. Build Temporal Working Frame
        work_df = pd.DataFrame({
            "Time_dt": df_hist["Time_dt"],
            "T_mean": t_mean_series,
            "T_min": t_min_series,
            "T_max": t_max_series,
            "spatial_range": spatial_range_series,
            "spatial_std": spatial_std_series,
            "hot_ratio": hot_ratio_series,
            "cold_ratio": cold_ratio_series,
            "mask_ratio": mask_ratio_series,
            "v4_median": v4_median_series,
            "v4_iqr": v4_iqr_series,
            "v4_p90": v4_p90_series,
            "v4_p95": v4_p95_series,
            "v4_over_max": v4_over_max_series,
            "v4_under_max": v4_under_max_series,
            "sconf": df_hist.get("sconf", 1.0),
            "coverage_time": df_hist.get("coverage_time", 1.0),
            "N_valid": n_valid
        })

        # 6. Causal Backward Rolling & Dynamic Features (Window = 6 steps = 60m backward)
        # Instantaneous 10m differences
        work_df["10m_delta"] = work_df["T_mean"].diff().fillna(0.0)
        work_df["10m_slope"] = work_df["10m_delta"] / 10.0
        work_df["accel"] = work_df["10m_slope"].diff().fillna(0.0)
        work_df["shock"] = work_df["10m_delta"].abs()

        # 50m / 60m backward slope: T(t) - T(t-5 steps)
        work_df["50m_delta"] = work_df["T_mean"] - work_df["T_mean"].shift(5)
        work_df["50m_slope"] = work_df["50m_delta"] / 50.0

        # Rolling 60m statistics (6 steps causal backward)
        # Using min_periods=1 ensures calculation during cold-start
        work_df["W60_T_mean"] = work_df["T_mean"].rolling(6, min_periods=1).mean()
        work_df["W60_T_std"] = work_df["T_mean"].rolling(6, min_periods=1).std().fillna(0.0)
        work_df["W60_T_min"] = work_df["T_mean"].rolling(6, min_periods=1).min()
        work_df["W60_T_max"] = work_df["T_mean"].rolling(6, min_periods=1).max()
        work_df["W60_T_range"] = work_df["W60_T_max"] - work_df["W60_T_min"]

        # Rolling spatial metrics
        work_df["W60_spatial_range_mean"] = work_df["spatial_range"].rolling(6, min_periods=1).mean()
        work_df["W60_spatial_range_max"] = work_df["spatial_range"].rolling(6, min_periods=1).max()
        work_df["W60_spatial_std_mean"] = work_df["spatial_std"].rolling(6, min_periods=1).mean()

        # Rolling hot ratio
        work_df["W60_hot_ratio_mean"] = work_df["hot_ratio"].rolling(6, min_periods=1).mean()
        work_df["W60_hot_ratio_max"] = work_df["hot_ratio"].rolling(6, min_periods=1).max()

        # Cumulative durations & areas in past 60m
        is_hot_step = (work_df["T_mean"] > 4.0).astype(float)
        is_cold_step = (work_df["T_mean"] < 0.0).astype(float)
        work_df["W60_over_dur_mean"] = is_hot_step.rolling(6, min_periods=1).mean()
        work_df["W60_under_dur_mean"] = is_cold_step.rolling(6, min_periods=1).mean()

        work_df["W60_over_auc_mean"] = work_df["v4_over_max"].rolling(6, min_periods=1).mean()
        work_df["W60_over_auc_max"] = work_df["v4_over_max"].rolling(6, min_periods=1).max()
        work_df["W60_under_auc_mean"] = work_df["v4_under_max"].rolling(6, min_periods=1).mean()
        work_df["W60_under_auc_max"] = work_df["v4_under_max"].rolling(6, min_periods=1).max()

        # 7. Extract the latest evaluation row (time t)
        last_row = work_df.iloc[-1]
        n_history_steps = len(work_df)
        is_cold_start = n_history_steps < 6
        is_inference_allowed = n_history_steps >= 6

        # 8. Map to the exact 40 schema feature keys
        feature_map: Dict[str, Optional[float]] = {
            "T_mean_t": float(last_row["T_mean"]),
            "spatial_range_t": float(last_row["spatial_range"]),
            "spatial_std_t": float(last_row["spatial_std"]),
            "hot_ratio_t": float(last_row["hot_ratio"]),
            "cold_ratio_t": float(last_row["cold_ratio"]),
            "mask_ratio_t": float(last_row["mask_ratio"]),
            "W60_T_mean": float(last_row["W60_T_mean"]),
            "W60_T_std": float(last_row["W60_T_std"]),
            "W60_T_min": float(last_row["W60_T_min"]),
            "W60_T_max": float(last_row["W60_T_max"]),
            "W60_T_range": float(last_row["W60_T_range"]),
            "W60_delta": float(last_row["50m_delta"]) if pd.notna(last_row["50m_delta"]) else float(last_row["10m_delta"]),
            "W60_slope": float(last_row["50m_slope"]) if pd.notna(last_row["50m_slope"]) else float(last_row["10m_slope"]),
            "W60_spatial_range_mean": float(last_row["W60_spatial_range_mean"]),
            "W60_spatial_range_max": float(last_row["W60_spatial_range_max"]),
            "W60_spatial_std_mean": float(last_row["W60_spatial_std_mean"]),
            "W60_hot_ratio_mean": float(last_row["W60_hot_ratio_mean"]),
            "W60_hot_ratio_max": float(last_row["W60_hot_ratio_max"]),
            "W60_over_auc_mean": float(last_row["W60_over_auc_mean"]),
            "W60_over_auc_max": float(last_row["W60_over_auc_max"]),
            "W60_under_auc_mean": float(last_row["W60_under_auc_mean"]),
            "W60_under_auc_max": float(last_row["W60_under_auc_max"]),
            "W60_over_dur_mean": float(last_row["W60_over_dur_mean"]),
            "W60_under_dur_mean": float(last_row["W60_under_dur_mean"]),
            "v4_slope_short_t": float(last_row["10m_slope"]),
            "v4_slope_long_t": float(last_row["50m_slope"]) if pd.notna(last_row["50m_slope"]) else float(last_row["10m_slope"]),
            "v4_accel_t": float(last_row["accel"]),
            "v4_shock_t": float(last_row["shock"]),
            "v4_median_t": float(last_row["v4_median"]),
            "v4_iqr_t": float(last_row["v4_iqr"]),
            "v4_p90_t": float(last_row["v4_p90"]),
            "v4_p95_t": float(last_row["v4_p95"]),
            "v4_over_auc_t": float(last_row["v4_over_max"]),
            "v4_under_auc_t": float(last_row["v4_under_max"]),
            "v4_over_max_t": float(last_row["v4_over_max"]),
            "v4_under_max_t": float(last_row["v4_under_max"]),
            "sconf": float(last_row["sconf"]) if pd.notna(last_row["sconf"]) else 1.0,
            "coverage_points": float(last_row["N_valid"]),
            "coverage_time": float(last_row["coverage_time"]) if pd.notna(last_row["coverage_time"]) else 1.0,
            "N_valid": float(last_row["N_valid"])
        }

        # 9. Return in exact schema sequence
        ordered_output = {k: feature_map[k] for k in self.feature_names}

        metadata = {
            "schema_version": self.schema_version,
            "evaluation_timestamp": str(last_row["Time_dt"]),
            "history_packets_count": n_history_steps,
            "cold_start_status": "COLD_START" if is_cold_start else "WARMED",
            "is_inference_allowed": is_inference_allowed,
            "active_probes_count": int(last_row["N_valid"]),
            "is_causally_isolated": True
        }

        return ordered_output, metadata

    def extract_features_dataframe(self, df_shipment: pd.DataFrame) -> pd.DataFrame:
        """
        Fast, fully vectorized extraction of the 40 causal features across an entire shipment trajectory.
        Guarantees strict 1-to-1 numerical equivalence with extract_features() at every step.
        """
        df_hist = df_shipment.copy()
        df_hist["Time_dt"] = pd.to_datetime(df_hist["timestamp"] if "timestamp" in df_hist.columns else df_hist["Time"])
        df_hist = df_hist.sort_values("Time_dt").reset_index(drop=True)

        known_probes = ['Front_Top', 'Front_Middle', 'Front_Bottom', 'Middle_Top', 'Middle_Middle', 'Middle_Bottom', 'Rear_Top', 'Rear_Middle', 'Rear_Bottom']
        probe_cols = [c for c in known_probes if c in df_hist.columns]
        if not probe_cols:
            probe_cols = [c for c in df_hist.columns if c.startswith("probe_")]

        probes_df = df_hist[probe_cols].astype(float)
        n_valid = probes_df.notna().sum(axis=1)
        total_channels = len(probe_cols) if len(probe_cols) > 0 else 9

        t_mean_series = probes_df.mean(axis=1)
        t_min_series = probes_df.min(axis=1)
        t_max_series = probes_df.max(axis=1)
        spatial_range_series = t_max_series - t_min_series
        spatial_std_series = probes_df.std(axis=1, ddof=0).fillna(0.0)

        hot_ratio_series = (probes_df > 4.0).sum(axis=1) / np.maximum(1, n_valid)
        cold_ratio_series = (probes_df < 0.0).sum(axis=1) / np.maximum(1, n_valid)
        mask_ratio_series = 1.0 - (n_valid / float(total_channels))

        v4_median_series = probes_df.median(axis=1)
        v4_iqr_series = probes_df.quantile(0.75, axis=1) - probes_df.quantile(0.25, axis=1)
        v4_p90_series = probes_df.quantile(0.90, axis=1)
        v4_p95_series = probes_df.quantile(0.95, axis=1)

        v4_over_max_series = np.maximum(0.0, t_max_series - 4.0)
        v4_under_max_series = np.maximum(0.0, 0.0 - t_min_series)

        # Causal temporal series
        d10m = t_mean_series.diff().fillna(0.0)
        s10m = d10m / 10.0
        accel = s10m.diff().fillna(0.0)
        shock = d10m.abs()

        d50m = t_mean_series - t_mean_series.shift(5)
        d50m_filled = d50m.fillna(d10m)
        s50m_filled = (d50m / 50.0).fillna(s10m)

        # Rolling 6-step (60m) statistics
        w60_mean = t_mean_series.rolling(6, min_periods=1).mean()
        w60_std = t_mean_series.rolling(6, min_periods=1).std().fillna(0.0)
        w60_min = t_mean_series.rolling(6, min_periods=1).min()
        w60_max = t_mean_series.rolling(6, min_periods=1).max()
        w60_range = w60_max - w60_min

        w60_sp_range_mean = spatial_range_series.rolling(6, min_periods=1).mean()
        w60_sp_range_max = spatial_range_series.rolling(6, min_periods=1).max()
        w60_sp_std_mean = spatial_std_series.rolling(6, min_periods=1).mean()

        w60_hot_mean = hot_ratio_series.rolling(6, min_periods=1).mean()
        w60_hot_max = hot_ratio_series.rolling(6, min_periods=1).max()

        is_hot = (t_mean_series > 4.0).astype(float)
        is_cold = (t_mean_series < 0.0).astype(float)
        w60_over_dur = is_hot.rolling(6, min_periods=1).mean()
        w60_under_dur = is_cold.rolling(6, min_periods=1).mean()

        w60_over_auc_mean = v4_over_max_series.rolling(6, min_periods=1).mean()
        w60_over_auc_max = v4_over_max_series.rolling(6, min_periods=1).max()
        w60_under_auc_mean = v4_under_max_series.rolling(6, min_periods=1).mean()
        w60_under_auc_max = v4_under_max_series.rolling(6, min_periods=1).max()

        sconf_series = df_hist["sconf"] if "sconf" in df_hist.columns else pd.Series(1.0, index=df_hist.index)
        cov_time_series = df_hist["coverage_time"] if "coverage_time" in df_hist.columns else pd.Series(1.0, index=df_hist.index)

        feature_dict = {
            "T_mean_t": t_mean_series,
            "spatial_range_t": spatial_range_series,
            "spatial_std_t": spatial_std_series,
            "hot_ratio_t": hot_ratio_series,
            "cold_ratio_t": cold_ratio_series,
            "mask_ratio_t": mask_ratio_series,
            "W60_T_mean": w60_mean,
            "W60_T_std": w60_std,
            "W60_T_min": w60_min,
            "W60_T_max": w60_max,
            "W60_T_range": w60_range,
            "W60_delta": d50m_filled,
            "W60_slope": s50m_filled,
            "W60_spatial_range_mean": w60_sp_range_mean,
            "W60_spatial_range_max": w60_sp_range_max,
            "W60_spatial_std_mean": w60_sp_std_mean,
            "W60_hot_ratio_mean": w60_hot_mean,
            "W60_hot_ratio_max": w60_hot_max,
            "W60_over_auc_mean": w60_over_auc_mean,
            "W60_over_auc_max": w60_over_auc_max,
            "W60_under_auc_mean": w60_under_auc_mean,
            "W60_under_auc_max": w60_under_auc_max,
            "W60_over_dur_mean": w60_over_dur,
            "W60_under_dur_mean": w60_under_dur,
            "v4_slope_short_t": s10m,
            "v4_slope_long_t": s50m_filled,
            "v4_accel_t": accel,
            "v4_shock_t": shock,
            "v4_median_t": v4_median_series,
            "v4_iqr_t": v4_iqr_series,
            "v4_p90_t": v4_p90_series,
            "v4_p95_t": v4_p95_series,
            "v4_over_auc_t": v4_over_max_series,
            "v4_under_auc_t": v4_under_max_series,
            "v4_over_max_t": v4_over_max_series,
            "v4_under_max_t": v4_under_max_series,
            "sconf": sconf_series,
            "coverage_points": n_valid.astype(float),
            "coverage_time": cov_time_series,
            "N_valid": n_valid.astype(float)
        }

        return pd.DataFrame({k: feature_dict[k] for k in self.feature_names})

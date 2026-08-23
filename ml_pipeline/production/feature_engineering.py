"""
FrostLink Production ML Architecture -- Feature Engineering Pipeline
=====================================================================
Implements strictly causal, backward-looking time-series feature extraction,
sensor quality indicator generation, missingness/staleness handling, and time alignment.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from feature_schema import PRODUCTION_FEATURE_REGISTRY, FeatureAvailability, FeatureGroup, SCHEMA_VERSION

class ProductionFeaturePipeline:
    def __init__(self, schema_version: str = SCHEMA_VERSION):
        self.schema_version = schema_version
        self.registry = {f.name: f for f in PRODUCTION_FEATURE_REGISTRY}
        
    def align_and_validate_stream(self, df_raw: pd.DataFrame, time_col: str = 'Time', id_col: str = 'shipment_id') -> pd.DataFrame:
        """
        Validates timestamps, removes exact temporal duplicates, and sorts chronologically.
        """
        df = df_raw.copy()
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df['Time_dt'] = pd.to_datetime(df[time_col])
        else:
            df['Time_dt'] = df[time_col]
            
        # Deduplicate on (shipment_id, Time_dt)
        df = df.drop_duplicates(subset=[id_col, 'Time_dt']).sort_values([id_col, 'Time_dt']).reset_index(drop=True)
        return df

    def extract_temporal_features(self, df_aligned: pd.DataFrame, temp_col: str = 'T_mean_t', id_col: str = 'shipment_id') -> pd.DataFrame:
        """
        Extracts strictly causal backward-looking rolling statistics and dynamics.
        NO future rows (t+1, t+2...) are ever accessed.
        """
        df = df_aligned.copy()
        grouped = df.groupby(id_col)
        
        # 1. Thermal State
        df['T_current'] = df[temp_col]
        
        # Spatial features if available in raw telemetry
        if 'spatial_range_t' in df.columns:
            df['T_spatial_range'] = df['spatial_range_t']
        elif 'v4_spatial_range_t' in df.columns:
            df['T_spatial_range'] = df['v4_spatial_range_t']
        else:
            df['T_spatial_range'] = np.nan
            
        if 'spatial_std_t' in df.columns:
            df['T_spatial_std'] = df['spatial_std_t']
        elif 'v4_spatial_std_t' in df.columns:
            df['T_spatial_std'] = df['v4_spatial_std_t']
        else:
            df['T_spatial_std'] = np.nan
            
        # 2. Thermal Dynamics (Causal backward-looking differences)
        # 10m step difference
        df['10m_delta'] = grouped[temp_col].transform(lambda x: x - x.shift(1).fillna(x.iloc[0]))
        df['10m_slope'] = df['10m_delta'] / 10.0
        
        # 30m backward difference (3 steps of 10m)
        df['30m_delta'] = grouped[temp_col].transform(lambda x: x - x.shift(3).fillna(x.iloc[0]))
        df['30m_slope'] = df['30m_delta'] / 30.0
        
        # 60m backward difference (5 steps of 10m -> [t-50m, t])
        df['60m_delta'] = grouped[temp_col].transform(lambda x: x - x.shift(5).fillna(x.iloc[0]))
        df['60m_slope'] = df['60m_delta'] / 50.0
        
        # Thermal acceleration (change in slope over consecutive steps)
        df['thermal_acceleration'] = grouped['10m_slope'].transform(lambda x: x - x.shift(1).fillna(0.0))
        
        # 3. Thermal Stability (Causal rolling windows of 6 steps = 60m backward)
        df['W60_mean'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).mean())
        df['W60_std'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).std().fillna(0.0))
        df['W60_min'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).min())
        df['W60_max'] = grouped[temp_col].transform(lambda x: x.rolling(6, min_periods=1).max())
        df['W60_range'] = df['W60_max'] - df['W60_min']
        
        # Time above R1 warning threshold in past 60m (cumulative minutes)
        df['time_above_warning_threshold_60m'] = grouped[temp_col].transform(
            lambda x: (x > 3.0).astype(float).rolling(6, min_periods=1).sum() * 10.0
        )
        
        # 4. Sensor Quality Indicators
        df['temp_sensor_valid'] = ((df[temp_col].notna()) & (df[temp_col] >= -30.0) & (df[temp_col] <= 60.0)).astype(int)
        time_diff_sec = grouped['Time_dt'].diff().dt.total_seconds().fillna(600.0)
        df['temp_sensor_age_seconds'] = time_diff_sec
        
        return df

    def transform_real_telemetry(self, df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Transforms real Strawberry cold chain data into production feature representations.
        Returns:
            processed_df (DataFrame)
            active_feature_columns (List[str])
        """
        df_aligned = self.align_and_validate_stream(df_raw, time_col='Time', id_col='shipment_id')
        df_features = self.extract_temporal_features(df_aligned, temp_col='T_mean_t', id_col='shipment_id')
        
        # Select active features available in real telemetry
        active_features = [
            f.name for f in PRODUCTION_FEATURE_REGISTRY 
            if f.availability in [FeatureAvailability.CURRENT_REAL, FeatureAvailability.DERIVED_TEMPORAL]
            and f.name in df_features.columns
        ]
        
        # Ensure schema metadata is stamped
        df_features['schema_version'] = self.schema_version
        return df_features, active_features

    def transform_multimodal_telemetry(self, df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Transforms full multimodal hardware telemetry streams (including door, compressor, ambient, vehicle).
        Handles missingness, stale limits, and indicator flags.
        """
        df_aligned = self.align_and_validate_stream(df_raw, time_col='Time', id_col='shipment_id')
        
        # Determine primary temperature column
        temp_col = 'observed_temp' if 'observed_temp' in df_aligned.columns else 'T_mean_t'
        df = self.extract_temporal_features(df_aligned, temp_col=temp_col, id_col='shipment_id')
        
        # Multimodal Hardware Mapping & Staleness Handling
        # 1. Refrigeration
        if 'observed_compressor_state' in df.columns:
            df['compressor_state'] = df['observed_compressor_state']
            df['compressor_duty_cycle_60m'] = df.groupby('shipment_id')['observed_compressor_duty_cycle'].transform(
                lambda x: x.rolling(6, min_periods=1).mean()
            )
            df['compressor_current'] = df.get('observed_refrigeration_current', np.nan)
            df['compressor_sensor_valid'] = df['observed_compressor_state'].notna().astype(int)
        else:
            df['compressor_state'] = np.nan
            df['compressor_duty_cycle_60m'] = np.nan
            df['compressor_current'] = np.nan
            df['compressor_sensor_valid'] = 0
            
        # 2. Door Telemetry
        if 'observed_door_state' in df.columns:
            df['door_state'] = df['observed_door_state']
            df['door_open_duration_current'] = df.get('door_open_duration_min', np.nan)
            df['door_sensor_valid'] = df['observed_door_state'].notna().astype(int)
        else:
            df['door_state'] = np.nan
            df['door_open_duration_current'] = np.nan
            df['door_sensor_valid'] = 0
            
        # 3. Ambient Telemetry
        if 'observed_ambient_temp' in df.columns:
            df['ambient_temperature'] = df['observed_ambient_temp']
            df['ambient_humidity'] = df.get('observed_humidity', np.nan)
            df['thermal_gradient_ambient_cargo'] = df['ambient_temperature'] - df['T_current']
        else:
            df['ambient_temperature'] = np.nan
            df['ambient_humidity'] = np.nan
            df['thermal_gradient_ambient_cargo'] = np.nan
            
        # 4. Vehicle Telemetry
        if 'observed_vehicle_speed' in df.columns:
            df['vehicle_speed'] = df['observed_vehicle_speed']
            df['vehicle_stationary_duration'] = df.get('vehicle_stationary_duration_min', np.nan)
            df['gps_valid'] = df['observed_vehicle_speed'].notna().astype(int)
        else:
            df['vehicle_speed'] = np.nan
            df['vehicle_stationary_duration'] = np.nan
            df['gps_valid'] = 0
            
        # 5. Power Telemetry
        if 'observed_battery_voltage' in df.columns:
            df['battery_voltage'] = df['observed_battery_voltage']
            if 'observed_refrigeration_current' in df.columns:
                df['refrigeration_power_watts'] = df['observed_battery_voltage'] * df['observed_refrigeration_current']
            else:
                df['refrigeration_power_watts'] = np.nan
        else:
            df['battery_voltage'] = np.nan
            df['refrigeration_power_watts'] = np.nan
            
        multimodal_features = [f.name for f in PRODUCTION_FEATURE_REGISTRY if f.name in df.columns]
        df['schema_version'] = self.schema_version
        return df, multimodal_features

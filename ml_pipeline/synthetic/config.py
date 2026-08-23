"""
FrostLink Synthetic Telemetry Engine -- Configuration Module
============================================================
Defines data structures, scenario definitions, physical constants, and noise parameters.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np

@dataclass
class ThermalParameters:
    # Setpoint
    setpoint_temp: float = 2.0  # Optimal strawberry storage temp (deg C)
    
    # Heat transfer coefficients (1 / min or deg C / min)
    # Calibrated to real transport refrigeration insulation values:
    k_ambient: float = 0.0012     # Passive conduction through container insulation (0.28C / 10m in 25C ambient)
    k_door: float = 0.0150        # Convective exchange during door open (1.5C / 10m in 25C ambient)
    k_traffic: float = 0.0010     # Stationary vehicle heat soak (deg C / min)
    
    # Active Cooling
    max_cooling_rate: float = 0.080  # Max active cooling rate at 100% duty (0.80C / 10m)
    
    # Environmental & System
    ambient_normal_range: Tuple[float, float] = (18.0, 28.0)
    ambient_hot_range: Tuple[float, float] = (32.0, 42.0)
    
    # Battery & Power
    battery_voltage_healthy: Tuple[float, float] = (12.4, 13.8)
    battery_voltage_fault: Tuple[float, float] = (9.5, 11.2)
    current_active_cooling: Tuple[float, float] = (12.0, 18.0)
    current_idle: Tuple[float, float] = (0.5, 1.5)

@dataclass
class NoiseParameters:
    temp_noise_std: float = 0.15          # Measurement noise (deg C)
    ambient_noise_std: float = 0.30       # Ambient sensor noise (deg C)
    humidity_noise_std: float = 1.0       # Relative humidity noise (%)
    voltage_noise_std: float = 0.05       # Battery voltage noise (V)
    current_noise_std: float = 0.20       # Compressor current noise (A)
    
    # Dropout probabilities (missing sensor data simulation)
    gps_dropout_prob: float = 0.02
    door_sensor_dropout_prob: float = 0.01
    compressor_telemetry_dropout_prob: float = 0.01

@dataclass
class GenerationConfig:
    random_seed: int = 42
    n_shipments: int = 100
    shipment_duration_hours: int = 48    # 48 hours per shipment
    sampling_interval_min: int = 10      # 10-minute cadence (matches Strawberry dataset)
    output_dir: str = "ml_pipeline/synthetic/data"
    
    # Distribution across the 12 scenarios
    scenario_distribution: Dict[str, float] = field(default_factory=lambda: {
        'SCENARIO_1_NORMAL': 0.15,
        'SCENARIO_2_HOT_AMBIENT_HEALTHY': 0.10,
        'SCENARIO_3_TRAFFIC_HEALTHY': 0.10,
        'SCENARIO_4_DOOR_OPENING': 0.10,
        'SCENARIO_5_COMPRESSOR_DEGRADATION': 0.08,
        'SCENARIO_6_COMPRESSOR_FAILURE': 0.08,
        'SCENARIO_7_POWER_INTERRUPTION': 0.07,
        'SCENARIO_8_DOOR_HOT_AMBIENT': 0.08,
        'SCENARIO_9_TRAFFIC_HOT_HEALTHY': 0.08,
        'SCENARIO_10_TRAFFIC_HOT_DEGRADED': 0.06,
        'SCENARIO_11_RECOVERY': 0.05,
        'SCENARIO_12_COMBINED_FAILURE': 0.05
    })

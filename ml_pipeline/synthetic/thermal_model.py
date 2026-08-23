"""
FrostLink Physics-Informed Synthetic Telemetry Engine -- Thermal Model (Phase 16A)
==================================================================================
Models continuous 1st-principles discrete-time thermal evolution:
  T_{t+1} = T_t + dQ_ambient + dQ_door + dQ_traffic - dQ_cooling + thermal_noise

Key Features:
- State-persistent cooling efficiency: NORMAL, DEGRADED, SEVERELY_DEGRADED, FAILED.
- Multi-probe 3D spatial gradient dispersion across 9 probe locations (Front/Mid/Rear x Top/Mid/Bot).
- Physical insulation conduction, convective door exchange, and stationary solar traffic soak.
- Bounded measurement noise and sensor dropouts without arbitrary synthetic fabrication.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
from enum import Enum

class CoolingState(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    SEVERELY_DEGRADED = "SEVERELY_DEGRADED"
    FAILED = "FAILED"

@dataclass
class PhysicsParameters:
    # Setpoint
    setpoint_celsius: float = 2.0  # Optimal strawberry storage temperature
    
    # Heat transfer coefficients (min^-1 or deg C / min)
    # [Simulation Assumption: Calibrated to commercial 40ft refrigerated container insulation]
    k_ambient: float = 0.0012   # Passive insulation conduction (0.28°C / 10m at 25°C ambient)
    k_door: float = 0.0150      # Convective exchange during door open (1.5°C / 10m at 25°C ambient)
    k_traffic: float = 0.0010   # Stationary vehicle solar thermal soak (°C / min)
    
    # Active refrigeration cooling power (°C / min at 100% capacity)
    max_cooling_rate: float = 0.080  # Max pull-down capability (0.80°C / 10m)
    
    # Spatial gradient offsets across 9 probe positions (relative to cargo core)
    # Top probes warmer due to buoyancy (+0.4°C); Rear probes warmer due to air circulation drop (+0.3°C)
    spatial_offsets: Dict[str, float] = None
    
    def __post_init__(self):
        if self.spatial_offsets is None:
            self.spatial_offsets = {
                "Front_Top": 0.25,
                "Front_Middle": -0.05,
                "Front_Bottom": -0.25,
                "Middle_Top": 0.35,
                "Middle_Middle": 0.00,
                "Middle_Bottom": -0.20,
                "Rear_Top": 0.55,
                "Rear_Middle": 0.20,
                "Rear_Bottom": 0.05
            }

class PhysicsThermalModel:
    def __init__(self, params: Optional[PhysicsParameters] = None):
        self.params = params or PhysicsParameters()

    def get_cooling_effectiveness(self, state: CoolingState, rng: np.random.RandomState) -> float:
        """Returns continuous cooling efficiency based on persistent mechanical state."""
        if state == CoolingState.NORMAL:
            return float(rng.uniform(0.92, 1.00))
        elif state == CoolingState.DEGRADED:
            return float(rng.uniform(0.45, 0.65))
        elif state == CoolingState.SEVERELY_DEGRADED:
            return float(rng.uniform(0.20, 0.35))
        elif state == CoolingState.FAILED:
            return float(rng.uniform(0.00, 0.05))
        return 1.0

    def step_thermal_state(
        self,
        current_core_temp: float,
        ambient_temp: float,
        door_open: bool,
        is_traffic: bool,
        cooling_state: CoolingState,
        power_available: bool,
        dt_minutes: float = 10.0,
        rng: Optional[np.random.RandomState] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates one discrete physical thermal evolution step.
        """
        if rng is None:
            rng = np.random.RandomState()
            
        # 1. Passive insulation conduction heat load
        dQ_ambient = self.params.k_ambient * (ambient_temp - current_core_temp) * dt_minutes
        
        # 2. Convective door opening heat load
        dQ_door = 0.0
        if door_open:
            dQ_door = self.params.k_door * (ambient_temp - current_core_temp) * dt_minutes
            
        # 3. Traffic / stationary solar radiation heat load
        dQ_traffic = 0.0
        if is_traffic:
            dQ_traffic = self.params.k_traffic * dt_minutes
            
        # 4. Active refrigeration cooling
        dQ_cooling = 0.0
        if power_available and (current_core_temp > self.params.setpoint_celsius - 0.5):
            effectiveness = self.get_cooling_effectiveness(cooling_state, rng)
            # Demand scales with ambient differential and cargo temp
            temp_error = current_core_temp - self.params.setpoint_celsius
            demand = max(0.2, min(1.0, 0.4 + 0.35 * temp_error + 0.015 * max(0.0, ambient_temp - 25.0)))
            
            effective_cooling = self.params.max_cooling_rate * effectiveness * demand * dt_minutes
            # Prevent cooling from over-chilling below freeze protection bound
            max_pull_down = max(0.0, (current_core_temp + dQ_ambient + dQ_door + dQ_traffic) - (self.params.setpoint_celsius - 0.5))
            dQ_cooling = min(effective_cooling, max_pull_down)
            
        # 5. Thermal disturbance noise (small natural micro-turbulence jitter)
        thermal_jitter = float(rng.normal(0.0, 0.015))
        
        # Next physical core temperature
        next_core_temp = current_core_temp + dQ_ambient + dQ_door + dQ_traffic - dQ_cooling + thermal_jitter
        next_core_temp = max(-1.0, next_core_temp) # Freeze limit
        
        thermal_components = {
            "dQ_ambient": dQ_ambient,
            "dQ_door": dQ_door,
            "dQ_traffic": dQ_traffic,
            "dQ_cooling": dQ_cooling,
            "thermal_jitter": thermal_jitter,
            "cooling_effectiveness": self.get_cooling_effectiveness(cooling_state, rng)
        }
        return next_core_temp, thermal_components

    def generate_spatial_probes(
        self,
        core_temp: float,
        ambient_temp: float,
        door_open: bool,
        rng: np.random.RandomState,
        noise_std: float = 0.08,
        dropout_prob: float = 0.0
    ) -> Dict[str, Optional[float]]:
        """
        Generates 9 spatial probe temperature readings based on physical geometry,
        thermal gradient offsets, door proximity, and bounded sensor noise.
        """
        probes = {}
        for probe_name, offset in self.params.spatial_offsets.items():
            # Apply dropout if simulated sensor fault
            if dropout_prob > 0.0 and rng.uniform(0.0, 1.0) < dropout_prob:
                probes[probe_name] = None
                continue
                
            # Additional localized heat ingress at rear door when open
            door_influence = 0.0
            if door_open and "Rear" in probe_name:
                door_influence = 0.6 if "Top" in probe_name else 0.35
                
            # Ambient gradient pull on outer perimeter probes
            ambient_influence = 0.02 * (ambient_temp - core_temp) if "Top" in probe_name else 0.0
            
            # Measurement noise
            sensor_noise = float(rng.normal(0.0, noise_std))
            
            p_val = core_temp + offset + door_influence + ambient_influence + sensor_noise
            probes[probe_name] = round(float(p_val), 3)
            
        return probes

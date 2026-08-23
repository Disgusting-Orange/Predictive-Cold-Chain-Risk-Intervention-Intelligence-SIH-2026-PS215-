"""
FrostLink Physics-Informed Synthetic Telemetry Engine -- Scenario Generator (Phase 16A)
======================================================================================
Generates time-indexed physical disturbance schedules across 13 required operational scenarios.
"""

import numpy as np
from typing import Dict, List, Any
try:
    from .thermal_model import CoolingState
except ImportError:
    from thermal_model import CoolingState

ALL_SCENARIOS = [
    "NORMAL",
    "HIGH_AMBIENT_HEALTHY_COOLING",
    "HIGH_AMBIENT_DEGRADED_COOLING",
    "SHORT_DOOR_OPENING",
    "LONG_DOOR_OPENING",
    "DOOR_PLUS_WEAK_COOLING",
    "HEAVY_TRAFFIC_HEALTHY_COOLING",
    "HEAVY_TRAFFIC_WEAK_COOLING",
    "COOLING_DEGRADATION",
    "COOLING_FAILURE",
    "AMBIENT_SPIKE",
    "SENSOR_NOISE",
    "SENSOR_DROPOUT"
]

class ScenarioScheduleGenerator:
    def __init__(self, rng: np.random.RandomState):
        self.rng = rng

    def generate_schedule(
        self,
        scenario_name: str,
        total_steps: int = 288,  # 48 hours at 10-minute cadence
        dt_minutes: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Generates step-by-step physical boundary conditions for a single shipment trajectory.
        """
        if scenario_name not in ALL_SCENARIOS:
            raise ValueError(f"Unknown scenario: '{scenario_name}'. Must be one of {ALL_SCENARIOS}")
            
        schedule = []
        init_core_temp = float(self.rng.uniform(1.8, 2.4))
        base_ambient = float(self.rng.uniform(21.0, 26.0))
        
        # Diurnal 24h sinusoidal temperature oscillation (amplitude +-3.5°C)
        hours = np.linspace(0.0, total_steps * dt_minutes / 60.0, total_steps)
        diurnal_cycle = 3.5 * np.sin(2.0 * np.pi * (hours - 8.0) / 24.0)
        
        for step in range(total_steps):
            t_hour = step * dt_minutes / 60.0
            
            # Baseline normal conditions
            ambient = base_ambient + diurnal_cycle[step] + float(self.rng.normal(0.0, 0.4))
            door_open = False
            is_traffic = False
            cooling_state = CoolingState.NORMAL
            power_available = True
            noise_std = 0.08
            dropout_prob = 0.0
            vehicle_speed = float(self.rng.uniform(65.0, 85.0))
            
            # -------------------------------------------------------------
            # Scenario-Specific Injections
            # -------------------------------------------------------------
            if scenario_name == "NORMAL":
                pass # Baseline steady run
                
            elif scenario_name == "HIGH_AMBIENT_HEALTHY_COOLING":
                ambient = 36.0 + diurnal_cycle[step] + float(self.rng.normal(0.0, 0.5))
                cooling_state = CoolingState.NORMAL # Healthy cooling counteracts high heat
                
            elif scenario_name == "HIGH_AMBIENT_DEGRADED_COOLING":
                ambient = 37.0 + diurnal_cycle[step] + float(self.rng.normal(0.0, 0.5))
                cooling_state = CoolingState.DEGRADED # 50% capacity -> cannot hold 37C
                
            elif scenario_name == "SHORT_DOOR_OPENING":
                # Door open for 20 minutes at hour 14:00 (steps 84-85)
                if 14.0 <= t_hour < 14.33:
                    door_open = True
                    vehicle_speed = 0.0
                    
            elif scenario_name == "LONG_DOOR_OPENING":
                # Door open for 60 minutes at hour 14:00 to 15:00
                if 14.0 <= t_hour < 15.0:
                    door_open = True
                    vehicle_speed = 0.0
                    
            elif scenario_name == "DOOR_PLUS_WEAK_COOLING":
                # Door open for 30m + degraded cooling
                cooling_state = CoolingState.DEGRADED
                if 14.0 <= t_hour < 14.5:
                    door_open = True
                    vehicle_speed = 0.0
                    
            elif scenario_name == "HEAVY_TRAFFIC_HEALTHY_COOLING":
                # 4-hour stationary traffic jam, healthy cooling
                if 12.0 <= t_hour < 16.0:
                    is_traffic = True
                    vehicle_speed = float(self.rng.uniform(0.0, 8.0))
                    
            elif scenario_name == "HEAVY_TRAFFIC_WEAK_COOLING":
                # Traffic jam with degraded cooling
                if 12.0 <= t_hour < 16.0:
                    is_traffic = True
                    cooling_state = CoolingState.DEGRADED
                    vehicle_speed = float(self.rng.uniform(0.0, 8.0))
                    
            elif scenario_name == "COOLING_DEGRADATION":
                # Progressive mechanical wear starting at hour 10
                if t_hour < 10.0:
                    cooling_state = CoolingState.NORMAL
                elif t_hour < 24.0:
                    cooling_state = CoolingState.DEGRADED
                else:
                    cooling_state = CoolingState.SEVERELY_DEGRADED
                    
            elif scenario_name == "COOLING_FAILURE":
                # Total compressor breakdown at hour 16
                if t_hour >= 16.0:
                    cooling_state = CoolingState.FAILED
                    
            elif scenario_name == "AMBIENT_SPIKE":
                # Transient extreme solar / desert heat spike (+12°C) between hour 13 and 17
                if 13.0 <= t_hour < 17.0:
                    ambient += 12.0
                    
            elif scenario_name == "SENSOR_NOISE":
                noise_std = 0.35 # Elevated sensor jitter without cargo compromise
                
            elif scenario_name == "SENSOR_DROPOUT":
                dropout_prob = 0.15 # 15% random probe measurement loss
                
            schedule.append({
                "step_index": step,
                "t_hour": t_hour,
                "init_core_temp": init_core_temp,
                "ambient_temp": round(ambient, 2),
                "door_open": door_open,
                "is_traffic": is_traffic,
                "cooling_state": cooling_state,
                "power_available": power_available,
                "noise_std": noise_std,
                "dropout_prob": dropout_prob,
                "vehicle_speed": round(vehicle_speed, 1)
            })
            
        return schedule

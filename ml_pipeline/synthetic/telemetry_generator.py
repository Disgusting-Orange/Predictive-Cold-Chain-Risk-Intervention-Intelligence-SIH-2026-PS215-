"""
FrostLink Physics-Informed Synthetic Telemetry Engine -- Telemetry Generator (Phase 16A)
========================================================================================
Executes forward numerical integration of discrete thermal dynamics across shipment trajectories
and emits multi-probe sensor observations matching the FrostLink raw telemetry schema.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    from .thermal_model import PhysicsThermalModel, PhysicsParameters, CoolingState
    from .scenario_generator import ScenarioScheduleGenerator
except ImportError:
    from thermal_model import PhysicsThermalModel, PhysicsParameters, CoolingState
    from scenario_generator import ScenarioScheduleGenerator

class SyntheticTelemetryGenerator:
    def __init__(
        self,
        physics_model: Optional[PhysicsThermalModel] = None,
        random_seed: int = 42
    ):
        self.physics = physics_model or PhysicsThermalModel()
        self.rng = np.random.RandomState(random_seed)
        self.scenario_gen = ScenarioScheduleGenerator(self.rng)

    def generate_shipment_trajectory(
        self,
        shipment_id: str,
        scenario_name: str,
        start_time: str = "2026-06-01T08:00:00Z",
        total_steps: int = 288, # 48 hours at 10-min cadence
        dt_minutes: float = 10.0
    ) -> pd.DataFrame:
        """
        Generates a continuous 48-hour multi-probe raw telemetry sequence for a single shipment.
        """
        schedule = self.scenario_gen.generate_schedule(
            scenario_name=scenario_name,
            total_steps=total_steps,
            dt_minutes=dt_minutes
        )
        
        base_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        current_core_temp = schedule[0]["init_core_temp"]
        
        rows = []
        for step_data in schedule:
            step_idx = step_data["step_index"]
            t_current = base_dt + timedelta(minutes=step_idx * dt_minutes)
            
            # 1. Step physical core thermal state
            next_core_temp, components = self.physics.step_thermal_state(
                current_core_temp=current_core_temp,
                ambient_temp=step_data["ambient_temp"],
                door_open=step_data["door_open"],
                is_traffic=step_data["is_traffic"],
                cooling_state=step_data["cooling_state"],
                power_available=step_data["power_available"],
                dt_minutes=dt_minutes,
                rng=self.rng
            )
            
            # 2. Generate 9 spatial probe readings (with noise & optional dropouts)
            probes = self.physics.generate_spatial_probes(
                core_temp=current_core_temp,
                ambient_temp=step_data["ambient_temp"],
                door_open=step_data["door_open"],
                rng=self.rng,
                noise_std=step_data["noise_std"],
                dropout_prob=step_data["dropout_prob"]
            )
            
            # Calculate sensor packet confidence score
            valid_probes = sum(1 for v in probes.values() if v is not None)
            sconf = round(float(valid_probes) / 9.0, 3)
            
            # 3. Assemble raw observation record
            row_dict = {
                "shipment_id": shipment_id,
                "Time": t_current.strftime("%Y-%m-%d %H:%M:%S"),
                "step_index": step_idx,
                "scenario_name": scenario_name,
                
                # 9 Spatial Sensor Probes
                "Front_Top": probes["Front_Top"],
                "Front_Middle": probes["Front_Middle"],
                "Front_Bottom": probes["Front_Bottom"],
                "Middle_Top": probes["Middle_Top"],
                "Middle_Middle": probes["Middle_Middle"],
                "Middle_Bottom": probes["Middle_Bottom"],
                "Rear_Top": probes["Rear_Top"],
                "Rear_Middle": probes["Rear_Middle"],
                "Rear_Bottom": probes["Rear_Bottom"],
                
                # Telemetry Packet Metadata
                "sconf": sconf,
                "coverage_time": 1.0,
                
                # Auxiliary Sensor Fields
                "ambient_temp": step_data["ambient_temp"],
                "door_open": int(step_data["door_open"]),
                "speed_kmh": step_data["vehicle_speed"],
                "cooling_state": step_data["cooling_state"].value,
                
                # Ground Truth Physical Quantities (For auditing / validation)
                "true_core_temp": round(current_core_temp, 3),
                "cooling_effectiveness": round(components["cooling_effectiveness"], 3)
            }
            rows.append(row_dict)
            current_core_temp = next_core_temp
            
        return pd.DataFrame(rows)

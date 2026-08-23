"""
FrostLink Synthetic Telemetry Engine -- Scenario Definitions
============================================================
Implements 12 reality-grounded operational scenarios and counterfactual generator.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np

class ScenarioEngine:
    def __init__(self, rng: np.random.RandomState = None):
        self.rng = rng or np.random.RandomState(42)
        
    def generate_scenario_schedule(
        self,
        scenario_name: str,
        total_steps: int = 288, # 48 hours at 10-min sampling
        dt_minutes: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Generates the time-indexed physical inputs for a 48-hour shipment trajectory.
        """
        schedule = []
        
        # Base initial conditions
        init_temp = self.rng.uniform(1.8, 2.5) # Initial temperature in safe band
        ambient_base = self.rng.uniform(20.0, 26.0)
        
        # Diurnal ambient variation cycle (24h period)
        hours = np.linspace(0, total_steps * dt_minutes / 60.0, total_steps)
        diurnal_cycle = 4.0 * np.sin(2 * np.pi * (hours - 8.0) / 24.0)
        
        for step in range(total_steps):
            t_hour = step * dt_minutes / 60.0
            
            # Default normal parameters
            ambient = ambient_base + diurnal_cycle[step] + self.rng.normal(0, 0.5)
            door_open = False
            is_traffic = False
            vehicle_speed = self.rng.uniform(60.0, 85.0)
            compressor_on = True
            duty_cycle = 0.60
            compressor_effectiveness = 1.0 # 100% healthy
            power_available = True
            
            # -------------------------------------------------------------
            # SCENARIO-SPECIFIC DYNAMICS INJECTIONS
            # -------------------------------------------------------------
            if scenario_name == 'SCENARIO_1_NORMAL':
                # Baseline steady run
                duty_cycle = 0.50 + 0.20 * max(0.0, (ambient - 20.0) / 15.0)
                
            elif scenario_name == 'SCENARIO_2_HOT_AMBIENT_HEALTHY':
                # Ambient is very hot (35C - 42C), but cooling is 100% healthy
                ambient = 36.0 + diurnal_cycle[step] + self.rng.normal(0, 0.5)
                duty_cycle = 0.90 # high duty cycle compensates
                
            elif scenario_name == 'SCENARIO_3_TRAFFIC_HEALTHY':
                # Traffic jam between hour 12 and 16
                if 12.0 <= t_hour <= 16.0:
                    is_traffic = True
                    vehicle_speed = self.rng.uniform(0.0, 10.0)
                    duty_cycle = 0.80
                    
            elif scenario_name == 'SCENARIO_4_DOOR_OPENING':
                # Door open between hour 14:00 and 14:40 (4 steps), then closed
                if 14.0 <= t_hour <= 14.67:
                    door_open = True
                    vehicle_speed = 0.0
                    
            elif scenario_name == 'SCENARIO_5_COMPRESSOR_DEGRADATION':
                # Gradual degradation starting at hour 10
                if t_hour > 10.0:
                    degrad_progress = min(1.0, (t_hour - 10.0) / 20.0)
                    compressor_effectiveness = 1.0 - 0.70 * degrad_progress # drops to 0.30
                duty_cycle = 1.0 # running continuously but degraded
                
            elif scenario_name == 'SCENARIO_6_COMPRESSOR_FAILURE':
                # Sharp mechanical failure at hour 15
                if t_hour >= 15.0:
                    compressor_effectiveness = 0.0
                    compressor_on = False
                    
            elif scenario_name == 'SCENARIO_7_POWER_INTERRUPTION':
                # Battery / power outage between hour 12 and 18
                if 12.0 <= t_hour <= 18.0:
                    power_available = False
                    compressor_on = False
                    
            elif scenario_name == 'SCENARIO_8_DOOR_HOT_AMBIENT':
                # Hot ambient + door opening at hour 14
                ambient = 37.0 + diurnal_cycle[step]
                if 14.0 <= t_hour <= 14.8:
                    door_open = True
                    vehicle_speed = 0.0
                    
            elif scenario_name == 'SCENARIO_9_TRAFFIC_HOT_HEALTHY':
                # Hot ambient + traffic jam, but healthy cooling
                ambient = 37.0 + diurnal_cycle[step]
                if 12.0 <= t_hour <= 18.0:
                    is_traffic = True
                    vehicle_speed = self.rng.uniform(0.0, 8.0)
                duty_cycle = 0.95
                
            elif scenario_name == 'SCENARIO_10_TRAFFIC_HOT_DEGRADED':
                # Hot ambient + traffic + degraded compressor (eta = 0.35)
                ambient = 37.0 + diurnal_cycle[step]
                if 12.0 <= t_hour <= 18.0:
                    is_traffic = True
                    vehicle_speed = self.rng.uniform(0.0, 8.0)
                compressor_effectiveness = 0.35
                duty_cycle = 1.0
                
            elif scenario_name == 'SCENARIO_11_RECOVERY':
                # Start in elevated state or degrade temporarily, then 100% cooling kicks in
                if t_hour < 12.0:
                    compressor_effectiveness = 0.20 # struggling
                else:
                    compressor_effectiveness = 1.0 # fixed/serviced
                    duty_cycle = 1.0
                    
            elif scenario_name == 'SCENARIO_12_COMBINED_FAILURE':
                # Extreme compounded failure at hour 12
                ambient = 38.0 + diurnal_cycle[step]
                if t_hour >= 12.0:
                    is_traffic = True
                    vehicle_speed = 0.0
                    compressor_effectiveness = 0.0
                    compressor_on = False
                if 12.5 <= t_hour <= 13.5:
                    door_open = True
                    
            step_dict = {
                'step': step,
                't_hour': t_hour,
                'ambient_temp': ambient,
                'door_open': door_open,
                'is_traffic': is_traffic,
                'vehicle_speed': vehicle_speed,
                'compressor_on': compressor_on,
                'duty_cycle': duty_cycle,
                'compressor_effectiveness': compressor_effectiveness,
                'power_available': power_available,
                'init_temp': init_temp
            }
            schedule.append(step_dict)
            
        return schedule

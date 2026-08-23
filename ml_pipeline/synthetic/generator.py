"""
FrostLink Synthetic Telemetry Engine -- Fleet Generator
========================================================
Generates a controlled pilot of 100 reproducible synthetic shipments.
Saves datasets to ml_pipeline/synthetic/data/ and exports generation_config.json.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from config import GenerationConfig, ThermalParameters, NoiseParameters
from thermal_model import DiscreteThermalModel
from scenarios import ScenarioEngine

class FleetGenerator:
    def __init__(self, config: GenerationConfig = None):
        self.config = config or GenerationConfig()
        self.rng = np.random.RandomState(self.config.random_seed)
        self.thermal_model = DiscreteThermalModel()
        self.scenario_engine = ScenarioEngine(self.rng)
        
    def generate_single_shipment(
        self,
        shipment_id: str,
        scenario_name: str,
        start_timestamp: pd.Timestamp = pd.Timestamp("2026-06-01 08:00:00")
    ) -> pd.DataFrame:
        """
        Generates a complete 48-hour synthetic shipment trajectory.
        """
        total_steps = int(self.config.shipment_duration_hours * 60 / self.config.sampling_interval_min)
        schedule = self.scenario_engine.generate_scenario_schedule(
            scenario_name=scenario_name,
            total_steps=total_steps,
            dt_minutes=float(self.config.sampling_interval_min)
        )
        
        records = []
        current_true_temp = schedule[0]['init_temp']
        door_open_duration = 0.0
        stationary_duration = 0.0
        
        for step_idx, step_input in enumerate(schedule):
            t_current = start_timestamp + pd.Timedelta(minutes=step_idx * self.config.sampling_interval_min)
            
            # Update physical durations
            if step_input['door_open']:
                door_open_duration += self.config.sampling_interval_min
            else:
                door_open_duration = 0.0
                
            if step_input['vehicle_speed'] < 5.0:
                stationary_duration += self.config.sampling_interval_min
            else:
                stationary_duration = 0.0
                
            # Step physical thermal dynamics
            next_true_temp, components = self.thermal_model.step_physical_temperature(
                current_temp=current_true_temp,
                ambient_temp=step_input['ambient_temp'],
                door_open=step_input['door_open'],
                is_traffic=step_input['is_traffic'],
                compressor_on=step_input['compressor_on'],
                duty_cycle=step_input['duty_cycle'],
                compressor_effectiveness=step_input['compressor_effectiveness'],
                power_available=step_input['power_available'],
                dt_minutes=float(self.config.sampling_interval_min),
                rng=self.rng
            )
            
            # Generate sensor observations (with noise & dropout)
            obs = self.thermal_model.generate_sensor_observations(
                true_temp=current_true_temp,
                true_ambient=step_input['ambient_temp'],
                true_door_open=step_input['door_open'],
                door_open_duration_m=door_open_duration,
                true_vehicle_speed=step_input['vehicle_speed'],
                stationary_duration_m=stationary_duration,
                true_compressor_on=step_input['compressor_on'],
                true_duty_cycle=step_input['duty_cycle'],
                true_compressor_effectiveness=step_input['compressor_effectiveness'],
                true_power_available=step_input['power_available'],
                is_traffic=step_input['is_traffic'],
                rng=self.rng
            )
            
            # Physical state record
            record = {
                'shipment_id': shipment_id,
                'scenario_name': scenario_name,
                'Time': t_current.strftime('%Y-%m-%d %H:%M:%S'),
                'step_index': step_idx,
                
                # Ground truth physical state
                'true_cargo_temp': current_true_temp,
                'true_ambient_temp': step_input['ambient_temp'],
                'true_door_open': int(step_input['door_open']),
                'true_vehicle_speed': step_input['vehicle_speed'],
                'true_compressor_on': int(step_input['compressor_on']),
                'true_duty_cycle': step_input['duty_cycle'],
                'true_compressor_effectiveness': step_input['compressor_effectiveness'],
                'true_power_available': int(step_input['power_available']),
                
                # Observed Telemetry
                **obs
            }
            records.append(record)
            current_true_temp = next_true_temp
            
        df_ship = pd.DataFrame(records)
        
        # -------------------------------------------------------------
        # GROUND TRUTH TARGET GENERATION (Derived from True Physical Temp)
        # -------------------------------------------------------------
        # Current risk level: 0.0 (Safe <=3.0C), 1.0 (Warning 3.0-4.0C), 2.0 (Excursion >4.0C)
        df_ship['risk_level'] = 0.0
        df_ship.loc[df_ship['true_cargo_temp'] > 3.0, 'risk_level'] = 1.0
        df_ship.loc[df_ship['true_cargo_temp'] > 4.0, 'risk_level'] = 2.0
        
        # Future 60-min excursion target: Lookahead of 6 steps (60 min)
        # y_next_60_R2 = 1 if max true temp in (t, t+60m] > 4.0C
        forward_window = 6
        rolling_max_future = df_ship['true_cargo_temp'].iloc[::-1].rolling(window=forward_window, closed='left').max().iloc[::-1]
        df_ship['y_next_60_R2'] = (rolling_max_future > 4.0).astype(float)
        # Last 6 rows cannot look ahead full 60 min -> set to NaN
        df_ship.loc[df_ship.index[-forward_window:], 'y_next_60_R2'] = np.nan
        
        return df_ship

    def generate_fleet(self) -> pd.DataFrame:
        """
        Generates full 100-shipment fleet according to scenario distribution.
        """
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        scenario_list = list(self.config.scenario_distribution.keys())
        scenario_probs = list(self.config.scenario_distribution.values())
        # Normalize probabilities
        scenario_probs = np.array(scenario_probs) / sum(scenario_probs)
        
        assigned_scenarios = self.rng.choice(
            scenario_list,
            size=self.config.n_shipments,
            p=scenario_probs
        )
        
        all_shipments = []
        shipment_meta = []
        
        print(f"Generating {self.config.n_shipments} synthetic shipments...")
        for i, sc_name in enumerate(assigned_scenarios, 1):
            sid = f"SYNTH_SHIP_{i:03d}"
            df_s = self.generate_single_shipment(shipment_id=sid, scenario_name=sc_name)
            all_shipments.append(df_s)
            
            # Save individual shipment CSV
            s_path = os.path.join(self.config.output_dir, f"{sid}.csv")
            df_s.to_csv(s_path, index=False)
            
            excursion_rate = (df_s['risk_level'] == 2.0).mean() * 100.0
            shipment_meta.append({
                'shipment_id': sid,
                'scenario': sc_name,
                'rows': len(df_s),
                'mean_true_temp': float(df_s['true_cargo_temp'].mean()),
                'max_true_temp': float(df_s['true_cargo_temp'].max()),
                'pct_excursion': float(excursion_rate)
            })
            
        full_fleet_df = pd.concat(all_shipments, ignore_index=True)
        combined_path = os.path.join(self.config.output_dir, "synthetic_fleet_100.csv")
        full_fleet_df.to_csv(combined_path, index=False)
        print(f"Fleet generation complete! Combined shape: {full_fleet_df.shape}. Saved to: {combined_path}")
        
        # Save generation configuration JSON
        config_dict = {
            'random_seed': self.config.random_seed,
            'n_shipments': self.config.n_shipments,
            'shipment_duration_hours': self.config.shipment_duration_hours,
            'sampling_interval_min': self.config.sampling_interval_min,
            'scenario_distribution': self.config.scenario_distribution,
            'scenario_counts': pd.Series(assigned_scenarios).value_counts().to_dict(),
            'thermal_parameters': vars(self.thermal_model.tp),
            'noise_parameters': vars(self.thermal_model.np),
            'output_combined_file': combined_path
        }
        with open(r"ml_pipeline\synthetic\generation_config.json", 'w') as f:
            json.dump(config_dict, f, indent=2)
            
        return full_fleet_df

if __name__ == "__main__":
    generator = FleetGenerator()
    fleet_df = generator.generate_fleet()

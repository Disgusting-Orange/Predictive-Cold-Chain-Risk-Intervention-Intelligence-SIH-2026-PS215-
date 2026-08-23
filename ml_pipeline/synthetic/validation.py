"""
FrostLink Synthetic Telemetry Engine -- Validation Suite
=========================================================
Executes:
1. 10 Physical Plausibility Checks.
2. 4 Automated Counterfactual Validation Tests.
3. Real vs. Synthetic Distribution Comparison.
4. Generation of diagnostic trajectory plots.
"""

import os
import json
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from generator import FleetGenerator
from scenarios import ScenarioEngine

class SyntheticValidator:
    def __init__(self, fleet_df: pd.DataFrame = None):
        if fleet_df is None:
            combined_path = r"ml_pipeline\synthetic\data\synthetic_fleet_100.csv"
            if os.path.exists(combined_path):
                self.fleet_df = pd.read_csv(combined_path)
            else:
                gen = FleetGenerator()
                self.fleet_df = gen.generate_fleet()
        else:
            self.fleet_df = fleet_df
            
        os.makedirs(r"ml_pipeline\synthetic\validation_plots", exist_ok=True)
        
    def run_physical_checks(self) -> Dict[str, Any]:
        """
        Validates the 10 physical principles across the generated fleet.
        """
        results = {}
        
        # 1. Temperature remains physically plausible (between -2C and 45C)
        min_temp = self.fleet_df['true_cargo_temp'].min()
        max_temp = self.fleet_df['true_cargo_temp'].max()
        p1 = bool(-2.0 <= min_temp and max_temp <= 45.0)
        results['1_temperature_plausible'] = {
            'passed': p1, 'min_temp': float(min_temp), 'max_temp': float(max_temp),
            'rule': '-2.0C <= T <= 45.0C'
        }
        
        # 2. Healthy cooling maintains safe range in normal conditions
        normal_ships = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_1_NORMAL']
        p2 = bool(normal_ships['true_cargo_temp'].max() <= 3.0)
        results['2_healthy_cooling_normal'] = {
            'passed': p2, 'max_temp_normal': float(normal_ships['true_cargo_temp'].max()),
            'mean_temp_normal': float(normal_ships['true_cargo_temp'].mean())
        }
        
        # 3. Hot ambient alone does not cause failure
        hot_healthy = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_2_HOT_AMBIENT_HEALTHY']
        # Max temp should remain below 4.0C (no R2 excursion)
        p3 = bool((hot_healthy['risk_level'] == 2.0).sum() == 0)
        results['3_hot_ambient_alone_safe'] = {
            'passed': p3, 'max_temp': float(hot_healthy['true_cargo_temp'].max()),
            'r2_excursion_count': int((hot_healthy['risk_level'] == 2.0).sum())
        }
        
        # 4. Traffic alone does not cause failure
        traffic_healthy = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_3_TRAFFIC_HEALTHY']
        p4 = bool((traffic_healthy['risk_level'] == 2.0).sum() == 0)
        results['4_traffic_alone_safe'] = {
            'passed': p4, 'max_temp': float(traffic_healthy['true_cargo_temp'].max()),
            'r2_excursion_count': int((traffic_healthy['risk_level'] == 2.0).sum())
        }
        
        # 5. Door opening produces thermal rise followed by post-close recovery
        door_ships = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_4_DOOR_OPENING']
        # Temperature during door open > baseline, and final temperature returns close to setpoint
        mean_open_t = door_ships[door_ships['true_door_open'] == 1]['true_cargo_temp'].mean()
        mean_post_t = door_ships.groupby('shipment_id').tail(12)['true_cargo_temp'].mean()
        p5 = bool(mean_open_t > 2.8 and mean_post_t < 2.5)
        results['5_door_disturbance_recovery'] = {
            'passed': p5, 'mean_temp_during_door_open': float(mean_open_t),
            'mean_final_recovered_temp': float(mean_post_t)
        }
        
        # 6. Compressor degradation produces sustained thermal rise
        degrad_ships = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_5_COMPRESSOR_DEGRADATION']
        final_degrad_temp = degrad_ships.groupby('shipment_id').tail(12)['true_cargo_temp'].mean()
        p6 = bool(final_degrad_temp > 3.5)
        results['6_compressor_degradation_rise'] = {
            'passed': p6, 'mean_final_temp': float(final_degrad_temp)
        }
        
        # 7. Compressor failure produces severe excursion
        fail_ships = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_6_COMPRESSOR_FAILURE']
        fail_r2_pct = (fail_ships['risk_level'] == 2.0).mean() * 100.0
        p7 = bool(fail_r2_pct > 30.0)
        results['7_compressor_failure_severity'] = {
            'passed': p7, 'pct_excursion_steps': float(fail_r2_pct),
            'max_temp': float(fail_ships['true_cargo_temp'].max())
        }
        
        # 8. Recovery scenario returns to safe baseline
        rec_ships = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_11_RECOVERY']
        mid_temp = rec_ships[rec_ships['step_index'] == 72]['true_cargo_temp'].mean() # at 12h
        end_temp = rec_ships.groupby('shipment_id').tail(12)['true_cargo_temp'].mean()
        p8 = bool(end_temp < mid_temp and end_temp <= 2.8)
        results['8_recovery_behavior'] = {
            'passed': p8, 'midpoint_elevated_temp': float(mid_temp),
            'final_recovered_temp': float(end_temp)
        }
        
        # 9. Combined failure is more severe than individual degradation
        comb_ships = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_12_COMBINED_FAILURE']
        comb_max_t = comb_ships['true_cargo_temp'].max()
        degrad_max_t = degrad_ships['true_cargo_temp'].max()
        p9 = bool(comb_max_t > degrad_max_t)
        results['9_combined_failure_severity'] = {
            'passed': p9, 'combined_max_temp': float(comb_max_t),
            'degraded_max_temp': float(degrad_max_t)
        }
        
        # 10. Sensor noise does not dominate physical signal (SNR > 10)
        signal_var = np.var(self.fleet_df['true_cargo_temp'])
        noise_var = np.var(self.fleet_df['observed_temp'] - self.fleet_df['true_cargo_temp'])
        snr = signal_var / noise_var if noise_var > 0 else 999.0
        p10 = bool(snr > 10.0)
        results['10_sensor_noise_snr'] = {
            'passed': p10, 'snr_ratio': float(snr), 'noise_std': float(np.sqrt(noise_var))
        }
        
        return results

    def run_counterfactual_tests(self) -> Dict[str, Any]:
        """
        Executes controlled counterfactual paired comparisons.
        """
        cf_results = {}
        
        # Test 1: Hot Ambient + Healthy vs Hot Ambient + Degraded
        sc2 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_2_HOT_AMBIENT_HEALTHY']
        sc10 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_10_TRAFFIC_HOT_DEGRADED']
        t1_passed = bool(sc10['true_cargo_temp'].mean() > sc2['true_cargo_temp'].mean() + 1.5)
        cf_results['CF_1_Hot_Healthy_vs_Hot_Degraded'] = {
            'passed': t1_passed,
            'mean_temp_hot_healthy': float(sc2['true_cargo_temp'].mean()),
            'mean_temp_hot_degraded': float(sc10['true_cargo_temp'].mean()),
            'delta': float(sc10['true_cargo_temp'].mean() - sc2['true_cargo_temp'].mean()),
            'expected': 'Degraded cooling under hot ambient must produce significantly higher temperature than healthy cooling.'
        }
        
        # Test 2: Traffic + Healthy vs Traffic + Degraded
        sc3 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_3_TRAFFIC_HEALTHY']
        t2_passed = bool(sc10['true_cargo_temp'].max() > sc3['true_cargo_temp'].max() + 2.0)
        cf_results['CF_2_Traffic_Healthy_vs_Traffic_Degraded'] = {
            'passed': t2_passed,
            'max_temp_traffic_healthy': float(sc3['true_cargo_temp'].max()),
            'max_temp_traffic_degraded': float(sc10['true_cargo_temp'].max()),
            'expected': 'Traffic with healthy cooling stays safe, while traffic with degraded cooling breaches threshold.'
        }
        
        # Test 3: Normal vs Door Open
        sc1 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_1_NORMAL']
        sc4 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_4_DOOR_OPENING']
        t3_passed = bool(sc4['true_cargo_temp'].max() > sc1['true_cargo_temp'].max() + 0.5)
        cf_results['CF_3_Door_Closed_vs_Door_Open'] = {
            'passed': t3_passed,
            'max_temp_normal_closed': float(sc1['true_cargo_temp'].max()),
            'max_temp_door_open': float(sc4['true_cargo_temp'].max()),
            'expected': 'Door opening must generate a distinct thermal peak compared to normal closed-door transit.'
        }
        
        # Test 4: Compressor Failure vs Recovery
        sc6 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_6_COMPRESSOR_FAILURE']
        sc11 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_11_RECOVERY']
        final_sc6 = sc6.groupby('shipment_id').tail(12)['true_cargo_temp'].mean()
        final_sc11 = sc11.groupby('shipment_id').tail(12)['true_cargo_temp'].mean()
        t4_passed = bool(final_sc6 > final_sc11 + 3.0)
        cf_results['CF_4_Failure_vs_Recovery'] = {
            'passed': t4_passed,
            'final_temp_unmitigated_failure': float(final_sc6),
            'final_temp_recovery': float(final_sc11),
            'expected': 'Unmitigated failure remains elevated, while recovery actively cools back down.'
        }
        
        return cf_results

    def compare_against_real_data(self) -> Dict[str, Any]:
        """
        Compares synthetic dataset distributions against real Strawberry data statistics.
        """
        with open(r"ml_pipeline\synthetic\real_data_statistics.json", 'r') as f:
            real_stats = json.load(f)
            
        synth_temp = self.fleet_df['observed_temp'].dropna()
        self.fleet_df['dt_min'] = 10.0
        self.fleet_df['dT'] = self.fleet_df.groupby('shipment_id')['observed_temp'].diff()
        self.fleet_df['slope'] = self.fleet_df['dT'] / 10.0
        synth_slopes = self.fleet_df['slope'].dropna()
        
        comp = {
            'temperature': {
                'real_mean': real_stats['temperature_stats']['mean'],
                'synthetic_mean': float(synth_temp.mean()),
                'real_std': real_stats['temperature_stats']['std'],
                'synthetic_std': float(synth_temp.std()),
                'real_min': real_stats['temperature_stats']['min'],
                'synthetic_min': float(synth_temp.min()),
                'real_max': real_stats['temperature_stats']['max'],
                'synthetic_max': float(synth_temp.max())
            },
            'slopes_deg_per_min': {
                'real_mean_slope': real_stats['step_change_and_slope_stats']['mean_slope'],
                'synthetic_mean_slope': float(synth_slopes.mean()),
                'real_std_slope': real_stats['step_change_and_slope_stats']['std_slope'],
                'synthetic_std_slope': float(synth_slopes.std()),
                'real_p05_slope': real_stats['step_change_and_slope_stats']['p05_slope'],
                'synthetic_p05_slope': float(synth_slopes.quantile(0.05)),
                'real_p95_slope': real_stats['step_change_and_slope_stats']['p95_slope'],
                'synthetic_p95_slope': float(synth_slopes.quantile(0.95))
            },
            'sampling_interval': {
                'real_sampling_cadence_min': real_stats['sampling_interval_stats']['median_interval_min'],
                'synthetic_sampling_cadence_min': 10.0
            }
        }
        return comp

    def generate_validation_plots(self):
        """
        Plots representative trajectories for normal, disturbance, failure, and recovery.
        """
        plt.figure(figsize=(14, 10))
        
        # 1. Normal vs Hot Ambient Healthy
        plt.subplot(2, 2, 1)
        s1 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_1_NORMAL'].iloc[:288]
        s2 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_2_HOT_AMBIENT_HEALTHY'].iloc[:288]
        plt.plot(s1['step_index'] * 10 / 60, s1['true_cargo_temp'], label='Scenario 1: Normal Transit', color='green')
        plt.plot(s2['step_index'] * 10 / 60, s2['true_cargo_temp'], label='Scenario 2: Hot Ambient + Healthy', color='orange')
        plt.axhline(4.0, color='red', linestyle='--', label='R2 Excursion Boundary (4.0°C)')
        plt.title('1. Thermal Regulation Under Normal vs Extreme Ambient')
        plt.xlabel('Hours in Transit')
        plt.ylabel('Cargo Temp (°C)')
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.3)
        
        # 2. Door Open Disturbance vs Traffic
        plt.subplot(2, 2, 2)
        s4 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_4_DOOR_OPENING'].iloc[:288]
        s3 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_3_TRAFFIC_HEALTHY'].iloc[:288]
        plt.plot(s4['step_index'] * 10 / 60, s4['true_cargo_temp'], label='Scenario 4: Door Opening & Recovery', color='purple')
        plt.plot(s3['step_index'] * 10 / 60, s3['true_cargo_temp'], label='Scenario 3: Traffic Jam + Healthy', color='blue')
        plt.axhline(4.0, color='red', linestyle='--')
        plt.title('2. Operational Disturbance: Door vs Traffic')
        plt.xlabel('Hours in Transit')
        plt.ylabel('Cargo Temp (°C)')
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.3)
        
        # 3. Degradation vs Failure vs Combined
        plt.subplot(2, 2, 3)
        s5 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_5_COMPRESSOR_DEGRADATION'].iloc[:288]
        s6 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_6_COMPRESSOR_FAILURE'].iloc[:288]
        s12 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_12_COMBINED_FAILURE'].iloc[:288]
        plt.plot(s5['step_index'] * 10 / 60, s5['true_cargo_temp'], label='Scenario 5: Compressor Degradation', color='goldenrod')
        plt.plot(s6['step_index'] * 10 / 60, s6['true_cargo_temp'], label='Scenario 6: Compressor Failure', color='crimson')
        plt.plot(s12['step_index'] * 10 / 60, s12['true_cargo_temp'], label='Scenario 12: Combined Failure', color='black', linestyle=':')
        plt.axhline(4.0, color='red', linestyle='--')
        plt.title('3. Failure Trajectories: Degradation vs Failure vs Combined')
        plt.xlabel('Hours in Transit')
        plt.ylabel('Cargo Temp (°C)')
        plt.legend(loc='upper left')
        plt.grid(True, alpha=0.3)
        
        # 4. Recovery Scenario
        plt.subplot(2, 2, 4)
        s11 = self.fleet_df[self.fleet_df['scenario_name'] == 'SCENARIO_11_RECOVERY'].iloc[:288]
        plt.plot(s11['step_index'] * 10 / 60, s11['true_cargo_temp'], label='Scenario 11: Active Recovery Trajectory', color='teal')
        plt.plot(s11['step_index'] * 10 / 60, s11['observed_temp'], label='Observed Telemetry with Noise', color='cyan', alpha=0.5)
        plt.axhline(4.0, color='red', linestyle='--')
        plt.title('4. Active Intervention & Physical Recovery')
        plt.xlabel('Hours in Transit')
        plt.ylabel('Cargo Temp (°C)')
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = r"ml_pipeline\synthetic\validation_plots\synthetic_trajectories_overview.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Validation plots saved to {plot_path}")

if __name__ == "__main__":
    validator = SyntheticValidator()
    p_checks = validator.run_physical_checks()
    cf_checks = validator.run_counterfactual_tests()
    real_comp = validator.compare_against_real_data()
    validator.generate_validation_plots()
    
    validation_report = {
        'physical_plausibility_checks': p_checks,
        'counterfactual_tests': cf_checks,
        'real_vs_synthetic_comparison': real_comp
    }
    with open(r"ml_pipeline\synthetic\validation_report.json", 'w') as f:
        json.dump(validation_report, f, indent=2)
        
    print("\n" + "=" * 80)
    print("SYNTHETIC VALIDATION SUITE RESULTS")
    print("=" * 80)
    all_p = all(v['passed'] for v in p_checks.values())
    all_cf = all(v['passed'] for v in cf_checks.values())
    print(f"All 10 Physical Plausibility Checks Passed: {all_p} ({sum(v['passed'] for v in p_checks.values())}/10)")
    print(f"All 4 Counterfactual Tests Passed:         {all_cf} ({sum(v['passed'] for v in cf_checks.values())}/4)")

"""
FrostLink Production ML Architecture -- Feature Schema Definition
==================================================================
Defines typed schemas, feature categories, missingness contracts, and validation rules.
Schema Version: 1.0.0 (Production Multimodal Contract)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import json

class FeatureAvailability(str, Enum):
    CURRENT_REAL = "CURRENT_REAL"          # Available in historical Strawberry telemetry
    FUTURE_HARDWARE = "FUTURE_HARDWARE"    # Reserved for upcoming hardware expansion
    DERIVED_TEMPORAL = "DERIVED_TEMPORAL"  # Computed via causal backward rolling windows
    EXTERNAL = "EXTERNAL"                  # Derived from external services (e.g. weather/traffic API)

class FeatureGroup(str, Enum):
    THERMAL_STATE = "THERMAL_STATE"
    THERMAL_DYNAMICS = "THERMAL_DYNAMICS"
    THERMAL_STABILITY = "THERMAL_STABILITY"
    REFRIGERATION = "REFRIGERATION"
    DOOR = "DOOR"
    AMBIENT = "AMBIENT"
    VEHICLE = "VEHICLE"
    POWER = "POWER"
    SENSOR_QUALITY = "SENSOR_QUALITY"

class MissingnessStrategy(str, Enum):
    NATIVE_PASS_THROUGH = "NATIVE_PASS_THROUGH"   # Tree model handles NaNs natively (no silent imputation)
    FORWARD_FILL_WITH_LIMIT = "FORWARD_FILL_WITH_LIMIT" # Forward fill up to max_stale_minutes, then NaN + is_stale flag
    EXPLICIT_INDICATOR = "EXPLICIT_INDICATOR"     # Emit accompanying _is_missing binary column

@dataclass
class FeatureSpec:
    name: str
    group: FeatureGroup
    availability: FeatureAvailability
    unit: str
    temporal_window: str
    calculation: str
    target_derived: bool = False
    leakage_status: str = "LEAKAGE_SAFE"
    hardware_source: str = "HARDWARE COMPONENT TBD"
    missingness_strategy: MissingnessStrategy = MissingnessStrategy.NATIVE_PASS_THROUGH
    max_stale_minutes: Optional[int] = None
    description: str = ""

SCHEMA_VERSION = "1.0.0"

# Complete Registry of Production Feature Specifications
PRODUCTION_FEATURE_REGISTRY: List[FeatureSpec] = [
    # -------------------------------------------------------------
    # 1. THERMAL STATE (Current Cargo State)
    # -------------------------------------------------------------
    FeatureSpec(
        name="T_current",
        group=FeatureGroup.THERMAL_STATE,
        availability=FeatureAvailability.CURRENT_REAL,
        unit="deg C",
        temporal_window="Instantaneous (t)",
        calculation="Primary cargo probe reading (or spatial mean across probes at t)",
        hardware_source="Multi-point Digital Temperature Probes (e.g., DS18B20 / RTD Pt100)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Instantaneous core strawberry cargo temperature."
    ),
    FeatureSpec(
        name="T_spatial_range",
        group=FeatureGroup.THERMAL_STATE,
        availability=FeatureAvailability.CURRENT_REAL,
        unit="deg C",
        temporal_window="Instantaneous (t)",
        calculation="max(probe_temperatures) - min(probe_temperatures)",
        hardware_source="Multi-probe Container Sensor Grid",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Instantaneous spatial thermal stratification across cargo container."
    ),
    FeatureSpec(
        name="T_spatial_std",
        group=FeatureGroup.THERMAL_STATE,
        availability=FeatureAvailability.CURRENT_REAL,
        unit="deg C",
        temporal_window="Instantaneous (t)",
        calculation="std(probe_temperatures)",
        hardware_source="Multi-probe Container Sensor Grid",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Instantaneous standard deviation across cargo probes."
    ),
    
    # -------------------------------------------------------------
    # 2. THERMAL DYNAMICS (Backward Rate of Change)
    # -------------------------------------------------------------
    FeatureSpec(
        name="10m_delta",
        group=FeatureGroup.THERMAL_DYNAMICS,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C",
        temporal_window="[t-10m, t]",
        calculation="T(t) - T(t-10m)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="10-minute net cargo temperature drift."
    ),
    FeatureSpec(
        name="10m_slope",
        group=FeatureGroup.THERMAL_DYNAMICS,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C / min",
        temporal_window="[t-10m, t]",
        calculation="(T(t) - T(t-10m)) / 10.0",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Instantaneous 10-minute temperature rate of change."
    ),
    FeatureSpec(
        name="30m_delta",
        group=FeatureGroup.THERMAL_DYNAMICS,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C",
        temporal_window="[t-30m, t]",
        calculation="T(t) - T(t-30m)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="30-minute backward net cargo temperature change."
    ),
    FeatureSpec(
        name="30m_slope",
        group=FeatureGroup.THERMAL_DYNAMICS,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C / min",
        temporal_window="[t-30m, t]",
        calculation="(T(t) - T(t-30m)) / 30.0",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="30-minute warming/cooling velocity."
    ),
    FeatureSpec(
        name="60m_delta",
        group=FeatureGroup.THERMAL_DYNAMICS,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C",
        temporal_window="[t-50m, t]",
        calculation="T(t) - T(t-50m)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Trailing 1-hour net temperature drift."
    ),
    FeatureSpec(
        name="60m_slope",
        group=FeatureGroup.THERMAL_DYNAMICS,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C / min",
        temporal_window="[t-50m, t]",
        calculation="(T(t) - T(t-50m)) / 50.0",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Trailing 1-hour temperature slope."
    ),
    FeatureSpec(
        name="thermal_acceleration",
        group=FeatureGroup.THERMAL_DYNAMICS,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C / min^2",
        temporal_window="[t-20m, t]",
        calculation="slope(t) - slope(t-10m)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Second derivative of temperature (acceleration of heating/cooling)."
    ),
    
    # -------------------------------------------------------------
    # 3. THERMAL STABILITY (Backward Rolling Spread & Risk Accumulation)
    # -------------------------------------------------------------
    FeatureSpec(
        name="W60_mean",
        group=FeatureGroup.THERMAL_STABILITY,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C",
        temporal_window="[t-50m, t]",
        calculation="mean(T(tau)) for tau in [t-50m, t]",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Trailing 60-minute mean cargo temperature."
    ),
    FeatureSpec(
        name="W60_std",
        group=FeatureGroup.THERMAL_STABILITY,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C",
        temporal_window="[t-50m, t]",
        calculation="std(T(tau)) for tau in [t-50m, t]",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Trailing 60-minute thermal variance."
    ),
    FeatureSpec(
        name="W60_range",
        group=FeatureGroup.THERMAL_STABILITY,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="deg C",
        temporal_window="[t-50m, t]",
        calculation="max(T(tau)) - min(T(tau)) for tau in [t-50m, t]",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Trailing 60-minute maximum temperature excursion spread."
    ),
    FeatureSpec(
        name="time_above_warning_threshold_60m",
        group=FeatureGroup.THERMAL_STABILITY,
        availability=FeatureAvailability.DERIVED_TEMPORAL,
        unit="minutes",
        temporal_window="[t-50m, t]",
        calculation="sum(10.0 for tau where T(tau) > 3.0C in past 60m)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Cumulative minutes spent above R1 warning threshold in past hour."
    ),
    
    # -------------------------------------------------------------
    # 4. REFRIGERATION TELEMETRY (Future Hardware Modality)
    # -------------------------------------------------------------
    FeatureSpec(
        name="compressor_state",
        group=FeatureGroup.REFRIGERATION,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="binary (0/1)",
        temporal_window="Instantaneous (t)",
        calculation="Direct micro-controller / CAN-bus relay status (1=Active, 0=Off)",
        hardware_source="Reefer CAN-bus / Relay Monitor (HARDWARE COMPONENT TBD)",
        missingness_strategy=MissingnessStrategy.FORWARD_FILL_WITH_LIMIT,
        max_stale_minutes=30,
        description="Active operation state of transport refrigeration compressor."
    ),
    FeatureSpec(
        name="compressor_duty_cycle_60m",
        group=FeatureGroup.REFRIGERATION,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="ratio (0.0 to 1.0)",
        temporal_window="[t-50m, t]",
        calculation="Fraction of time compressor was actively engaged in past 60m",
        hardware_source="TRU Telemetry / Micro-controller Cycle Timer",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="60-minute trailing refrigeration duty cycle."
    ),
    FeatureSpec(
        name="compressor_current",
        group=FeatureGroup.REFRIGERATION,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="Amperes",
        temporal_window="Instantaneous (t)",
        calculation="Current sensor reading on primary compressor motor feed",
        hardware_source="Hall-effect / Shunt Current Sensor (e.g., ACS712 / SCT-013)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Electrical current draw of refrigeration compressor motor."
    ),
    FeatureSpec(
        name="cooling_effectiveness_proxy",
        group=FeatureGroup.REFRIGERATION,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="deg C / (Amp * min)",
        temporal_window="[t-30m, t]",
        calculation="abs(dT / dt) / max(0.1, compressor_current) during active chilling",
        hardware_source="Derived from Current Sensor + Cargo Temperature Probes",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Measured cooling yield per ampere of compressor electrical draw."
    ),
    
    # -------------------------------------------------------------
    # 5. DOOR TELEMETRY (Future Hardware Modality)
    # -------------------------------------------------------------
    FeatureSpec(
        name="door_state",
        group=FeatureGroup.DOOR,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="binary (0/1)",
        temporal_window="Instantaneous (t)",
        calculation="Direct sensor state (1=Open, 0=Closed)",
        hardware_source="Magnetic Reed Switch / Hall Sensor (e.g., MC-38)",
        missingness_strategy=MissingnessStrategy.FORWARD_FILL_WITH_LIMIT,
        max_stale_minutes=15,
        description="Container cargo door open/close status."
    ),
    FeatureSpec(
        name="door_open_duration_current",
        group=FeatureGroup.DOOR,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="minutes",
        temporal_window="Continuous episode up to t",
        calculation="Elapsed continuous minutes in door_state == 1",
        hardware_source="Door Switch Event Timer",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Current ongoing door open duration in minutes."
    ),
    FeatureSpec(
        name="door_open_count_60m",
        group=FeatureGroup.DOOR,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="count",
        temporal_window="[t-50m, t]",
        calculation="Number of door open transitions in past 60 minutes",
        hardware_source="Door Switch Event Logger",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Frequency of door opening events in the trailing hour."
    ),
    FeatureSpec(
        name="time_since_door_close",
        group=FeatureGroup.DOOR,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="minutes",
        temporal_window="Past history up to t",
        calculation="Elapsed minutes since last transition from 1 -> 0",
        hardware_source="Door Switch Event Logger",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Minutes elapsed since the container door was last sealed."
    ),
    
    # -------------------------------------------------------------
    # 6. AMBIENT & ENVIRONMENTAL (Future Hardware Modality)
    # -------------------------------------------------------------
    FeatureSpec(
        name="ambient_temperature",
        group=FeatureGroup.AMBIENT,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="deg C",
        temporal_window="Instantaneous (t)",
        calculation="External ambient temperature sensor reading",
        hardware_source="External Environmental Sensor (e.g., DHT22 / SHT31 / BME280)",
        missingness_strategy=MissingnessStrategy.FORWARD_FILL_WITH_LIMIT,
        max_stale_minutes=30,
        description="Outside environmental temperature surrounding vehicle."
    ),
    FeatureSpec(
        name="ambient_humidity",
        group=FeatureGroup.AMBIENT,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="percent RH",
        temporal_window="Instantaneous (t)",
        calculation="External relative humidity reading",
        hardware_source="External Environmental Sensor (e.g., SHT31 / BME280)",
        missingness_strategy=MissingnessStrategy.FORWARD_FILL_WITH_LIMIT,
        max_stale_minutes=30,
        description="External environmental relative humidity."
    ),
    FeatureSpec(
        name="thermal_gradient_ambient_cargo",
        group=FeatureGroup.AMBIENT,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="deg C",
        temporal_window="Instantaneous (t)",
        calculation="ambient_temperature(t) - T_current(t)",
        hardware_source="Derived from Ambient Sensor + Cargo Temperature Probes",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Driving thermal gradient between ambient air and cargo interior."
    ),
    
    # -------------------------------------------------------------
    # 7. VEHICLE TELEMETRY (Future Hardware Modality)
    # -------------------------------------------------------------
    FeatureSpec(
        name="vehicle_speed",
        group=FeatureGroup.VEHICLE,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="km/h",
        temporal_window="Instantaneous (t)",
        calculation="GPS ground speed / OBD-II vehicle telemetry",
        hardware_source="GPS Module / OBD-II Telematics Unit (e.g., NEO-6M / Teltonika)",
        missingness_strategy=MissingnessStrategy.FORWARD_FILL_WITH_LIMIT,
        max_stale_minutes=15,
        description="Vehicle instantaneous ground speed."
    ),
    FeatureSpec(
        name="vehicle_stationary_duration",
        group=FeatureGroup.VEHICLE,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="minutes",
        temporal_window="Continuous episode up to t",
        calculation="Elapsed continuous minutes with vehicle_speed < 5.0 km/h",
        hardware_source="GPS Telematics Unit",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Continuous duration vehicle has been stationary (traffic/loading)."
    ),
    FeatureSpec(
        name="route_delay_minutes",
        group=FeatureGroup.VEHICLE,
        availability=FeatureAvailability.EXTERNAL,
        unit="minutes",
        temporal_window="Instantaneous (t)",
        calculation="actual_eta - scheduled_eta via routing API",
        hardware_source="Navigation / Routing Telematics Service (HARDWARE COMPONENT TBD)",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Estimated transit delay relative to delivery schedule."
    ),
    
    # -------------------------------------------------------------
    # 8. POWER TELEMETRY (Future Hardware Modality)
    # -------------------------------------------------------------
    FeatureSpec(
        name="battery_voltage",
        group=FeatureGroup.POWER,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="Volts",
        temporal_window="Instantaneous (t)",
        calculation="Auxiliary battery / alternator DC voltage",
        hardware_source="Battery Voltage Sensing Circuit (e.g., Voltage Divider / INA219)",
        missingness_strategy=MissingnessStrategy.FORWARD_FILL_WITH_LIMIT,
        max_stale_minutes=30,
        description="Refrigeration auxiliary battery / power rail voltage."
    ),
    FeatureSpec(
        name="refrigeration_power_watts",
        group=FeatureGroup.POWER,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="Watts",
        temporal_window="Instantaneous (t)",
        calculation="battery_voltage(t) * compressor_current(t)",
        hardware_source="Derived from Voltage + Current Telemetry",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Active instantaneous electrical power consumption of refrigeration unit."
    ),
    
    # -------------------------------------------------------------
    # 9. SENSOR QUALITY & TELEMETRY HEALTH
    # -------------------------------------------------------------
    FeatureSpec(
        name="temp_sensor_valid",
        group=FeatureGroup.SENSOR_QUALITY,
        availability=FeatureAvailability.CURRENT_REAL,
        unit="binary (0/1)",
        temporal_window="Instantaneous (t)",
        calculation="1 if T_current is not null and -30C <= T_current <= 60C, else 0",
        hardware_source="Sensor Health Monitor",
        missingness_strategy=MissingnessStrategy.EXPLICIT_INDICATOR,
        description="Flag indicating valid non-corrupt cargo temperature packet."
    ),
    FeatureSpec(
        name="temp_sensor_age_seconds",
        group=FeatureGroup.SENSOR_QUALITY,
        availability=FeatureAvailability.CURRENT_REAL,
        unit="seconds",
        temporal_window="Instantaneous (t)",
        calculation="Time elapsed since last valid temperature transmission",
        hardware_source="Gateway Timestamp Monitor",
        missingness_strategy=MissingnessStrategy.NATIVE_PASS_THROUGH,
        description="Age of last received temperature telemetry reading."
    ),
    FeatureSpec(
        name="door_sensor_valid",
        group=FeatureGroup.SENSOR_QUALITY,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="binary (0/1)",
        temporal_window="Instantaneous (t)",
        calculation="1 if door_state is not null and reading is within stale limit, else 0",
        hardware_source="Sensor Health Monitor",
        missingness_strategy=MissingnessStrategy.EXPLICIT_INDICATOR,
        description="Flag indicating operational door sensor telemetry."
    ),
    FeatureSpec(
        name="compressor_sensor_valid",
        group=FeatureGroup.SENSOR_QUALITY,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="binary (0/1)",
        temporal_window="Instantaneous (t)",
        calculation="1 if compressor current/state telemetry is active and non-null, else 0",
        hardware_source="Sensor Health Monitor",
        missingness_strategy=MissingnessStrategy.EXPLICIT_INDICATOR,
        description="Flag indicating active compressor current and status telemetry."
    ),
    FeatureSpec(
        name="gps_valid",
        group=FeatureGroup.SENSOR_QUALITY,
        availability=FeatureAvailability.FUTURE_HARDWARE,
        unit="binary (0/1)",
        temporal_window="Instantaneous (t)",
        calculation="1 if GPS lock is acquired and speed is non-null, else 0",
        hardware_source="GPS Receiver Status",
        missingness_strategy=MissingnessStrategy.EXPLICIT_INDICATOR,
        description="Flag indicating valid GPS navigation lock."
    )
]

def export_schema_to_json(filepath: str = "ml_pipeline/production/schema.json"):
    schema_dict = {
        "schema_version": SCHEMA_VERSION,
        "contract_name": "FrostLink Production Multimodal ML Feature Architecture",
        "target_definition": {
            "target_name": "y_next_60_R2",
            "prediction_horizon_minutes": 60,
            "target_condition": "max(T_cargo(tau)) > 4.0 deg C for tau in (t, t+60m]",
            "evaluation_population": "Non-excursion states at prediction time t (risk_level in [0.0, 1.0])",
            "terminal_steps_handling": "Set to NaN for final 60m of shipment (no future lookahead beyond trip end)"
        },
        "feature_count": len(PRODUCTION_FEATURE_REGISTRY),
        "features": [
            {
                "name": f.name,
                "group": f.group.value,
                "availability": f.availability.value,
                "unit": f.unit,
                "temporal_window": f.temporal_window,
                "calculation": f.calculation,
                "hardware_source": f.hardware_source,
                "missingness_strategy": f.missingness_strategy.value,
                "max_stale_minutes": f.max_stale_minutes,
                "target_derived": f.target_derived,
                "leakage_status": f.leakage_status,
                "description": f.description
            }
            for f in PRODUCTION_FEATURE_REGISTRY
        ]
    }
    with open(filepath, 'w') as f:
        json.dump(schema_dict, f, indent=2)
    print(f"Exported production feature schema (v{SCHEMA_VERSION}) to {filepath}")

if __name__ == "__main__":
    export_schema_to_json()

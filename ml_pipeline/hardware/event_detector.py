"""
FrostLink Fast Event Detector -- Phase 18A
===========================================
Performs real-time, low-latency, causal event detection on raw telemetry observations
without modifying or invoking the downstream temporal ML model.

Invariants:
- Uses ONLY information available at current observation time t and historical lookback.
- Strictly NO lookahead (no t+1, no future simulator labels, no ground truth).
- Never fabricates missing sensor values (door state, temperature, humidity).
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import numpy as np
import math

class ObservedEvent(BaseModel):
    event_type: str = Field(..., description="Type of event detected (e.g., RAPID_WARMING, CORRELATED_WARMING, SENSOR_DROPOUT)")
    description: str = Field(..., description="Human-readable summary of observable evidence")
    detected_at: str = Field(..., description="Timestamp of current observation")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Concrete numerical or state measurements supporting the event")

class EventDetectorConfig(BaseModel):
    # Rapid warming rate in °C per minute (e.g. 0.03°C/min = 0.30°C per 10min)
    # Basis: Convective thermal exchange during door open is ~0.15°C/min, while closed-body is ~0.0012°C/min.
    rapid_warming_rate_c_per_min: float = 0.030
    
    # Minimum temperature jump for a single probe to count as warming (°C)
    probe_warming_delta_c: float = 0.10
    
    # Spatial spread limit across probes before flagging suspicious gradient (°C)
    max_spatial_range_c: float = 2.50
    
    # Maximum allowed gap between consecutive observations before flagging stale stream (minutes)
    stale_timeout_minutes: float = 30.0

class FastEventDetector:
    def __init__(self, config: Optional[EventDetectorConfig] = None):
        self.config = config or EventDetectorConfig()

    def detect_events(
        self,
        current_packet_dict: Dict[str, Any],
        previous_packet_dict: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ObservedEvent], Dict[str, Any]]:
        """
        Evaluates current raw telemetry observation and immediate previous observation.
        Returns:
            events: List of detected ObservedEvent instances
            status_meta: Metadata regarding sensor health and feature availability
        """
        events: List[ObservedEvent] = []
        status_meta: Dict[str, Any] = {
            "sensor_health": "HEALTHY",
            "active_probes_count": 0,
            "missing_probes": [],
            "door_monitoring_available": False
        }

        curr_ts_str = current_packet_dict.get("timestamp", "")
        try:
            curr_dt = datetime.fromisoformat(curr_ts_str.replace("Z", "+00:00"))
        except Exception:
            curr_dt = None

        probes_raw = current_packet_dict.get("probes", {})
        valid_probes = {k: float(v) for k, v in probes_raw.items() if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))}
        missing_probes = [k for k, v in probes_raw.items() if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))]
        
        status_meta["active_probes_count"] = len(valid_probes)
        status_meta["missing_probes"] = missing_probes

        # -------------------------------------------------------------
        # 1. Probe Dropout / Degradation Check
        # -------------------------------------------------------------
        if len(valid_probes) == 0:
            status_meta["sensor_health"] = "ERROR_ALL_PROBES_MISSING"
            events.append(ObservedEvent(
                event_type="SENSOR_DROPOUT_TOTAL",
                description="All temperature probes are disconnected or reporting invalid readings",
                detected_at=curr_ts_str,
                evidence={"active_probes": 0, "total_configured": len(probes_raw)}
            ))
            return events, status_meta
        elif len(valid_probes) < len(probes_raw):
            status_meta["sensor_health"] = "DEGRADED"
            events.append(ObservedEvent(
                event_type="SENSOR_DROPOUT",
                description=f"{len(missing_probes)} temperature probe(s) offline: {', '.join(missing_probes)}",
                detected_at=curr_ts_str,
                evidence={"active_probes": len(valid_probes), "missing_probes": missing_probes}
            ))

        # -------------------------------------------------------------
        # 2. Sensor Spatial Disagreement Check
        # -------------------------------------------------------------
        if len(valid_probes) >= 2:
            probe_vals = list(valid_probes.values())
            spatial_range = max(probe_vals) - min(probe_vals)
            if spatial_range > self.config.max_spatial_range_c:
                events.append(ObservedEvent(
                    event_type="SENSOR_DISAGREEMENT",
                    description=f"Significant thermal disparity between probes ({spatial_range:.2f}°C spread exceeds normal {self.config.max_spatial_range_c:.2f}°C limit)",
                    detected_at=curr_ts_str,
                    evidence={
                        "spatial_range_c": round(spatial_range, 3),
                        "max_probe": max(valid_probes, key=valid_probes.get),
                        "max_temp": max(probe_vals),
                        "min_probe": min(valid_probes, key=valid_probes.get),
                        "min_temp": min(probe_vals)
                    }
                ))

        # -------------------------------------------------------------
        # 3. Door State Check (ONLY if physical door sensor is present)
        # -------------------------------------------------------------
        door_val = current_packet_dict.get("door_open")
        if door_val is not None:
            status_meta["door_monitoring_available"] = True
            if bool(door_val) is True:
                events.append(ObservedEvent(
                    event_type="DOOR_OPEN",
                    description="Refrigerated container door is currently OPEN",
                    detected_at=curr_ts_str,
                    evidence={"door_open": True}
                ))
        else:
            status_meta["door_monitoring_available"] = False

        # -------------------------------------------------------------
        # 4. Temporal Delta Checks (Requires previous packet)
        # -------------------------------------------------------------
        if previous_packet_dict and curr_dt is not None:
            prev_ts_str = previous_packet_dict.get("timestamp", "")
            try:
                prev_dt = datetime.fromisoformat(prev_ts_str.replace("Z", "+00:00"))
            except Exception:
                prev_dt = None

            if prev_dt is not None:
                elapsed_sec = (curr_dt - prev_dt).total_seconds()
                elapsed_min = elapsed_sec / 60.0

                # A. Stale Telemetry Check
                if elapsed_sec <= 0:
                    events.append(ObservedEvent(
                        event_type="STALE_TELEMETRY",
                        description=f"Non-advancing or duplicate telemetry timestamp received ({curr_ts_str} <= {prev_ts_str})",
                        detected_at=curr_ts_str,
                        evidence={"current_ts": curr_ts_str, "previous_ts": prev_ts_str, "elapsed_seconds": elapsed_sec}
                    ))
                elif elapsed_min > self.config.stale_timeout_minutes:
                    events.append(ObservedEvent(
                        event_type="STALE_TELEMETRY",
                        description=f"Telemetry transmission gap of {elapsed_min:.1f} minutes exceeds {self.config.stale_timeout_minutes}m threshold",
                        detected_at=curr_ts_str,
                        evidence={"elapsed_minutes": round(elapsed_min, 1), "gap_threshold_min": self.config.stale_timeout_minutes}
                    ))

                # B. Rate-of-Change & Multi-Probe Correlated Warming Check
                if elapsed_min > 0:
                    prev_probes_raw = previous_packet_dict.get("probes", {})
                    prev_valid_probes = {k: float(v) for k, v in prev_probes_raw.items() if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))}
                    
                    # Common probes across t and t-1
                    common_probes = set(valid_probes.keys()).intersection(set(prev_valid_probes.keys()))
                    if len(common_probes) > 0:
                        curr_mean = float(np.mean([valid_probes[p] for p in common_probes]))
                        prev_mean = float(np.mean([prev_valid_probes[p] for p in common_probes]))
                        mean_delta = curr_mean - prev_mean
                        rate_per_min = mean_delta / elapsed_min

                        # Rapid Mean Warming
                        if rate_per_min >= self.config.rapid_warming_rate_c_per_min:
                            events.append(ObservedEvent(
                                event_type="RAPID_WARMING",
                                description=f"Rapid cargo warming detected: +{rate_per_min:.4f}°C/min (+{mean_delta:.2f}°C over {elapsed_min:.1f}m)",
                                detected_at=curr_ts_str,
                                evidence={
                                    "rate_c_per_min": round(rate_per_min, 4),
                                    "delta_t_c": round(mean_delta, 3),
                                    "elapsed_minutes": round(elapsed_min, 1)
                                }
                            ))

                        # Multi-Probe Correlated Warming
                        warming_probes = []
                        for p in common_probes:
                            p_delta = valid_probes[p] - prev_valid_probes[p]
                            if p_delta >= self.config.probe_warming_delta_c:
                                warming_probes.append((p, round(p_delta, 3)))

                        # Trigger only if at least 3 probes AND > 50% of common active probes are warming
                        if len(warming_probes) >= 3 and len(warming_probes) > (len(common_probes) / 2):
                            events.append(ObservedEvent(
                                event_type="CORRELATED_WARMING",
                                description=f"Synchronous warming across {len(warming_probes)} of {len(common_probes)} active temperature probes",
                                detected_at=curr_ts_str,
                                evidence={
                                    "warming_probes_count": len(warming_probes),
                                    "total_common_probes": len(common_probes),
                                    "warming_probes": [wp[0] for wp in warming_probes],
                                    "details": {wp[0]: wp[1] for wp in warming_probes}
                                }
                            ))

        return events, status_meta

"""
FrostLink Hardware Gateway Ingestion Service -- Phase 18A
========================================================
Ingests raw multi-probe packets from ESP32 gateways, executes causal Fast Event Detection,
maintains shipment history buffers, extracts 40 causal features, runs frozen XGBoost v2 + SHAP,
and synthesizes the unified assessment via the Risk Fusion layer.
"""

import sys
import os
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple, Union, List
from datetime import datetime
from pydantic import BaseModel, Field

# Internal imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "feature_engineering")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service")))

from raw_schema import RawTelemetryPacket
from feature_engineer import FrostLinkFeatureEngineer
from validation import validate_raw_packet, validate_feature_vector
from model_service import ModelService
from schemas import PredictionRequest, PredictionResponse

try:
    from .event_detector import FastEventDetector, ObservedEvent
    from .risk_fusion import RiskFusionEngine, FusedRiskAssessment
except ImportError:
    from event_detector import FastEventDetector, ObservedEvent
    from risk_fusion import RiskFusionEngine, FusedRiskAssessment

logger = logging.getLogger("frostlink_hardware_gateway")

class IngestionResult(BaseModel):
    success: bool
    shipment_id: str
    timestamp: str
    cold_start_status: str
    active_probes: int
    fused_state: Optional[str] = None
    observed_events: List[Dict[str, Any]] = Field(default_factory=list)
    risk_probability: Optional[float] = None
    risk_level: Optional[str] = None
    threshold: Optional[float] = None
    prediction_horizon_minutes: Optional[int] = 60
    explanation: Optional[Dict[str, Any]] = None
    fused_assessment: Optional[Dict[str, Any]] = None
    latencies_ms: Dict[str, float] = Field(default_factory=dict)
    error_message: Optional[str] = None

class HardwareGateway:
    def __init__(
        self,
        history_buffer: Optional[Any] = None,
        feature_engineer: Optional[FrostLinkFeatureEngineer] = None,
        model_service: Optional[ModelService] = None,
        event_detector: Optional[FastEventDetector] = None,
        risk_fusion: Optional[RiskFusionEngine] = None,
        log_dir: Optional[str] = None
    ):
        try:
            from .history_buffer import ShipmentHistoryBuffer
        except ImportError:
            from history_buffer import ShipmentHistoryBuffer
        self.history_buffer = history_buffer or ShipmentHistoryBuffer()
        self.feature_engineer = feature_engineer or FrostLinkFeatureEngineer()
        self.model_service = model_service or ModelService.get_instance()
        self.event_detector = event_detector or FastEventDetector()
        self.risk_fusion = risk_fusion or RiskFusionEngine(ml_threshold=self.model_service.operating_threshold)
        self.log_dir = log_dir or os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(self.log_dir, exist_ok=True)

    def process_raw_telemetry(
        self,
        raw_payload: Union[str, Dict[str, Any], RawTelemetryPacket]
    ) -> IngestionResult:
        """
        End-to-end ingestion pipeline:
        1. Parse & validate raw packet
        2. Fast Event Detection (Causal delta against latest previous observation)
        3. Insert into per-shipment history buffer
        4. Extract 40 causal features
        5. Validate feature vector
        6. Conditional XGBoost v2 model inference & SHAP (strictly N >= 6)
        7. Risk Fusion: Synthesize fast events + predictive risk
        8. Measure latency and log data
        """
        t_start = time.perf_counter()
        latencies = {}

        # 1. Parse & Validate Raw Packet
        t0 = time.perf_counter()
        try:
            if isinstance(raw_payload, str):
                payload_dict = json.loads(raw_payload)
                packet = RawTelemetryPacket(**payload_dict)
            elif isinstance(raw_payload, dict):
                packet = RawTelemetryPacket(**raw_payload)
            elif isinstance(raw_payload, RawTelemetryPacket):
                packet = raw_payload
            else:
                raise TypeError(f"Unsupported payload type: {type(raw_payload)}")
        except Exception as e:
            return IngestionResult(
                success=False,
                shipment_id="UNKNOWN",
                timestamp=datetime.utcnow().isoformat() + "Z",
                cold_start_status="ERROR",
                fused_state="ERROR",
                active_probes=0,
                error_message=f"Raw packet validation failed: {str(e)}"
            )

        if not validate_raw_packet(packet.dict()):
            return IngestionResult(
                success=False,
                shipment_id=packet.shipment_id,
                timestamp=packet.timestamp,
                cold_start_status="ERROR",
                fused_state="ERROR",
                active_probes=0,
                error_message="Raw packet failed structural or probe validation (no valid probe readings)."
            )
        latencies["validation_ms"] = (time.perf_counter() - t0) * 1000.0

        # 2. Fast Event Detection (Evaluated before updating history)
        t_evt = time.perf_counter()
        existing_hist = self.history_buffer.get_history(packet.shipment_id)
        prev_packet = existing_hist[-1] if len(existing_hist) > 0 else None
        prev_dict = prev_packet.dict() if prev_packet is not None else None
        
        observed_events, sensor_meta = self.event_detector.detect_events(
            current_packet_dict=packet.dict(),
            previous_packet_dict=prev_dict
        )
        latencies["event_detection_ms"] = (time.perf_counter() - t_evt) * 1000.0

        # 3. Add to History Buffer
        t1 = time.perf_counter()
        self.history_buffer.add_packet(packet)
        history = self.history_buffer.get_history(packet.shipment_id, up_to_timestamp=packet.timestamp)
        latencies["history_buffer_ms"] = (time.perf_counter() - t1) * 1000.0

        # 4. Extract 40 Causal Features
        t2 = time.perf_counter()
        try:
            features_dict, meta = self.feature_engineer.extract_features(
                history=history,
                target_timestamp=packet.timestamp
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                shipment_id=packet.shipment_id,
                timestamp=packet.timestamp,
                cold_start_status="ERROR",
                fused_state="ERROR",
                active_probes=0,
                error_message=f"Feature extraction failure: {str(e)}"
            )
        latencies["feature_engineering_ms"] = (time.perf_counter() - t2) * 1000.0

        # 5. Validate 40 Features
        is_valid, val_err = validate_feature_vector(features_dict, self.feature_engineer.feature_names)
        if not is_valid:
            return IngestionResult(
                success=False,
                shipment_id=packet.shipment_id,
                timestamp=packet.timestamp,
                cold_start_status=meta.get("cold_start_status", "UNKNOWN"),
                fused_state="ERROR",
                active_probes=meta.get("active_probes_count", 0),
                error_message=f"Engineered features failed validation: {val_err}"
            )

        # 6. Cold-Start Safety Policy: Do NOT invoke model inference before 6 valid observations
        if not meta.get("is_inference_allowed", False):
            latencies["inference_and_shap_ms"] = 0.0
            
            # Risk Fusion on Cold-Start
            t_fus = time.perf_counter()
            fused_assessment = self.risk_fusion.fuse(
                shipment_id=packet.shipment_id,
                timestamp=packet.timestamp,
                observed_events=observed_events,
                sensor_meta=sensor_meta,
                cold_start_status="COLD_START",
                ml_prob=None,
                ml_level=None,
                ml_threshold=self.model_service.operating_threshold,
                shap_explanation=None
            )
            latencies["risk_fusion_ms"] = (time.perf_counter() - t_fus) * 1000.0
            latencies["total_pipeline_ms"] = (time.perf_counter() - t_start) * 1000.0
            
            self._log_telemetry_and_prediction(packet, features_dict, None, observed_events, fused_assessment)

            return IngestionResult(
                success=True,
                shipment_id=packet.shipment_id,
                timestamp=packet.timestamp,
                cold_start_status="COLD_START",
                fused_state=fused_assessment.fused_state,
                observed_events=[e.dict() for e in observed_events],
                active_probes=meta.get("active_probes_count", 0),
                risk_probability=None,
                risk_level="INSUFFICIENT_DATA",
                threshold=self.model_service.operating_threshold,
                prediction_horizon_minutes=60,
                explanation=None,
                fused_assessment=fused_assessment.dict(),
                latencies_ms=latencies
            )

        # 7. Invoke Model Inference & SHAP (Only when fully warmed, N >= 6)
        t3 = time.perf_counter()
        try:
            pred_req = PredictionRequest(
                shipment_id=packet.shipment_id,
                timestamp=packet.timestamp,
                features=features_dict
            )
            pred_resp: PredictionResponse = self.model_service.predict_risk(pred_req)
        except Exception as e:
            return IngestionResult(
                success=False,
                shipment_id=packet.shipment_id,
                timestamp=packet.timestamp,
                cold_start_status=meta.get("cold_start_status", "UNKNOWN"),
                fused_state="ERROR",
                active_probes=meta.get("active_probes_count", 0),
                error_message=f"Model inference failed: {str(e)}"
            )
        latencies["inference_and_shap_ms"] = (time.perf_counter() - t3) * 1000.0

        # 8. Risk Fusion: Synthesize Fast Events + XGBoost v2 Predictive Risk
        t_fus = time.perf_counter()
        fused_assessment = self.risk_fusion.fuse(
            shipment_id=packet.shipment_id,
            timestamp=packet.timestamp,
            observed_events=observed_events,
            sensor_meta=sensor_meta,
            cold_start_status=meta.get("cold_start_status", "WARMED"),
            ml_prob=pred_resp.risk_probability,
            ml_level=pred_resp.risk_level.value,
            ml_threshold=pred_resp.threshold,
            shap_explanation=pred_resp.explanation.dict()
        )
        latencies["risk_fusion_ms"] = (time.perf_counter() - t_fus) * 1000.0
        latencies["total_pipeline_ms"] = (time.perf_counter() - t_start) * 1000.0

        # 9. Structured Logging (Raw Telemetry, Events, and ML Predictions)
        self._log_telemetry_and_prediction(packet, features_dict, pred_resp, observed_events, fused_assessment)

        return IngestionResult(
            success=True,
            shipment_id=packet.shipment_id,
            timestamp=packet.timestamp,
            cold_start_status=meta.get("cold_start_status", "WARMED"),
            fused_state=fused_assessment.fused_state,
            observed_events=[e.dict() for e in observed_events],
            active_probes=meta.get("active_probes_count", 0),
            risk_probability=pred_resp.risk_probability,
            risk_level=pred_resp.risk_level.value,
            threshold=pred_resp.threshold,
            prediction_horizon_minutes=pred_resp.prediction_horizon_minutes,
            explanation=pred_resp.explanation.dict(),
            fused_assessment=fused_assessment.dict(),
            latencies_ms=latencies
        )

    def _log_telemetry_and_prediction(
        self,
        packet: RawTelemetryPacket,
        features: Dict[str, Any],
        prediction: Optional[PredictionResponse] = None,
        observed_events: Optional[List[ObservedEvent]] = None,
        fused_assessment: Optional[FusedRiskAssessment] = None
    ):
        """Logs raw packet, fast events, and prediction output separately for auditability."""
        log_entry = {
            "timestamp_logged": datetime.utcnow().isoformat() + "Z",
            "raw_packet": packet.dict(),
            "observed_events": [e.dict() for e in (observed_events or [])],
            "fused_state": fused_assessment.fused_state if fused_assessment else None,
            "prediction": {
                "risk_probability": prediction.risk_probability,
                "risk_level": prediction.risk_level.value,
                "threshold": prediction.threshold
            } if prediction is not None else None
        }
        log_file = os.path.join(self.log_dir, f"{packet.shipment_id}_telemetry_log.jsonl")
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to append to log file: {e}")

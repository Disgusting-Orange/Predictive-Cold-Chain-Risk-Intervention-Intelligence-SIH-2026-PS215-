"""
FrostLink Feature Engineering Package -- Phase 14
=================================================
Converts raw multi-probe hardware/simulator telemetry into the exact 40-feature schema.
"""

from .raw_schema import RawTelemetryPacket, RawTelemetryHistory
from .feature_engineer import FrostLinkFeatureEngineer
from .validation import validate_raw_packet, validate_feature_vector

__all__ = [
    "RawTelemetryPacket",
    "RawTelemetryHistory",
    "FrostLinkFeatureEngineer",
    "validate_raw_packet",
    "validate_feature_vector"
]

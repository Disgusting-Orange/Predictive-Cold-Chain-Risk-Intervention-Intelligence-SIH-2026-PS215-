"""
FrostLink Hardware Gateway Package -- Phase 15
==============================================
Provides hardware integration, ESP32 raw telemetry ingestion, shipment history buffering,
and end-to-end dispatch to the ML feature engineering and XGBoost inference service.
"""

from .history_buffer import ShipmentHistoryBuffer
from .gateway import HardwareGateway, IngestionResult

__all__ = [
    "ShipmentHistoryBuffer",
    "HardwareGateway",
    "IngestionResult"
]

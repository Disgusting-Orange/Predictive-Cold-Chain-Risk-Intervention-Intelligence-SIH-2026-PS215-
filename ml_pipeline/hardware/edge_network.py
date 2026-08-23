"""
FrostLink Edge Network Health & Mode Manager -- Phase 21
=========================================================
Tracks discrete network modes, connectivity flags, and local edge health:
- Modes: ONLINE, LOCAL_ONLY, EDGE_UNAVAILABLE, DEGRADED
- Independent flags: internet_connected, edge_gateway_reachable, sensor_connected, ml_available
- Simulation hooks for network failure testing.
"""

from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class NetworkModeEnum(str, Enum):
    ONLINE = "ONLINE"                     # LAN OK, Internet OK, Local ML OK, Cloud sync active
    LOCAL_ONLY = "LOCAL_ONLY"             # LAN OK, Internet OFF, Local ML OK, Cloud sync buffered
    EDGE_UNAVAILABLE = "EDGE_UNAVAILABLE" # ESP32 cannot reach Edge Gateway
    DEGRADED = "DEGRADED"                 # Sensor dropout / missing probes / stale telemetry

class EdgeHealthStatus(BaseModel):
    network_mode: NetworkModeEnum
    internet_connected: bool
    edge_gateway_reachable: bool
    sensor_connected: bool
    ml_available: bool
    cloud_sync_pending_count: int
    active_shipments_count: int
    last_evaluation_timestamp: Optional[str] = None
    uptime_seconds: float = 0.0
    status_updated_at: str

class EdgeNetworkManager:
    _instance: Optional["EdgeNetworkManager"] = None

    def __init__(self):
        self.boot_time = datetime.utcnow()
        self.internet_connected: bool = True
        self.edge_gateway_reachable: bool = True
        self.sensor_connected: bool = True
        self.ml_available: bool = True
        self.last_evaluation_timestamp: Optional[str] = None
        self.active_shipment_ids: set = set()

    @classmethod
    def get_instance(cls) -> "EdgeNetworkManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_internet_connected(self, connected: bool):
        self.internet_connected = connected

    def set_edge_gateway_reachable(self, reachable: bool):
        self.edge_gateway_reachable = reachable

    def set_sensor_connected(self, connected: bool):
        self.sensor_connected = connected

    def set_ml_available(self, available: bool):
        self.ml_available = available

    def record_activity(self, shipment_id: str, timestamp: str, sensor_healthy: bool = True):
        self.active_shipment_ids.add(shipment_id)
        self.last_evaluation_timestamp = timestamp
        self.edge_gateway_reachable = True
        self.sensor_connected = sensor_healthy

    def get_current_mode(self, sensor_healthy: bool = True) -> NetworkModeEnum:
        """Evaluates network mode from individual state flags."""
        if not self.edge_gateway_reachable:
            return NetworkModeEnum.EDGE_UNAVAILABLE
        if not sensor_healthy or not self.sensor_connected:
            return NetworkModeEnum.DEGRADED
        if not self.internet_connected:
            return NetworkModeEnum.LOCAL_ONLY
        return NetworkModeEnum.ONLINE

    def get_status(self, local_storage=None) -> EdgeHealthStatus:
        pending_count = local_storage.get_pending_sync_count() if local_storage else 0
        current_mode = self.get_current_mode(sensor_healthy=self.sensor_connected)
        uptime = (datetime.utcnow() - self.boot_time).total_seconds()
        
        return EdgeHealthStatus(
            network_mode=current_mode,
            internet_connected=self.internet_connected,
            edge_gateway_reachable=self.edge_gateway_reachable,
            sensor_connected=self.sensor_connected,
            ml_available=self.ml_available,
            cloud_sync_pending_count=pending_count,
            active_shipments_count=len(self.active_shipment_ids),
            last_evaluation_timestamp=self.last_evaluation_timestamp,
            uptime_seconds=uptime,
            status_updated_at=datetime.utcnow().isoformat() + "Z"
        )

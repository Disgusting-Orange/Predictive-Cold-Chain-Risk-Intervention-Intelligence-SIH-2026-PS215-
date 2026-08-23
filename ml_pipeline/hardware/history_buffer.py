"""
FrostLink Shipment History Buffer -- Phase 15
=============================================
Thread-safe, bounded, timestamp-ordered historical telemetry buffer per shipment.
Preserves causal history for multi-step feature engineering (W60 windows).
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
import threading
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "feature_engineering")))
from raw_schema import RawTelemetryPacket

class ShipmentHistoryBuffer:
    def __init__(self, max_history_packets: int = 100):
        self.max_history_packets = max_history_packets
        self._buffers: Dict[str, List[RawTelemetryPacket]] = {}
        self._lock = threading.Lock()

    def add_packet(self, packet: RawTelemetryPacket) -> int:
        """
        Inserts a packet into the shipment's history buffer in timestamp order.
        Handles duplicate timestamps by updating the existing entry.
        Returns the updated buffer length.
        """
        with self._lock:
            shipment_id = packet.shipment_id
            if shipment_id not in self._buffers:
                self._buffers[shipment_id] = []
            
            buf = self._buffers[shipment_id]
            pkt_time = datetime.fromisoformat(packet.timestamp.replace("Z", "+00:00"))
            
            # Check for existing duplicate timestamp
            duplicate_idx = -1
            for idx, existing in enumerate(buf):
                ex_time = datetime.fromisoformat(existing.timestamp.replace("Z", "+00:00"))
                if ex_time == pkt_time:
                    duplicate_idx = idx
                    break
            
            if duplicate_idx != -1:
                # Update with latest received packet
                buf[duplicate_idx] = packet
            else:
                buf.append(packet)
            
            # Sort strictly by timestamp ascending
            buf.sort(key=lambda p: datetime.fromisoformat(p.timestamp.replace("Z", "+00:00")))
            
            # Enforce max buffer bound
            if len(buf) > self.max_history_packets:
                self._buffers[shipment_id] = buf[-self.max_history_packets:]
                
            return len(self._buffers[shipment_id])

    def get_history(
        self,
        shipment_id: str,
        up_to_timestamp: Optional[Union[str, datetime]] = None
    ) -> List[RawTelemetryPacket]:
        """
        Returns chronological packets for a shipment up to target timestamp (causal slice).
        """
        with self._lock:
            if shipment_id not in self._buffers:
                return []
            
            buf = list(self._buffers[shipment_id])
            if up_to_timestamp is None:
                return buf
            
            t_eval = up_to_timestamp
            if isinstance(t_eval, str):
                t_eval = datetime.fromisoformat(t_eval.replace("Z", "+00:00"))
            elif t_eval.tzinfo is None:
                # Local or naive -> treat as UTC
                t_eval = t_eval.replace(tzinfo=datetime.now().astimezone().tzinfo)
                
            return [
                p for p in buf
                if datetime.fromisoformat(p.timestamp.replace("Z", "+00:00")) <= t_eval
            ]

    def clear(self, shipment_id: Optional[str] = None):
        """Clears memory for a specific shipment or all shipments."""
        with self._lock:
            if shipment_id is not None:
                self._buffers.pop(shipment_id, None)
            else:
                self._buffers.clear()

    def get_shipment_count(self) -> int:
        with self._lock:
            return len(self._buffers)

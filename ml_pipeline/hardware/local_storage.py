"""
FrostLink Edge Gateway Local Persistent Storage -- Phase 21
============================================================
Thread-safe, atomic SQLite database engine for local edge storage and offline queueing.
Ensures zero data loss when Internet is disconnected and enforces duplicate-protected
chronological storage.
"""

import os
import json
import sqlite3
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger("frostlink_local_storage")

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "logs", "frostlink_edge_store.db")

class LocalStorage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        """Initializes tables and indexes."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Raw Telemetry Records (Idempotent per shipment_id + timestamp)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS telemetry_records (
                        shipment_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        raw_json TEXT NOT NULL,
                        active_probes INTEGER NOT NULL,
                        sconf REAL,
                        coverage_time REAL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (shipment_id, timestamp)
                    );
                """)
                
                # 2. Fused ML Risk Evaluations
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS fused_evaluations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shipment_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        cold_start_status TEXT NOT NULL,
                        fused_state TEXT NOT NULL,
                        risk_probability REAL,
                        risk_level TEXT,
                        threshold REAL,
                        observed_events_json TEXT,
                        explanation_json TEXT,
                        latencies_json TEXT,
                        control_state TEXT,
                        protective_action_json TEXT,
                        created_at TEXT NOT NULL,
                        UNIQUE(shipment_id, timestamp)
                    );
                """)
                
                # 3. Cloud Synchronization Queue
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cloud_sync_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shipment_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        record_type TEXT NOT NULL DEFAULT 'EVALUATION',
                        payload_json TEXT NOT NULL,
                        sync_status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, SYNCING, SYNCED, FAILED
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        last_attempt_at TEXT,
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        UNIQUE(shipment_id, timestamp, record_type)
                    );
                """)
                
                # Indexes for fast chronological lookups
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry_records(shipment_id, timestamp);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_time ON fused_evaluations(shipment_id, timestamp);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON cloud_sync_queue(sync_status, timestamp);")
                conn.commit()

    def insert_telemetry_packet(self, packet_dict: Dict[str, Any]) -> bool:
        """
        Stores an incoming raw packet.
        Returns True if inserted as a new record, False if it was an existing duplicate.
        """
        shipment_id = packet_dict.get("shipment_id", "UNKNOWN")
        timestamp = packet_dict.get("timestamp", datetime.utcnow().isoformat() + "Z")
        probes = packet_dict.get("probes", {})
        active_count = sum(1 for v in probes.values() if v is not None and -50.0 <= float(v) <= 80.0) if isinstance(probes, dict) else 0
        sconf = float(packet_dict.get("sconf", 1.0))
        cov_time = float(packet_dict.get("coverage_time", 1.0))
        now_str = datetime.utcnow().isoformat() + "Z"

        with self._lock:
            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT INTO telemetry_records (shipment_id, timestamp, raw_json, active_probes, sconf, coverage_time, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (shipment_id, timestamp, json.dumps(packet_dict), active_count, sconf, cov_time, now_str))
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    # Duplicate packet received -> safe idempotent ignore/update
                    return False

    def insert_evaluation(
        self,
        shipment_id: str,
        timestamp: str,
        cold_start_status: str,
        fused_state: str,
        risk_probability: Optional[float],
        risk_level: Optional[str],
        threshold: Optional[float],
        observed_events: List[Dict[str, Any]],
        explanation: Optional[Dict[str, Any]],
        latencies_ms: Dict[str, float],
        control_state: Optional[str] = None,
        protective_action: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Stores a complete fused ML evaluation and enqueues it for cloud synchronization."""
        now_str = datetime.utcnow().isoformat() + "Z"
        eval_payload = {
            "shipment_id": shipment_id,
            "timestamp": timestamp,
            "cold_start_status": cold_start_status,
            "fused_state": fused_state,
            "risk_probability": risk_probability,
            "risk_level": risk_level,
            "threshold": threshold,
            "observed_events": observed_events,
            "explanation": explanation,
            "latencies_ms": latencies_ms,
            "control_state": control_state,
            "protective_action": protective_action,
            "logged_at": now_str
        }

        with self._lock:
            with self._get_connection() as conn:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO fused_evaluations 
                        (shipment_id, timestamp, cold_start_status, fused_state, risk_probability, 
                         risk_level, threshold, observed_events_json, explanation_json, latencies_json, 
                         control_state, protective_action_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        shipment_id,
                        timestamp,
                        cold_start_status,
                        fused_state,
                        risk_probability,
                        risk_level,
                        threshold,
                        json.dumps(observed_events),
                        json.dumps(explanation) if explanation else None,
                        json.dumps(latencies_ms),
                        control_state,
                        json.dumps(protective_action) if protective_action else None,
                        now_str
                    ))

                    # Enqueue to Cloud Sync Queue
                    conn.execute("""
                        INSERT OR IGNORE INTO cloud_sync_queue
                        (shipment_id, timestamp, record_type, payload_json, sync_status, retry_count, created_at)
                        VALUES (?, ?, 'EVALUATION', ?, 'PENDING', 0, ?)
                    """, (shipment_id, timestamp, json.dumps(eval_payload), now_str))
                    
                    conn.commit()
                    return True
                except Exception as e:
                    logger.error(f"Error persisting evaluation: {e}")
                    return False

    def get_pending_sync_records(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves pending synchronization records in strict chronological order."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, shipment_id, timestamp, record_type, payload_json, retry_count
                    FROM cloud_sync_queue
                    WHERE sync_status IN ('PENDING', 'FAILED')
                    ORDER BY timestamp ASC, id ASC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "id": r["id"],
                        "shipment_id": r["shipment_id"],
                        "timestamp": r["timestamp"],
                        "record_type": r["record_type"],
                        "payload": json.loads(r["payload_json"]),
                        "retry_count": r["retry_count"]
                    })
                return results

    def mark_sync_success(self, record_ids: List[int]):
        """Marks sync records as successfully transmitted."""
        if not record_ids:
            return
        now_str = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            with self._get_connection() as conn:
                placeholders = ",".join("?" for _ in record_ids)
                conn.execute(f"""
                    UPDATE cloud_sync_queue
                    SET sync_status = 'SYNCED', last_attempt_at = ?
                    WHERE id IN ({placeholders})
                """, [now_str] + record_ids)
                conn.commit()

    def mark_sync_failure(self, record_id: int, error_message: str):
        """Marks a record as failed to sync, incrementing retry count."""
        now_str = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE cloud_sync_queue
                    SET sync_status = 'FAILED', retry_count = retry_count + 1,
                        last_attempt_at = ?, error_message = ?
                    WHERE id = ?
                """, (now_str, error_message, record_id))
                conn.commit()

    def get_pending_sync_count(self) -> int:
        """Returns the number of records waiting for cloud sync."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) AS cnt FROM cloud_sync_queue WHERE sync_status IN ('PENDING', 'FAILED');")
                row = cursor.fetchone()
                return int(row["cnt"]) if row else 0

    def get_synced_count(self) -> int:
        """Returns the number of successfully synced records."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) AS cnt FROM cloud_sync_queue WHERE sync_status = 'SYNCED';")
                row = cursor.fetchone()
                return int(row["cnt"]) if row else 0

    def get_latest_evaluation(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Returns the most recent evaluation for a shipment."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM fused_evaluations
                    WHERE shipment_id = ?
                    ORDER BY timestamp DESC, id DESC
                    LIMIT 1
                """, (shipment_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "shipment_id": row["shipment_id"],
                    "timestamp": row["timestamp"],
                    "cold_start_status": row["cold_start_status"],
                    "fused_state": row["fused_state"],
                    "risk_probability": row["risk_probability"],
                    "risk_level": row["risk_level"],
                    "threshold": row["threshold"],
                    "observed_events": json.loads(row["observed_events_json"]) if row["observed_events_json"] else [],
                    "explanation": json.loads(row["explanation_json"]) if row["explanation_json"] else None,
                    "latencies_ms": json.loads(row["latencies_json"]) if row["latencies_json"] else {},
                    "control_state": row["control_state"],
                    "protective_action": json.loads(row["protective_action_json"]) if row["protective_action_json"] else None,
                    "created_at": row["created_at"]
                }

    def clear(self):
        """Clears all tables (used primarily in test suites)."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM telemetry_records;")
                conn.execute("DELETE FROM fused_evaluations;")
                conn.execute("DELETE FROM cloud_sync_queue;")
                conn.commit()

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog


async def log_audit_event(
    db: AsyncSession,
    shipment_id: str,
    stage: str,
    title: str,
    details: Optional[str] = None,
    user_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """Record a compliance audit timeline event."""
    log_entry = AuditLog(
        shipment_id=shipment_id,
        user_id=user_id,
        stage=stage,
        title=title,
        details=details,
        extra_metadata=metadata or {},
        created_at=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry

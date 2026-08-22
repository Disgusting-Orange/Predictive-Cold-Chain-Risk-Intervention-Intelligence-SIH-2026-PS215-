from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.db.models import AuditLog

router = APIRouter(prefix="/audit", tags=["Compliance & Audit"])


@router.get("/{shipment_id}")
async def get_shipment_audit_trail(
    shipment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve chronological audit trail of events (Pickup ➔ Excursions ➔ Approvals ➔ Handoff).
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.shipment_id == shipment_id)
        .order_by(AuditLog.created_at.asc())
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return {
        "shipmentId": shipment_id,
        "totalEvents": len(logs),
        "auditTrail": [
            {
                "id": str(log.id),
                "timestamp": log.created_at.strftime("%I:%M %p") if log.created_at else "",
                "fullTimestamp": log.created_at.isoformat() if log.created_at else "",
                "stage": log.stage,
                "title": log.title,
                "details": log.details,
                "metadata": log.extra_metadata
            }
            for log in logs
        ]
    }

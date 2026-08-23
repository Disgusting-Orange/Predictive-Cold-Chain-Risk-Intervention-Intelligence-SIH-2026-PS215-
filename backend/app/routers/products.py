from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Product

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
async def list_product_profiles(db: AsyncSession = Depends(get_db)):
    """Retrieve all configurable product profiles and safe temperature limits."""
    stmt = select(Product)
    result = await db.execute(stmt)
    products = result.scalars().all()
    
    return {
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "category": p.category,
                "safeTempMin": float(p.safe_temp_min),
                "safeTempMax": float(p.safe_temp_max),
                "criticalTempMax": float(p.critical_temp_max),
                "safeHumidityMin": float(p.safe_humidity_min or 30.0),
                "safeHumidityMax": float(p.safe_humidity_max or 70.0),
                "temperatureSensitivity": p.temperature_sensitivity,
                "shelfLifeHours": float(p.shelf_life_hours)
            }
            for p in products
        ]
    }

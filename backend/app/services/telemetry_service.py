from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import Telemetry, Shipment, RiskPrediction, Alert, Product
from app.schemas.telemetry import TelemetryCreate
from app.services.risk_service import calculate_risk_and_shap
from app.schemas.risk import RiskPredictionResponse


async def process_telemetry_ingestion(
    telemetry_in: TelemetryCreate,
    db: AsyncSession
) -> dict:
    """
    Ingest, validate, persist telemetry from ESP32 / Simulator,
    calculate AI risk & SHAP factors, and record alerts.
    """
    # 1. Sanity Range Validation
    sensor_health = "HEALTHY"
    if telemetry_in.temperature < -50.0 or telemetry_in.temperature > 80.0:
        sensor_health = "DEGRADED_TEMP_OUT_OF_BOUNDS"
    if telemetry_in.humidity < 0.0 or telemetry_in.humidity > 100.0:
        sensor_health = "DEGRADED_HUMIDITY_OUT_OF_BOUNDS"

    # 2. Persist Raw Telemetry
    telemetry_record = Telemetry(
        shipment_id=telemetry_in.shipmentId,
        device_id=telemetry_in.deviceId or "BOX-01",
        timestamp=telemetry_in.timestamp or datetime.now(timezone.utc),
        temperature=telemetry_in.temperature,
        humidity=telemetry_in.humidity,
        latitude=telemetry_in.latitude,
        longitude=telemetry_in.longitude,
        speed=telemetry_in.speed or 0.0,
        door_open=telemetry_in.doorOpen,
        cooling_power=telemetry_in.coolingPower or 70,
        gas_value=telemetry_in.gasValue,
        battery_level=telemetry_in.battery or 90.0
    )
    db.add(telemetry_record)

    # 3. Retrieve Shipment & Product Profile Defaults
    stmt = select(Shipment).where(Shipment.shipment_code == telemetry_in.shipmentId)
    res = await db.execute(stmt)
    shipment = res.scalars().first()

    safe_min = 2.0
    safe_max = 8.0
    cargo_val = 240000.0
    current_eta = 45
    delay_mins = 0

    if shipment:
        if telemetry_in.latitude and telemetry_in.longitude:
            shipment.current_lat = telemetry_in.latitude
            shipment.current_lng = telemetry_in.longitude
        if shipment.product:
            safe_min = float(shipment.product.safe_temp_min)
            safe_max = float(shipment.product.safe_temp_max)
        cargo_val = float(shipment.estimated_cargo_value)
        current_eta = shipment.current_eta_minutes
        delay_mins = shipment.delay_minutes
    else:
        # Auto-create shipment for newly ingested hardware/simulator streams
        prod_stmt = select(Product).limit(1)
        p_res = await db.execute(prod_stmt)
        default_prod = p_res.scalars().first()
        shipment = Shipment(
            shipment_code=telemetry_in.shipmentId,
            product_id=default_prod.id if default_prod else None,
            device_id=telemetry_in.deviceId or "BOX-01",
            vehicle_number="TN-07-EXP-1001",
            origin_name="MediCold Distribution Centre",
            origin_lat=telemetry_in.latitude or 13.0827,
            origin_lng=telemetry_in.longitude or 80.2707,
            destination_name="Apollo Hospital Pharmacy",
            destination_lat=13.0604,
            destination_lng=80.2496,
            current_lat=telemetry_in.latitude or 13.0827,
            current_lng=telemetry_in.longitude or 80.2707,
            status="IN_TRANSIT",
            planned_eta_minutes=45,
            current_eta_minutes=45,
            estimated_cargo_value=240000.0
        )
        db.add(shipment)
        if default_prod:
            safe_min = float(default_prod.safe_temp_min)
            safe_max = float(default_prod.safe_temp_max)

    # 4. Calculate Rate of Climb Trend from Recent History
    hist_stmt = (
        select(Telemetry)
        .where(Telemetry.shipment_id == telemetry_in.shipmentId)
        .order_by(desc(Telemetry.timestamp))
        .limit(4)
    )
    hist_res = await db.execute(hist_stmt)
    recent_readings = hist_res.scalars().all()

    temp_trend = 0.0
    if len(recent_readings) >= 2:
        t_first = float(recent_readings[0].temperature)
        t_last = float(recent_readings[-1].temperature)
        temp_trend = round((t_first - t_last) / max(1, len(recent_readings) - 1), 2)

    # 5. Execute AI Risk & SHAP Engine
    (
        risk_score,
        risk_level,
        spoilage_risk_pct,
        remaining_safe_life,
        excursion_prob,
        ai_conf,
        shap_factors,
        predicted_points,
        msg
    ) = calculate_risk_and_shap(
        temperature=telemetry_in.temperature,
        safe_min=safe_min,
        safe_max=safe_max,
        temp_trend=temp_trend,
        eta_minutes=current_eta,
        delay_minutes=delay_mins,
        door_open=telemetry_in.doorOpen,
        speed=telemetry_in.speed or 0.0
    )

    # 6. Save Risk Prediction Record
    risk_record = RiskPrediction(
        shipment_id=telemetry_in.shipmentId,
        timestamp=datetime.now(timezone.utc),
        risk_score=risk_score,
        risk_level=risk_level,
        spoilage_risk_percent=spoilage_risk_pct,
        remaining_safe_life_minutes=remaining_safe_life,
        excursion_probability=excursion_prob,
        ai_confidence_percent=ai_conf,
        temp_trend_per_tick=temp_trend,
        shap_factors=[f.model_dump() for f in shap_factors],
        model_version="xgb_v1.0"
    )
    db.add(risk_record)

    # 7. Update Shipment Status
    if shipment:
        if risk_level == "CRITICAL":
            shipment.status = "AT_RISK"
        elif risk_level == "HIGH":
            shipment.status = "WARNING"
        elif risk_level == "LOW" and shipment.status != "DIVERTED":
            shipment.status = "IN_TRANSIT"

    # 8. Check for Critical Alerts
    if risk_level in ("HIGH", "CRITICAL"):
        alert_msg = f"Critical risk ({risk_score}/100) on {telemetry_in.shipmentId}: {msg}"
        alert_record = Alert(
            shipment_id=telemetry_in.shipmentId,
            severity=risk_level,
            alert_type="TEMP_EXCURSION",
            message=alert_msg
        )
        db.add(alert_record)

    await db.commit()

    return {
        "status": "success",
        "sensorHealth": sensor_health,
        "shipmentId": telemetry_in.shipmentId,
        "temperature": telemetry_in.temperature,
        "humidity": telemetry_in.humidity,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "spoilageRiskPercent": spoilage_risk_pct,
        "remainingSafeLifeMinutes": remaining_safe_life,
        "excursionProbability": excursion_prob,
        "aiConfidencePercent": ai_conf,
        "shapFactors": [f.model_dump() for f in shap_factors],
        "predictedTemperatures": [p.model_dump() for p in predicted_points],
        "message": msg
    }

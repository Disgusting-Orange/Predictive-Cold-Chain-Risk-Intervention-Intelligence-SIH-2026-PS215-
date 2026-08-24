import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.models import Telemetry, Shipment, RiskPrediction, Alert, Product
from app.schemas.telemetry import TelemetryCreate
from app.services.risk_service import calculate_risk_and_shap
from app.schemas.risk import RiskPredictionResponse
from app.core.config import settings


async def process_telemetry_ingestion(
    telemetry_in: TelemetryCreate,
    db: AsyncSession
) -> dict:
    """
    Ingest, validate, persist telemetry from ESP32 / Simulator,
    calculate AI risk & SHAP factors, and record alerts asynchronously.
    """
    # Derive aggregate temperature if probes given
    current_temp = telemetry_in.temperature
    if current_temp is None and telemetry_in.probes:
        valid_vals = [v for v in telemetry_in.probes.values() if v is not None and -50.0 <= float(v) <= 80.0]
        current_temp = round(sum(valid_vals) / len(valid_vals), 2) if valid_vals else 4.0
    elif current_temp is None:
        current_temp = 4.0

    current_humidity = telemetry_in.humidity if telemetry_in.humidity is not None else 50.0

    # 1. Sanity Range Validation
    sensor_health = "HEALTHY"
    if current_temp < -50.0 or current_temp > 80.0:
        sensor_health = "DEGRADED_TEMP_OUT_OF_BOUNDS"
    if current_humidity < 0.0 or current_humidity > 100.0:
        sensor_health = "DEGRADED_HUMIDITY_OUT_OF_BOUNDS"

    # 2. Persist Raw Telemetry
    telemetry_record = Telemetry(
        shipment_id=telemetry_in.shipmentId,
        device_id=telemetry_in.deviceId or "BOX-01",
        timestamp=telemetry_in.timestamp or datetime.now(timezone.utc),
        temperature=current_temp,
        humidity=current_humidity,
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
        .limit(120)
    )
    hist_res = await db.execute(hist_stmt)
    recent_readings = hist_res.scalars().all()

    temp_trend = 0.0
    if len(recent_readings) >= 2:
        t_first = float(recent_readings[0].temperature)
        t_last = float(recent_readings[-1].temperature)
        temp_trend = round((t_first - t_last) / max(1, len(recent_readings) - 1), 2)

    # 5. Execute AI Risk & SHAP Engine Asynchronously in Thread Pool
    xgb_result = None
    if settings.RISK_ENGINE_MODE.lower() == "xgboost":
        try:
            from app.services.xgb_bridge import FrostLinkXGBoost, build_feature_vector
            features = build_feature_vector(recent_readings, telemetry_in.temperature, safe_min, safe_max)
            xgb_result = FrostLinkXGBoost.instance().predict(features, telemetry_in.temperature, temp_trend, safe_max)
        except Exception:
            xgb_result = None

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
    ) = await asyncio.to_thread(
        calculate_risk_and_shap,
        temperature=current_temp,
        safe_min=safe_min,
        safe_max=safe_max,
        temp_trend=temp_trend,
        eta_minutes=current_eta,
        delay_minutes=delay_mins,
        door_open=telemetry_in.doorOpen,
        speed=telemetry_in.speed or 0.0,
        shipment_id=telemetry_in.shipmentId,
        timestamp=telemetry_in.timestamp,
        battery=telemetry_in.battery or 90.0,
        raw_probes=telemetry_in.probes
    )
    model_version = "heuristic_v1"
    if xgb_result is not None:
        risk_score = xgb_result.risk_score
        risk_level = xgb_result.risk_level
        spoilage_risk_pct = xgb_result.spoilage_risk_pct
        remaining_safe_life = xgb_result.remaining_safe_life
        excursion_prob = xgb_result.excursion_prob
        ai_conf = xgb_result.ai_confidence
        shap_factors = xgb_result.shap_factors
        predicted_points = xgb_result.predicted_points
        msg = xgb_result.message
        model_version = xgb_result.model_version

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
        model_version=model_version
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
        "modelVersion": model_version,
        "shapFactors": [f.model_dump() for f in shap_factors],
        "predictedTemperatures": [p.model_dump() for p in predicted_points],
        "message": msg
    }

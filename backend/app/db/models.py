import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Numeric, Integer, Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="FIELD_AGENT")  # ADMIN, FIELD_AGENT, CLIENT
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # Dairy, Vaccines, Insulin, Biologics, Seafood
    safe_temp_min = Column(Numeric(5, 2), nullable=False)
    safe_temp_max = Column(Numeric(5, 2), nullable=False)
    critical_temp_max = Column(Numeric(5, 2), nullable=False)
    safe_humidity_min = Column(Numeric(5, 2), default=30.0)
    safe_humidity_max = Column(Numeric(5, 2), default=70.0)
    temperature_sensitivity = Column(String(20), default="HIGH")
    shelf_life_hours = Column(Numeric(6, 1), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ColdStorageFacility(Base):
    __tablename__ = "cold_storage_facilities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    facility_type = Column(String(50), default="cold_storage")
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    address = Column(Text, nullable=True)
    capacity_percent = Column(Integer, default=50)
    total_bays = Column(Integer, default=8)
    active_bays = Column(Integer, default=4)
    current_temperature = Column(Numeric(5, 2), default=3.0)
    temp_setpoint = Column(Numeric(5, 2), default=3.0)
    cooling_status = Column(String(50), default="operational")
    power_status = Column(String(50), default="grid")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_code = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    assigned_driver_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    device_id = Column(String(50), default="BOX-01")
    vehicle_number = Column(String(50), nullable=False)
    origin_name = Column(String(150), nullable=False)
    origin_lat = Column(Numeric(10, 7), nullable=False)
    origin_lng = Column(Numeric(10, 7), nullable=False)
    destination_name = Column(String(150), nullable=False)
    destination_lat = Column(Numeric(10, 7), nullable=False)
    destination_lng = Column(Numeric(10, 7), nullable=False)
    current_lat = Column(Numeric(10, 7), nullable=True)
    current_lng = Column(Numeric(10, 7), nullable=True)
    status = Column(String(50), default="IN_TRANSIT")
    planned_eta_minutes = Column(Integer, nullable=False)
    current_eta_minutes = Column(Integer, nullable=False)
    delay_minutes = Column(Integer, default=0)
    estimated_cargo_value = Column(Numeric(12, 2), default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    product = relationship("Product", lazy="joined")
    driver = relationship("User", lazy="joined")


class Telemetry(Base):
    __tablename__ = "telemetry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(String(50), nullable=False, index=True)
    device_id = Column(String(50), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    temperature = Column(Numeric(5, 2), nullable=False)
    humidity = Column(Numeric(5, 2), nullable=False)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    speed = Column(Numeric(6, 2), default=0.0)
    door_open = Column(Boolean, default=False)
    cooling_power = Column(Integer, default=70)
    gas_value = Column(Numeric(8, 2), nullable=True)
    battery_level = Column(Numeric(5, 2), default=90.0)


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    spoilage_risk_percent = Column(Integer, nullable=False)
    remaining_safe_life_minutes = Column(Integer, nullable=True)
    excursion_probability = Column(Numeric(4, 3), nullable=True)
    ai_confidence_percent = Column(Integer, default=87)
    temp_trend_per_tick = Column(Numeric(5, 2), default=0.0)
    shap_factors = Column(JSON, default=list)
    model_version = Column(String(50), default="xgb_v1.0")


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Intervention(Base):
    __tablename__ = "interventions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(String(50), nullable=False, index=True)
    recommended_action = Column(String(100), nullable=False)
    target_facility_id = Column(UUID(as_uuid=True), ForeignKey("cold_storage_facilities.id", ondelete="SET NULL"), nullable=True)
    target_facility_name = Column(String(150), nullable=True)
    risk_before = Column(Integer, nullable=False)
    risk_after = Column(Integer, nullable=False)
    eta_before = Column(Integer, nullable=False)
    eta_after = Column(Integer, nullable=False)
    estimated_loss_without_intervention = Column(Numeric(12, 2), default=0.0)
    estimated_loss_with_intervention = Column(Numeric(12, 2), default=0.0)
    potential_loss_avoided = Column(Numeric(12, 2), default=0.0)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING_APPROVAL")
    override_reason = Column(Text, nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    handoff_photo_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    stage = Column(String(50), nullable=False)
    title = Column(String(150), nullable=False)
    details = Column(Text, nullable=True)
    extra_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

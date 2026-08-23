import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client: TestClient):
    """Test health check endpoints."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_auth_login(client: TestClient):
    """Test authentication for Admin and Field Agent roles."""
    # 1. Admin Login
    admin_res = client.post("/api/auth/login", json={
        "email": "admin@coldchain.ai",
        "password": "admin123"
    })
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert admin_data["role"] == "ADMIN"
    assert "access_token" in admin_data

    # 2. Driver / Field Agent Login
    driver_res = client.post("/api/auth/login", json={
        "email": "driver@coldchain.ai",
        "password": "driver123"
    })
    assert driver_res.status_code == 200
    driver_data = driver_res.json()
    assert driver_data["role"] == "FIELD_AGENT"


def test_telemetry_ingestion(client: TestClient):
    """Test canonical telemetry ingestion from ESP32/simulator."""
    telemetry_payload = {
        "shipmentId": "SHP-1042",
        "deviceId": "BOX-01",
        "temperature": 6.8,
        "humidity": 48.0,
        "latitude": 13.0740,
        "longitude": 80.2640,
        "speed": 35.0,
        "doorOpen": False,
        "coolingPower": 75,
        "battery": 88.0
    }
    response = client.post("/telemetry", json=telemetry_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["shipmentId"] == "SHP-1042"
    assert "riskScore" in data
    assert "shapFactors" in data
    assert len(data["shapFactors"]) > 0


def test_shipments_list(client: TestClient):
    """Test listing all active shipments."""
    response = client.get("/api/shipments")
    assert response.status_code == 200
    data = response.json()
    assert "shipments" in data
    assert len(data["shipments"]) > 0


def test_products_list(client: TestClient):
    """Test listing product profiles."""
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    assert len(data["products"]) > 0


def test_what_if_simulation(client: TestClient):
    """Test What-If intervention simulation generating 3 scenarios."""
    response = client.post("/api/interventions/SHP-1042/simulate")
    assert response.status_code == 200
    data = response.json()
    assert data["shipmentId"] == "SHP-1042"
    assert len(data["scenarios"]) == 3
    assert data["potentialLossAvoided"] >= 0
    assert any(s["isRecommended"] for s in data["scenarios"])


def test_intervention_approval_lifecycle(client: TestClient):
    """Test full intervention lifecycle: approve -> field-accept -> handoff."""
    # 1. Approve
    app_res = client.post("/api/interventions/SHP-1042/approve")
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "success"

    # 2. Field Accept
    fa_res = client.post("/api/interventions/SHP-1042/field-accept")
    assert fa_res.status_code == 200

    # 3. Handoff
    ho_res = client.post("/api/interventions/SHP-1042/handoff", json={
        "notes": "Delivered in optimal condition to Bay 4"
    })
    assert ho_res.status_code == 200


def test_public_client_tracking(client: TestClient):
    """Test public read-only tracking view for clients."""
    response = client.get("/api/public/track/SHP-1042")
    assert response.status_code == 200
    data = response.json()
    assert data["shipmentId"] == "SHP-1042"
    assert "trustBadge" in data
    assert "timeline" in data
    assert len(data["timeline"]) == 5


def test_audit_trail(client: TestClient):
    """Test audit log history retrieval."""
    response = client.get("/api/audit/SHP-1042")
    assert response.status_code == 200
    data = response.json()
    assert data["shipmentId"] == "SHP-1042"
    assert "auditTrail" in data

"""
FrostLink Telemetry Sender -- Hardware / Sensor Simulator
=========================================================
Sends telemetry observations (temperature, humidity, door state, 
9-probe reefer mesh, battery level) from your laptop to the local backend.

The backend processes telemetry through the server-side ML model (XGBoost V2 + TreeSHAP)
and broadcasts live predictions over WebSockets to the frontend dashboard.
"""

import time
import requests
import json

BACKEND_URL = "http://localhost:8000/api/telemetry"

def send_telemetry_reading(shipment_id="SHP-1042", temp=4.5, door_open=False, humidity=48.0, speed=40.0):
    payload = {
        "shipmentId": shipment_id,
        "deviceId": "ESP32-HARDWARE-LAPTOP-01",
        "temperature": temp,
        "humidity": humidity,
        "speed": speed,
        "doorOpen": door_open,
        "coolingPower": 75 if temp <= 8.0 else 30,
        "battery": 92.0,
        "probes": {
            "Front_Top": round(temp + 0.25, 2),
            "Front_Middle": round(temp, 2),
            "Front_Bottom": round(temp - 0.20, 2),
            "Middle_Top": round(temp + 0.35, 2),
            "Middle_Middle": round(temp + 0.05, 2),
            "Middle_Bottom": round(temp - 0.15, 2),
            "Rear_Top": round(temp + 0.55, 2),
            "Rear_Middle": round(temp + 0.20, 2),
            "Rear_Bottom": round(temp + 0.05, 2)
        }
    }
    
    print(f"\n[➜] Sending hardware data for {shipment_id}: Temp={temp}°C, DoorOpen={door_open}...")
    try:
        response = requests.post(BACKEND_URL, json=payload, timeout=5)
        if response.status_code in (200, 201):
            data = response.json()
            print(f"[✓] Backend & ML Response:")
            print(f"    - Risk Score: {data.get('riskScore')}/100 ({data.get('riskLevel')})")
            print(f"    - Excursion Probability: {data.get('excursionProbability')}")
            print(f"    - Spoilage Risk Percent: {data.get('spoilageRiskPercent')}%")
            print(f"    - AI Confidence: {data.get('aiConfidencePercent')}%")
            print(f"    - SHAP Factors: {json.dumps(data.get('shapFactors'), indent=6)}")
        else:
            print(f"[✗] Error from backend ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[✗] Could not connect to backend at {BACKEND_URL}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("FROSTLINK HARDWARE TELEMETRY STREAMER")
    print("=" * 60)
    
    # 1. Normal operating telemetry
    send_telemetry_reading("SHP-1042", temp=4.5, door_open=False)
    time.sleep(2)
    
    # 2. Temperature rising
    send_telemetry_reading("SHP-1042", temp=7.8, door_open=False)
    time.sleep(2)
    
    # 3. Temperature excursion + door open event
    send_telemetry_reading("SHP-1042", temp=11.2, door_open=True)

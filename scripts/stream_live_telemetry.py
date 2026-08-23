#!/usr/bin/env python3
"""
Cold Chain AI — Live Telemetry Continuous Streamer
===================================================
Simulates continuous IoT hardware (ESP32) sensor streams pushing real-time
telemetry to the FastAPI backend and Supabase PostgreSQL.

Usage:
  python scripts/stream_live_telemetry.py [--url https://cold-chain-ai-ps215.vercel.app] [--interval 4]
"""

import argparse
import random
import time
import httpx
import sys

WAYPOINTS = [
    {"lat": 13.0827, "lng": 80.2707, "name": "MediCold DC Central"},
    {"lat": 13.0780, "lng": 80.2680, "name": "Poonamallee High Rd"},
    {"lat": 13.0710, "lng": 80.2610, "name": "EVR Periyar Salai"},
    {"lat": 13.0640, "lng": 80.2540, "name": "Anna Salai Junction"},
    {"lat": 13.0604, "lng": 80.2496, "name": "Apollo Hospital Pharmacy"},
]

def stream_telemetry(base_url: str, interval: float, shipment_id: str, mode: str):
    url = f"{base_url.rstrip('/')}/api/telemetry"
    print("=" * 65)
    print(f"📡 Cold Chain AI — Live Telemetry Streamer")
    print(f"🎯 Target Endpoint: {url}")
    print(f"🚚 Shipment Code  : {shipment_id}")
    print(f"⏱️ Interval       : {interval}s")
    print(f"⚠️ Simulation Mode: {mode.upper()}")
    print("=" * 65)
    print("Press Ctrl+C to stop streaming.\n")

    tick = 0
    temp = 4.2 if mode == "normal" else 7.8
    humidity = 48.0
    battery = 92.0
    
    with httpx.Client(timeout=15.0) as client:
        while True:
            tick += 1
            waypoint = WAYPOINTS[tick % len(WAYPOINTS)]
            
            if mode == "normal":
                temp += random.uniform(-0.15, 0.15)
                temp = max(2.5, min(4.8, temp))
                door_open = False
                speed = random.uniform(30.0, 48.0)
                cooling_power = 72
            else:
                temp += random.uniform(0.3, 0.8)
                door_open = tick > 3
                speed = max(0.0, random.uniform(5.0, 20.0))
                cooling_power = max(20, 70 - tick * 5)
                
            humidity = max(40.0, min(80.0, humidity + random.uniform(-1.0, 1.0)))
            battery = max(10.0, battery - 0.05)

            payload = {
                "shipmentId": shipment_id,
                "deviceId": "ESP32-NODE-01",
                "temperature": round(temp, 2),
                "humidity": round(humidity, 1),
                "latitude": round(waypoint["lat"] + random.uniform(-0.0005, 0.0005), 5),
                "longitude": round(waypoint["lng"] + random.uniform(-0.0005, 0.0005), 5),
                "speed": round(speed, 1),
                "doorOpen": door_open,
                "coolingPower": cooling_power,
                "battery": round(battery, 1),
                "gasValue": round(random.uniform(8.0, 18.0), 1)
            }

            try:
                res = client.post(url, json=payload)
                if res.status_code in (200, 201):
                    data = res.json()
                    risk_score = data.get("riskScore", "N/A")
                    risk_level = data.get("riskLevel", "N/A")
                    print(f"[Tick #{tick:03d}] Temp: {payload['temperature']:5.1f}°C | Hum: {payload['humidity']:4.1f}% | Risk: {risk_score:>3}/100 ({risk_level:<8}) | Door: {'OPEN' if door_open else 'CLOSED'} | GPS: {payload['latitude']}, {payload['longitude']}")
                else:
                    print(f"[Tick #{tick:03d}] ⚠️ Server responded with HTTP {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"[Tick #{tick:03d}] ❌ Error sending telemetry: {e}")

            time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Telemetry Continuous Streamer")
    parser.add_argument("--url", default="https://cold-chain-ai-ps215.vercel.app", help="Base URL of backend")
    parser.add_argument("--interval", type=float, default=4.0, help="Seconds between sensor readings")
    parser.add_argument("--shipment", default="SHP-1042", help="Shipment Code (e.g. SHP-1042)")
    parser.add_argument("--mode", choices=["normal", "failure"], default="normal", help="Simulation mode")
    args = parser.parse_args()

    try:
        stream_telemetry(args.url, args.interval, args.shipment, args.mode)
    except KeyboardInterrupt:
        print("\n\n🛑 Telemetry streaming stopped by user.")
        sys.exit(0)

#!/usr/bin/env python3
"""
Cold Chain AI — USB Serial to Cloud Bridge
==========================================
Reads raw JSON / CSV sensor lines from ESP32 over USB Serial (e.g. /dev/ttyUSB0, COM3)
and automatically forwards them via HTTP POST to the live production backend.

Usage:
  python scripts/usb_serial_bridge.py --port /dev/ttyUSB0 --baud 115200 --url https://cold-chain-ai-ps215.vercel.app
"""

import argparse
import json
import re
import sys
import time
import httpx

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial not installed. Install with: pip install pyserial")
    serial = None

def detect_ports():
    if not serial:
        return []
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

def parse_serial_line(line: str, shipment_id: str):
    """
    Parses either a JSON string: {"temp": 4.5, "hum": 55}
    or comma/key-value text: "TEMP: 4.5, HUM: 55, DOOR: 0"
    """
    line = line.strip()
    if not line:
        return None

    # Case 1: Pure JSON
    try:
        data = json.loads(line)
        if isinstance(data, dict):
            if "shipmentId" not in data and "shipment_id" not in data:
                data["shipmentId"] = shipment_id
            return data
    except Exception:
        pass

    # Case 2: Key-value / Regex matching
    payload = {"shipmentId": shipment_id}
    
    temp_match = re.search(r'(?:temp|temperature)[:=]\s*([-\d.]+)', line, re.IGNORECASE)
    if temp_match:
        payload["temperature"] = float(temp_match.group(1))

    hum_match = re.search(r'(?:hum|humidity)[:=]\s*([-\d.]+)', line, re.IGNORECASE)
    if hum_match:
        payload["humidity"] = float(hum_match.group(1))

    door_match = re.search(r'(?:door|door_open)[:=]\s*([01]|true|false|open|closed)', line, re.IGNORECASE)
    if door_match:
        val = door_match.group(1).lower()
        payload["doorOpen"] = val in ("1", "true", "open")

    lat_match = re.search(r'(?:lat|latitude)[:=]\s*([-\d.]+)', line, re.IGNORECASE)
    if lat_match:
        payload["latitude"] = float(lat_match.group(1))

    lng_match = re.search(r'(?:lng|lon|longitude)[:=]\s*([-\d.]+)', line, re.IGNORECASE)
    if lng_match:
        payload["longitude"] = float(lng_match.group(1))

    if "temperature" in payload or "humidity" in payload:
        return payload

    return None

def run_bridge(port: str, baud: int, url: str, shipment_id: str):
    target_url = f"{url.rstrip('/')}/api/telemetry"
    print("=" * 65)
    print("🔌 Cold Chain AI — USB Serial to Cloud Bridge")
    print(f"📡 Serial Port : {port} @ {baud} baud")
    print(f"🎯 Target URL   : {target_url}")
    print(f"🚚 Default SHP  : {shipment_id}")
    print("=" * 65)

    if not serial:
        print("Error: pyserial library is required. Run: pip install pyserial")
        sys.exit(1)

    try:
        ser = serial.Serial(port, baud, timeout=2.0)
        print(f"✅ Connected to serial port {port}. Listening for sensor packets...\n")
    except Exception as e:
        print(f"❌ Failed to open serial port {port}: {e}")
        available = detect_ports()
        print(f"Available serial ports: {available or 'None found'}")
        sys.exit(1)

    with httpx.Client(timeout=15.0) as client:
        while True:
            try:
                raw_line = ser.readline().decode('utf-8', errors='ignore')
                if not raw_line.strip():
                    continue

                print(f"[SERIAL IN]: {raw_line.strip()}")
                payload = parse_serial_line(raw_line, shipment_id)
                if not payload:
                    continue

                # Ensure minimum valid fields
                if "temperature" not in payload:
                    payload["temperature"] = 4.5
                if "humidity" not in payload:
                    payload["humidity"] = 50.0

                # Send to cloud
                res = client.post(target_url, json=payload)
                if res.status_code in (200, 201):
                    res_data = res.json()
                    print(f"  └─► 🚀 FORWARDED TO CLOUD: HTTP {res.status_code} | Risk: {res_data.get('riskScore')}/100 ({res_data.get('riskLevel')})")
                else:
                    print(f"  └─► ⚠️ Cloud returned HTTP {res.status_code}: {res.text[:100]}")

            except KeyboardInterrupt:
                print("\n🛑 Bridge stopped.")
                break
            except Exception as e:
                print(f"⚠️ Bridge loop error: {e}")
                time.sleep(1)

    ser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="USB Serial to Cloud Telemetry Bridge")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port (e.g. /dev/ttyUSB0, COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--url", default="https://cold-chain-ai-ps215.vercel.app", help="Backend URL")
    parser.add_argument("--shipment", default="SHP-1042", help="Shipment code")
    args = parser.parse_args()

    run_bridge(args.port, args.baud, args.url, args.shipment)

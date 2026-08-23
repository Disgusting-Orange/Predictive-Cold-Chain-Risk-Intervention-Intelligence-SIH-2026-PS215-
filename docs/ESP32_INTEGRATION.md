# ESP32 integration guide

## What the device connects to

The ESP32 should send an HTTPS POST request to the FastAPI telemetry endpoint. It should not connect directly to Supabase PostgreSQL. The backend validates the payload, stores the reading, calculates risk, creates alerts when needed, and returns the result.

```text
ESP32 sensors
  -> Wi-Fi or cellular gateway
  -> HTTPS POST /api/telemetry
  -> FastAPI
  -> Supabase PostgreSQL
  -> risk calculation and alert record
```

## Endpoint

| Environment | URL |
|---|---|
| Local | `http://YOUR_COMPUTER_IP:8000/api/telemetry` |
| Vercel | `https://YOUR_PROJECT.vercel.app/api/telemetry` |

Use the Vercel project URL configured for your account. The device must be able to resolve DNS and make outbound HTTPS requests.

## Payload

Send JSON with these fields.

| Field | Type | Required | Example | Meaning |
|---|---|---:|---|---|
| `shipmentId` | string | Yes | `SHP-1042` | Shipment code already known by the backend |
| `deviceId` | string | No | `ESP32-BOX-01` | Device identifier |
| `timestamp` | ISO string | No | `2026-08-23T14:30:00Z` | Sensor reading time |
| `temperature` | number | Yes | `4.2` | Cargo temperature in Celsius |
| `humidity` | number | Yes | `48` | Relative humidity from 0 to 100 |
| `latitude` | number | No | `13.075` | GPS latitude |
| `longitude` | number | No | `80.265` | GPS longitude |
| `speed` | number | No | `38` | Vehicle speed in kilometres per hour |
| `doorOpen` | boolean | No | `false` | Cargo door state |
| `coolingPower` | integer | No | `72` | Reefer cooling power from 0 to 100 |
| `gasValue` | number | No | `0.12` | VOC or spoilage gas sensor reading |
| `battery` | number | No | `91` | Device battery percentage |

Example payload:

```json
{
  "shipmentId": "SHP-1042",
  "deviceId": "ESP32-BOX-01",
  "timestamp": "2026-08-23T14:30:00Z",
  "temperature": 4.2,
  "humidity": 48,
  "latitude": 13.075,
  "longitude": 80.265,
  "speed": 38,
  "doorOpen": false,
  "coolingPower": 72,
  "gasValue": 0.12,
  "battery": 91
}
```

## Test the endpoint before flashing the device

```bash
curl -X POST "https://YOUR_PROJECT.vercel.app/api/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "shipmentId": "SHP-1042",
    "deviceId": "CURL-TEST-01",
    "temperature": 4.2,
    "humidity": 48,
    "latitude": 13.075,
    "longitude": 80.265,
    "speed": 38,
    "doorOpen": false,
    "coolingPower": 72,
    "battery": 91
  }'
```

Expected response fields include:

| Field | Meaning |
|---|---|
| `status` | Ingestion result |
| `shipmentId` | Shipment that was updated |
| `riskScore` | Current risk score from 0 to 100 |
| `riskLevel` | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `shapFactors` | Current explanation factors from the active scorer |
| `predictedTemperatures` | Forward temperature estimate when a trend exists |
| `sensorHealth` | Sensor range validation result |

## ESP32 request flow

1. Connect to Wi-Fi.
2. Read the temperature, humidity, GPS, door, cooling, and battery sensors.
3. Build the JSON object using the field names in this guide.
4. Send an HTTPS POST request.
5. Treat any 2xx response as accepted only after checking the JSON `status` field.
6. If the request fails, store the reading locally and retry with exponential backoff.
7. Do not discard readings when the network is unavailable.

Recommended retry schedule:

| Attempt | Delay |
|---:|---:|
| 1 | 5 seconds |
| 2 | 15 seconds |
| 3 | 60 seconds |
| 4 and later | 5 minutes |

## Security requirement before fleet rollout

The current telemetry route is designed for the prototype hardware contract and does not yet enforce a per-device API key. Do not expose it to untrusted devices without adding device authentication, rate limiting, request signing, and replay protection. A practical next step is an `X-Device-Key` header mapped to a shipment or device record.

## Hardware to backend mapping

| Hardware value | Backend field |
|---|---|
| DS18B20 or probe average | `temperature` |
| DHT22 or SHT31 humidity | `humidity` |
| GPS module latitude | `latitude` |
| GPS module longitude | `longitude` |
| GPS speed | `speed` |
| Reed switch or door sensor | `doorOpen` |
| Reefer controller output | `coolingPower` |
| MQ or VOC sensor | `gasValue` |
| ESP32 ADC or battery monitor | `battery` |


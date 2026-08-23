/*
 * FrostLink ESP32 Cold-Chain Multi-Probe Telemetry Gateway
 * =========================================================
 * Firmware for ESP32 with 1-Wire DS18B20 Multi-Probe Sensor Mesh.
 * Reads spatial temperatures, validates CRC, formats raw telemetry JSON,
 * and transmits to the FrostLink hardware ingestion endpoint over HTTP/Wi-Fi/Cellular.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include <time.h>

// Configuration
#define ONE_WIRE_BUS 4          // GPIO connected to DS18B20 1-Wire Data Line (with 4.7k pullup)
#define SAMPLING_INTERVAL_MS 600000 // 10 minutes (600,000 ms) in production
#define WIFI_SSID "ColdChain_Reefer_AP"
#define WIFI_PASS "FrostLinkSecure2026"
#define BACKEND_INGEST_URL "http://gateway.frostlink.internal:8000/api/v1/telemetry"
#define SHIPMENT_ID "SHIP_ESP32_REEFER_001"

// 1-Wire and Temperature instances
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Known 64-bit ROM Addresses for 9 Spatial Probes
// (Scan via sensors.getAddress() during physical installation)
DeviceAddress probe_Front_Top    = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x01 };
DeviceAddress probe_Front_Middle = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x02 };
DeviceAddress probe_Front_Bottom = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x03 };
DeviceAddress probe_Mid_Top      = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x04 };
DeviceAddress probe_Mid_Middle   = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x05 };
DeviceAddress probe_Mid_Bottom   = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x06 };
DeviceAddress probe_Rear_Top     = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x07 };
DeviceAddress probe_Rear_Middle  = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x08 };
DeviceAddress probe_Rear_Bottom  = { 0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x09 };

struct ProbeConfig {
  const char* name;
  DeviceAddress address;
};

ProbeConfig probeList[] = {
  {"Front_Top",    {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x01}},
  {"Front_Middle", {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x02}},
  {"Front_Bottom", {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x03}},
  {"Middle_Top",   {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x04}},
  {"Middle_Middle",{0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x05}},
  {"Middle_Bottom",{0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x06}},
  {"Rear_Top",     {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x07}},
  {"Rear_Middle",  {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x08}},
  {"Rear_Bottom",  {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x09}}
};

const int NUM_PROBES = sizeof(probeList) / sizeof(probeList[0]);

void setup() {
  Serial.begin(115200);
  Serial.println("[+] FrostLink ESP32 Gateway Booting...");
  
  // Initialize DS18B20 sensors
  sensors.begin();
  sensors.setResolution(12); // 12-bit resolution (0.0625°C precision)
  sensors.setWaitForConversion(true);
  
  int count = sensors.getDeviceCount();
  Serial.printf("[+] Detected %d 1-Wire devices on bus.\n", count);
  
  // Wi-Fi Connection
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  configTime(0, 0, "pool.ntp.org"); // NTP time sync for ISO-8601
}

String getISO8601Timestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "2026-08-23T14:30:00Z"; // Fallback if NTP unready
  }
  char strftime_buf[30];
  strftime(strftime_buf, sizeof(strftime_buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(strftime_buf);
}

void loop() {
  Serial.println("[-] Acquiring sensor readings...");
  sensors.requestTemperatures(); // Block 750ms for 12-bit conversion
  
  StaticJsonDocument<1024> doc;
  doc["shipment_id"] = SHIPMENT_ID;
  doc["timestamp"] = getISO8601Timestamp();
  
  JsonObject probes = doc.createNestedObject("probes");
  int validCount = 0;
  
  for (int i = 0; i < NUM_PROBES; i++) {
    float tempC = sensors.getTempCByIndex(i); // Or by specific ROM address
    
    // Check for 1-Wire error codes (-127.0°C = disconnected, 85.0°C = power-on reset error)
    if (tempC == DEVICE_DISCONNECTED_C || tempC == 85.0 || tempC < -50.0 || tempC > 80.0) {
      probes[probeList[i].name] = nullptr; // Null out faulty probe
    } else {
      probes[probeList[i].name] = tempC;
      validCount++;
    }
  }
  
  // Compute packet confidence score
  doc["sconf"] = (float)validCount / (float)NUM_PROBES;
  doc["coverage_time"] = 1.0;
  
  String payload;
  serializeJson(doc, payload);
  Serial.printf("[+] Prepared Packet: %s\n", payload.c_str());
  
  // Transmit over HTTP POST
  if (WiFi.status() == WL_CONNECTED && validCount > 0) {
    HTTPClient http;
    http.begin(BACKEND_INGEST_URL);
    http.addHeader("Content-Type", "application/json");
    int httpResponseCode = http.POST(payload);
    Serial.printf("[+] Ingestion response code: %d\n", httpResponseCode);
    http.end();
  }
  
  delay(SAMPLING_INTERVAL_MS);
}

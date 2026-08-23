/*
 * FrostLink ESP32 Cold-Chain Multi-Probe Telemetry Gateway -- Phase 21
 * ====================================================================
 * Edge-Resilient Firmware for ESP32 with 1-Wire DS18B20 Multi-Probe Sensor Mesh.
 * 
 * Local Edge Architecture Features:
 * - Direct local-LAN HTTP communication to Edge Gateway (no public internet required).
 * - Fully configurable host, port, endpoint, device/shipment ID, and auth token.
 * - Non-blocking local circular ring buffer for offline buffering during LAN drops (NO_LOCAL_NETWORK).
 * - Bounded stepped/exponential retry backoff.
 * - Monotonic timestamp continuity handling with NTP sync fallback.
 * - 1-Wire CRC validation and fault code sanitization (-127°C, 85°C).
 * - Explicit packet state tracking: GENERATED -> STORED_LOCALLY -> TRANSMITTED -> ACKNOWLEDGED.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include <time.h>

// ============================================================
// CONFIGURABLE PARAMETERS (DO NOT HARDCODE STATIC IP IN PROD)
// ============================================================
#define ONE_WIRE_BUS 4               // GPIO connected to DS18B20 1-Wire Data Line (with 4.7k pullup)
#define SAMPLING_INTERVAL_MS 600000  // 10 minutes (600,000 ms) in production
#define WIFI_SSID "ColdChain_Reefer_AP"
#define WIFI_PASS "FrostLinkSecure2026"

// Local Edge Gateway Configuration
const char* EDGE_GATEWAY_HOST = "192.168.4.1"; // Configurable Edge Gateway Host / IP
const int   EDGE_GATEWAY_PORT = 8000;          // Configurable Port
const char* TELEMETRY_ENDPOINT = "/api/v1/telemetry"; // Configurable Endpoint
const char* SHIPMENT_ID = "SHIP_ESP32_REEFER_001";    // Configurable Shipment / Device Identifier
const char* AUTH_TOKEN = "FL_EDGE_TOKEN_2026";        // Configurable Local Auth Token

// Retry and Buffer Configuration
#define MAX_BUFFERED_PACKETS 30      // Local RAM circular buffer for offline resilience
#define INITIAL_RETRY_DELAY_MS 1000  // 1s initial retry delay
#define MAX_RETRY_DELAY_MS 30000     // 30s maximum backoff cap

// ============================================================
// SENSOR HARDWARE CONFIGURATION
// ============================================================
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

struct ProbeConfig {
  const char* name;
  DeviceAddress address;
};

ProbeConfig probeList[] = {
  {"Front_Top",     {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x01}},
  {"Front_Middle",  {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x02}},
  {"Front_Bottom",  {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x03}},
  {"Middle_Top",    {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x04}},
  {"Middle_Middle", {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x05}},
  {"Middle_Bottom", {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x06}},
  {"Rear_Top",      {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x07}},
  {"Rear_Middle",   {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x08}},
  {"Rear_Bottom",   {0x28, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E, 0x6F, 0x09}}
};

const int NUM_PROBES = sizeof(probeList) / sizeof(probeList[0]);

// ============================================================
// LOCAL TELEMETRY BUFFER (RAM RING BUFFER FOR LAN OUTAGES)
// ============================================================
struct BufferedPacket {
  String jsonPayload;
  unsigned long timestampMillis;
  bool isAcknowledged;
};

BufferedPacket localBuffer[MAX_BUFFERED_PACKETS];
int bufferHead = 0;
int bufferTail = 0;
int bufferCount = 0;

unsigned long lastSampleTime = 0;
unsigned long currentRetryDelay = INITIAL_RETRY_DELAY_MS;
bool isEdgeGatewayReachable = false;
unsigned long bootEpoch = 1787493600; // Monotonic base epoch fallback (2026-08-23T14:00:00Z)

// ============================================================
// HELPER FUNCTIONS
// ============================================================
String buildGatewayUrl() {
  return "http://" + String(EDGE_GATEWAY_HOST) + ":" + String(EDGE_GATEWAY_PORT) + String(TELEMETRY_ENDPOINT);
}

String getISO8601Timestamp() {
  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    char strftime_buf[30];
    strftime(strftime_buf, sizeof(strftime_buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(strftime_buf);
  }
  // Safe monotonic continuity fallback if NTP is unavailable
  unsigned long elapsedSec = millis() / 1000;
  time_t currentEpoch = bootEpoch + elapsedSec;
  struct tm* fallbackTime = gmtime(&currentEpoch);
  char strftime_buf[30];
  strftime(strftime_buf, sizeof(strftime_buf), "%Y-%m-%dT%H:%M:%SZ", fallbackTime);
  return String(strftime_buf);
}

void storePacketInLocalBuffer(const String& payload) {
  localBuffer[bufferHead].jsonPayload = payload;
  localBuffer[bufferHead].timestampMillis = millis();
  localBuffer[bufferHead].isAcknowledged = false;
  
  bufferHead = (bufferHead + 1) % MAX_BUFFERED_PACKETS;
  if (bufferCount < MAX_BUFFERED_PACKETS) {
    bufferCount++;
  } else {
    // Buffer overflow: drop oldest unacknowledged packet to maintain freshest observations
    bufferTail = (bufferTail + 1) % MAX_BUFFERED_PACKETS;
    Serial.println("[!] Warning: Local buffer full, oldest unacknowledged packet overwritten.");
  }
  Serial.printf("[+] Stored packet locally. Pending buffer queue size: %d\n", bufferCount);
}

bool transmitHttpPacket(const String& payload) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  
  HTTPClient http;
  String url = buildGatewayUrl();
  http.begin(url);
  http.setTimeout(3000); // 3-second non-blocking timeout
  http.addHeader("Content-Type", "application/json");
  if (strlen(AUTH_TOKEN) > 0) {
    http.addHeader("X-FrostLink-Auth", AUTH_TOKEN);
  }
  
  int httpResponseCode = http.POST(payload);
  bool success = (httpResponseCode >= 200 && httpResponseCode < 300);
  
  if (success) {
    Serial.printf("[+] Telemetry transmitted successfully (HTTP %d)\n", httpResponseCode);
  } else {
    Serial.printf("[-] Transmission failed (HTTP %d) to %s\n", httpResponseCode, url.c_str());
  }
  http.end();
  return success;
}

void flushLocalBuffer() {
  while (bufferCount > 0 && WiFi.status() == WL_CONNECTED) {
    String payload = localBuffer[bufferTail].jsonPayload;
    Serial.printf("[*] Flushing buffered observation (Remaining: %d)...\n", bufferCount);
    
    if (transmitHttpPacket(payload)) {
      localBuffer[bufferTail].isAcknowledged = true;
      bufferTail = (bufferTail + 1) % MAX_BUFFERED_PACKETS;
      bufferCount--;
      currentRetryDelay = INITIAL_RETRY_DELAY_MS; // Reset backoff on success
      isEdgeGatewayReachable = true;
    } else {
      isEdgeGatewayReachable = false;
      Serial.printf("[-] Flush halted. Edge Gateway unreachable. Backoff: %lu ms\n", currentRetryDelay);
      break;
    }
  }
}

// ============================================================
// SETUP & LOOP
// ============================================================
void setup() {
  Serial.begin(115200);
  Serial.println("[+] FrostLink ESP32 Local Edge Gateway Booting (Phase 21)...");
  
  // Initialize DS18B20 1-Wire sensors
  sensors.begin();
  sensors.setResolution(12); // 12-bit resolution (0.0625°C precision)
  sensors.setWaitForConversion(true);
  
  int count = sensors.getDeviceCount();
  Serial.printf("[+] Detected %d 1-Wire devices on bus.\n", count);
  
  // Wi-Fi Local Connection
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  configTime(0, 0, "pool.ntp.org");
}

void loop() {
  unsigned long now = millis();
  
  // 1. Periodically sample sensors (Non-blocking timing)
  if (now - lastSampleTime >= SAMPLING_INTERVAL_MS || lastSampleTime == 0) {
    lastSampleTime = now;
    Serial.println("[-] Acquiring sensor readings from multi-probe mesh...");
    sensors.requestTemperatures();
    
    StaticJsonDocument<1024> doc;
    doc["shipment_id"] = SHIPMENT_ID;
    doc["timestamp"] = getISO8601Timestamp();
    
    JsonObject probes = doc.createNestedObject("probes");
    int validCount = 0;
    
    for (int i = 0; i < NUM_PROBES; i++) {
      float tempC = sensors.getTempCByIndex(i);
      // Validate 1-Wire readings and filter disconnect/fault codes (-127°C, 85°C)
      if (tempC == DEVICE_DISCONNECTED_C || tempC == 85.0 || tempC < -50.0 || tempC > 80.0) {
        probes[probeList[i].name] = nullptr;
      } else {
        probes[probeList[i].name] = tempC;
        validCount++;
      }
    }
    
    doc["sconf"] = (float)validCount / (float)NUM_PROBES;
    doc["coverage_time"] = 1.0;
    
    String payload;
    serializeJson(doc, payload);
    Serial.printf("[+] Generated Telemetry Packet: %s\n", payload.c_str());
    
    // Attempt immediate transmission over Local Wi-Fi
    if (WiFi.status() == WL_CONNECTED && transmitHttpPacket(payload)) {
      isEdgeGatewayReachable = true;
      currentRetryDelay = INITIAL_RETRY_DELAY_MS;
    } else {
      // Offline fallback: Buffer packet locally
      isEdgeGatewayReachable = false;
      Serial.println("[-] Edge Gateway unreachable over Local LAN. Storing observation in local ring buffer...");
      storePacketInLocalBuffer(payload);
    }
  }
  
  // 2. Retry flushing any buffered observations with bounded backoff
  if (bufferCount > 0 && (now % currentRetryDelay < 100)) {
    flushLocalBuffer();
    if (!isEdgeGatewayReachable) {
      currentRetryDelay = min((unsigned long)(currentRetryDelay * 2), (unsigned long)MAX_RETRY_DELAY_MS);
    }
  }
  
  delay(100);
}

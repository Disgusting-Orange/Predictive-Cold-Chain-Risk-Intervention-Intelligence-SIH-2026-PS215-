/*
  Cold Chain AI — ESP32 Direct Wi-Fi HTTPS Telemetry Ingestion
  ==============================================================
  Sends real-time sensor packets directly to the FastAPI / Supabase cloud backend.
  
  Key Features:
  - Uses WiFiClientSecure with setInsecure() for hassle-free HTTPS TLS handshake
  - Sends JSON payload to https://cold-chain-ai-ps215.vercel.app/api/telemetry
  - Prints AI Risk Score and Severity returned from the cloud on Serial Monitor
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

// ==========================================
// 1. NETWORK & BACKEND CONFIGURATION
// ==========================================
const char* WIFI_SSID     = "YOUR_WIFI_NAME";        // 2.4GHz Wi-Fi (or Mobile Hotspot)
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* BACKEND_URL   = "https://cold-chain-ai-ps215.vercel.app/api/telemetry";
const char* SHIPMENT_CODE = "SHP-1042";             // Associated shipment code
const char* DEVICE_ID     = "ESP32-HARDWARE-01";

// Ingestion interval (milliseconds)
const unsigned long POST_INTERVAL_MS = 4000; 
unsigned long lastPostTime = 0;

// ==========================================
// 2. SENSOR PINS & VARIABLES
// ==========================================
// Adjust pins based on your physical wiring:
const int DOOR_SENSOR_PIN = 4;    // Digital input for reed switch / door switch
const int TEMP_SENSOR_PIN = 34;   // Analog or digital sensor pin

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(DOOR_SENSOR_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.println("\n=============================================");
  Serial.println("  Cold Chain AI — ESP32 Sensor Client");
  Serial.println("=============================================");
  
  // Connect to Wi-Fi
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Wi-Fi Connected!");
    Serial.print("📡 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ Wi-Fi Connection Failed. Please check SSID/Password.");
  }
}

void loop() {
  // Reconnect Wi-Fi if disconnected
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ Wi-Fi lost. Reconnecting...");
    WiFi.reconnect();
    delay(2000);
    return;
  }

  // Periodic Telemetry Transmission
  if (millis() - lastPostTime >= POST_INTERVAL_MS) {
    lastPostTime = millis();
    sendTelemetryPacket();
  }
}

void sendTelemetryPacket() {
  // ----------------------------------------
  // Read Physical / Simulated Sensor Values
  // ----------------------------------------
  // Replace with your actual sensor library calls (e.g. dht.readTemperature()):
  float temperature = 4.2 + (random(-30, 30) / 100.0); // e.g. 3.9°C to 4.5°C
  float humidity = 48.0 + (random(-50, 50) / 10.0);    // e.g. 43% to 53%
  bool doorOpen = (digitalRead(DOOR_SENSOR_PIN) == LOW); // LOW = Door Open if pulled up
  float battery = 94.0;
  float speed = 36.5;
  float latitude = 13.0760;
  float longitude = 80.2660;

  // Build JSON Payload
  String jsonPayload = "{";
  jsonPayload += "\"shipmentId\":\"" + String(SHIPMENT_CODE) + "\",";
  jsonPayload += "\"deviceId\":\"" + String(DEVICE_ID) + "\",";
  jsonPayload += "\"temperature\":" + String(temperature, 2) + ",";
  jsonPayload += "\"humidity\":" + String(humidity, 1) + ",";
  jsonPayload += "\"latitude\":" + String(latitude, 5) + ",";
  jsonPayload += "\"longitude\":" + String(longitude, 5) + ",";
  jsonPayload += "\"speed\":" + String(speed, 1) + ",";
  jsonPayload += "\"doorOpen\":" + String(doorOpen ? "true" : "false") + ",";
  jsonPayload += "\"coolingPower\":72,";
  jsonPayload += "\"battery\":" + String(battery, 1);
  jsonPayload += "}";

  Serial.println("\n---------------------------------------------");
  Serial.print("📤 Sending Packet to Cloud: ");
  Serial.println(jsonPayload);

  // Configure Secure HTTPS Client
  WiFiClientSecure client;
  client.setInsecure(); // Bypass CA certificate verification for seamless connection

  HTTPClient http;
  if (http.begin(client, BACKEND_URL)) {
    http.addHeader("Content-Type", "application/json");
    
    digitalWrite(LED_BUILTIN, HIGH); // Flash LED during transmission
    int httpResponseCode = http.POST(jsonPayload);
    digitalWrite(LED_BUILTIN, LOW);

    if (httpResponseCode > 0) {
      Serial.print("📥 Cloud HTTP Response Code: ");
      Serial.println(httpResponseCode);
      String responseBody = http.getString();
      Serial.print("🤖 AI Risk Engine Response: ");
      Serial.println(responseBody);
    } else {
      Serial.print("❌ HTTP POST Request Failed: ");
      Serial.println(http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    Serial.println("❌ Unable to connect to backend server endpoint.");
  }
}

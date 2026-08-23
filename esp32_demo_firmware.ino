/*
 * ====================================================================
 * FrostLink ESP32 Cold-Chain AI Hardware Gateway -- Hackathon Demo Firmware
 * ====================================================================
 * Sensors:
 *  - DHT11 (GPIO 4) -> Temperature & Humidity
 *  - MQ-2  (GPIO 34) -> Smoke / Combustible Gas Spoilage Sensor
 *  - MQ-3  (GPIO 35) -> Alcohol / Fermentation Spoilage Sensor
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include <ArduinoJson.h>

// ================= 1. CONFIGURATION =================

const char* WIFI_SSID = "Kam's M35";         // Wi-Fi Name
const char* WIFI_PASS = "Whiplash&65_Dash";   // Wi-Fi Password

// Backend Laptop IP (Updated to match laptop IPv4 on Wi-Fi: 10.234.209.47)
const char* BACKEND_IP   = "10.234.209.47";    
const int   BACKEND_PORT = 8000;
const char* SHIPMENT_ID  = "SHP-1042";

// Fast Review Sampling Interval (3 seconds for fast demo)
const unsigned long SAMPLING_INTERVAL_MS = 3000;

// ================= 2. PIN SETUP =================

#define DHT_PIN 4
#define DHT_TYPE DHT11
#define MQ2_PIN 34
#define MQ3_PIN 35

DHT dht(DHT_PIN, DHT_TYPE);

unsigned long lastSampleTime = 0;
bool simDoorOpen = false;

String getApiUrl() {
  return "http://" + String(BACKEND_IP) + ":" + String(BACKEND_PORT) + "/api/telemetry";
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable Brownout Detector
  Serial.begin(115200);
  delay(1000);

  dht.begin();
  analogReadResolution(12); // ESP32 ADC: 0 - 4095

  Serial.println("\n==================================================");
  Serial.println("   FROSTLINK AI COLD CHAIN HARDWARE GATEWAY");
  Serial.println("==================================================");
  Serial.printf("[+] Connecting to Wi-Fi: %s ...\n", WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[✓] Wi-Fi Connected!");
    Serial.print("[+] ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("[+] Target Backend API: ");
    Serial.println(getApiUrl());
  } else {
    Serial.println("\n[!] Wi-Fi Connection failed. Will retry in loop.");
  }

  Serial.println("\n[+] DEMO COMMANDS (Type in Serial Monitor):");
  Serial.println("    'd' -> Toggle Container Door Open / Closed");
  Serial.println("==================================================\n");
}

void loop() {
  // Check for Serial commands during live demo
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'd') {
      simDoorOpen = !simDoorOpen;
      Serial.printf("\n[!] SIMULATION: Door Open = %s\n", simDoorOpen ? "TRUE" : "FALSE");
    }
  }

  unsigned long now = millis();
  if (now - lastSampleTime >= SAMPLING_INTERVAL_MS || lastSampleTime == 0) {
    lastSampleTime = now;

    // Read Hardware Sensors
    float temp = dht.readTemperature();
    float hum  = dht.readHumidity();
    int mq2Val = analogRead(MQ2_PIN);
    int mq3Val = analogRead(MQ3_PIN);

    if (isnan(temp)) temp = 4.5;
    if (isnan(hum))  hum  = 48.0;

    int maxGas = max(mq2Val, mq3Val);

    Serial.println("==================================================");
    Serial.printf(" [SENSOR READINGS] Temp: %.1f°C | Humidity: %.1f%% | MQ-2: %d | MQ-3: %d\n", 
                  temp, hum, mq2Val, mq3Val);

    // Transmit to Backend if Wi-Fi connected
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(getApiUrl());
      http.addHeader("Content-Type", "application/json");

      StaticJsonDocument<512> doc;
      doc["shipmentId"]   = SHIPMENT_ID;
      doc["deviceId"]     = "ESP32-HARDWARE-NODE";
      doc["temperature"]  = temp;
      doc["humidity"]     = hum;
      doc["doorOpen"]     = simDoorOpen;
      doc["speed"]        = 38.0;
      doc["coolingPower"] = (temp > 8.0) ? 30 : 80;
      doc["gasValue"]     = maxGas;
      doc["battery"]      = 94.0;

      JsonObject probes = doc.createNestedObject("probes");
      probes["Front_Top"]     = temp + 0.3;
      probes["Front_Middle"]  = temp;
      probes["Front_Bottom"]  = temp - 0.2;
      probes["Middle_Top"]    = temp + 0.4;
      probes["Middle_Middle"] = temp + 0.1;
      probes["Middle_Bottom"] = temp - 0.1;
      probes["Rear_Top"]      = temp + 0.6;
      probes["Rear_Middle"]   = temp + 0.2;
      probes["Rear_Bottom"]   = temp + 0.1;

      String jsonPayload;
      serializeJson(doc, jsonPayload);

      Serial.println(" [TRANSMITTING TO BACKEND]");
      int httpCode = http.POST(jsonPayload);

      if (httpCode > 0) {
        String responseStr = http.getString();
        
        // Parse & Display Backend ML Response
        StaticJsonDocument<1024> respDoc;
        DeserializationError err = deserializeJson(respDoc, responseStr);

        if (!err) {
          int riskScore     = respDoc["riskScore"] | 0;
          const char* level = respDoc["riskLevel"] | "UNKNOWN";
          int spoilage      = respDoc["spoilageRiskPercent"] | 0;
          int confidence    = respDoc["aiConfidencePercent"] | 0;
          const char* msg   = respDoc["message"] | "";

          Serial.println(" ------------------------------------------------");
          Serial.println(" [LIVE AI/ML MODEL INFERENCE RESPONSE]");
          Serial.printf("  ➜ RISK SCORE        : %d / 100\n", riskScore);
          Serial.printf("  ➜ RISK LEVEL        : %s\n", level);
          Serial.printf("  ➜ SPOILAGE RISK     : %d %%\n", spoilage);
          Serial.printf("  ➜ AI CONFIDENCE     : %d %%\n", confidence);
          Serial.printf("  ➜ ENGINE MESSAGE    : %s\n", msg);

          JsonArray shap = respDoc["shapFactors"];
          if (shap.size() > 0) {
            Serial.println("  ➜ SHAP EXPLANATIONS :");
            for (JsonObject factor : shap) {
              const char* desc = factor["description"] | "";
              float impact     = factor["impact"] | 0.0;
              Serial.printf("      - [%.2f] %s\n", impact, desc);
            }
          }
          Serial.println(" ------------------------------------------------");
        } else {
          Serial.printf(" [✓] Transmitted OK (HTTP %d)\n", httpCode);
        }
      } else {
        Serial.printf(" [✗] HTTP POST Failed, error: %s\n", http.errorToString(httpCode).c_str());
      }
      http.end();
    } else {
      Serial.println(" [!] Wi-Fi disconnected. Reconnecting...");
      WiFi.reconnect();
    }

    Serial.println("==================================================\n");
  }

  delay(100);
}

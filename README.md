# AI Cold Chain Optimisation Platform

SIH 2026 Prototype — Problem Statement #117 (Cold Chain)

This is a working prototype demonstrating an AI-powered Cold Chain Intelligence & Optimisation Platform. It monitors shipments, predicts cold-chain failures before they happen, evaluates route/intervention alternatives, and recommends the best action to prevent product loss.

## Tech Stack
- **Frontend**: React, Vite, TypeScript, Tailwind CSS (v4), Recharts, React-Leaflet
- **Backend**: Python, FastAPI, WebSocket
- **Data**: In-memory deterministic simulation for reliable SIH demos

## Prerequisites
- Node.js (v18+)
- Python (3.10+)

## Running the Prototype

### 1. Start the Backend
Open a terminal and run:
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
*(The backend runs a simulation loop and serves real-time data over WebSocket)*

### 2. Start the Frontend
Open a second terminal and run:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

## The SIH Demo Flow (Combined Failure)

Follow this exact sequence for the best demo:

1. **Initial State**: You will see the command centre with 5 active shipments around Chennai. All are in a "Normal" state with LOW risk.
2. **Select Shipment**: Click on `SHP-1042` (either on the map or in the table). Observe the stable temperature graph, low risk, and normal telemetry.
3. **Trigger Failure**: In the top right Scenario Controls, click **Combined Failure**.
4. **Observe Escalation**: 
   - The temperature will begin to rise.
   - Traffic delays will increase the ETA.
   - The risk score will climb from LOW → MEDIUM → HIGH → CRITICAL.
   - Alerts will appear in the left panel.
5. **Prediction**: The "Cold-Chain Forecast" panel will predict an excursion (e.g., "Excursion predicted in ~32 minutes").
6. **Intervention**: The AI will recommend an action (e.g., "DIVERT TO COLD STORAGE A") and show alternative routes with their predicted risks.
7. **Apply Action**: Click the orange **⚡ Apply Intervention** button.
8. **Recovery**: 
   - The vehicle on the map will divert to the new destination.
   - Temperature will stabilise and drop.
   - Risk will decrease back to LOW.
   - The "Estimated Impact" panel will show the financial loss avoided.
9. **Reset**: Click **Reset Demo** to start over.

## Architecture Notes
- The `simulator.py` generates deterministic telemetry but uses the exact same `risk_engine.py` as a real hardware integration would.
- To integrate real IoT sensors (e.g., ESP32), you would simply replace `simulator.py` with an MQTT or HTTP ingestion endpoint that populates the `shipments` state dictionary. The dashboard and predictive logic remain unchanged.

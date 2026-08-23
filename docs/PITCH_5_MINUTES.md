# Five minute pitch

## Opening

Every temperature-sensitive shipment carries a second deadline. The first deadline is the planned delivery time. The second is the moment when the cargo becomes unsafe. Most logistics systems show where a vehicle is. They do not show how much safe life is left in the cargo or which action can prevent a loss.

Cold Chain AI is built to close that gap.

## The problem

Cold-chain operators move vaccines, insulin, biologics, dairy, seafood, and other products that can lose value after a temperature excursion. The operational problem is not only temperature. It is the interaction between temperature drift, door openings, traffic delay, cooling performance, battery state, sensor quality, and the remaining route.

| Existing gap | Operational consequence |
|---|---|
| Monitoring is often retrospective | Teams discover damage after delivery |
| Alerts are based on single thresholds | Operators receive noise without context |
| Fleet and sensor data are separated | Dispatchers cannot connect cause and action |
| Manual intervention decisions are slow | Reroutes happen after safe life is exhausted |
| Compliance records are fragmented | Audits take time and lack a complete timeline |

## Market need

Cold-chain logistics is expanding with pharmaceutical distribution, vaccines, specialty medicines, food delivery, and biologics. The cost of a failure includes spoiled inventory, emergency replacement, missed service-level commitments, rejected deliveries, and loss of trust.

The first market is regional distributors and hospital supply networks that already have vehicles and sensors but lack a decision layer. They need a system that can start with a simulator or a small ESP32 fleet, integrate with existing operations, and add model sophistication without replacing their whole transport system.

## The solution

Cold Chain AI connects the physical shipment to an operational response.

```text
Sensors
  -> FastAPI ingestion
  -> Supabase event history
  -> risk and remaining-safe-life calculation
  -> alerts and intervention scenarios
  -> role-specific action
```

The system supports three users:

| User | Decision supported |
|---|---|
| Admin or operations team | Review fleet risk, approve reroutes, inspect audit history |
| Field agent or driver | Accept a route change, activate backup cooling, confirm handoff |
| Client or hospital viewer | Track shipment progress and condition without internal access |

## Product flow

1. An ESP32 or simulator sends a timestamped sensor reading.
2. The backend validates the physical ranges and stores the raw event.
3. The active risk engine combines temperature, trend, delay, door, and vehicle state.
4. The system records a risk prediction and opens an alert for high or critical conditions.
5. Operations compares continuing the route, rerouting to cold storage, or making an emergency delivery.
6. The selected action is assigned to the correct role and written to the audit trail.

## Novelty

The novelty is the connection between prediction and action.

| Common monitoring product | Cold Chain AI |
|---|---|
| Shows a temperature chart | Explains the factors increasing risk |
| Sends a threshold alert | Estimates remaining safe life and excursion probability |
| Leaves the response to a dispatcher | Compares intervention scenarios and loss avoided |
| Treats the shipment as one dashboard item | Gives Admin, Field Agent, and Client views |
| Stores scattered events | Produces a chronological compliance trail |
| Assumes a stable network | Leaves a path for edge buffering and ESP32 retries |

The model path is also designed for staged adoption. The current scorer can operate while the 40-feature FrostLink XGBoost model is validated against recorded telemetry. This keeps the product usable while improving prediction quality through measured comparison rather than an abrupt model replacement.

## Technology stack

| Layer | Technology | Reason |
|---|---|---|
| Device | ESP32, temperature, humidity, GPS, door, battery, and cooling sensors | Low-cost telemetry at the shipment edge |
| Frontend | React, Vite, TypeScript, Tailwind CSS | Fast role-based web interface |
| API | Python, FastAPI, Pydantic | Typed contracts and clear REST endpoints |
| Authentication | JWT with role checks | Separate Admin, Field Agent, and Client permissions |
| Database | Supabase PostgreSQL | Durable relational records for shipments, telemetry, alerts, predictions, interventions, and audits |
| Current risk engine | Python service with bounded operational rules | Immediate baseline and interpretable factors |
| Model package | XGBoost artifact with a 40-feature schema and SHAP service | Planned model-backed prediction and explanation path |
| Deployment | Vercel for frontend and HTTP API | Simple project deployment and previews |
| Live transport | FastAPI WebSocket locally or on a persistent backend host | Continuous dashboard updates |

## Business model

The initial model is business-to-business software for distributors, hospital networks, and specialist logistics providers.

| Revenue path | Description |
|---|---|
| Platform subscription | Charge per fleet, facility, or shipment volume |
| Hardware integration | Setup and device onboarding for ESP32 or existing telematics |
| Premium analytics | Model calibration, performance reporting, and compliance exports |
| Operations support | Incident workflows and managed alert response |

The product can start with a small fleet and expand by shipment count, facility count, and connected devices.

## Validation plan

The next validation steps are measurable.

| Stage | Measure |
|---|---|
| Hardware pilot | Delivery rate, retry success, battery impact, sensor coverage |
| Operations pilot | Alert precision, response time, reroute acceptance, avoided loss |
| Model comparison | Heuristic versus XGBoost probability, calibration, false alert rate |
| Commercial pilot | Spoilage incidents, service-level performance, operator time saved |

## Closing

Cold Chain AI is not only a dashboard. It is a decision system for the period between the first sign of risk and the last safe intervention. It starts with simple sensors and a working API, gives each participant the action they need, and has a clear path from interpretable baseline scoring to validated XGBoost predictions.

The goal is simple: identify the shipment at risk, explain why it is at risk, and help the team act while the cargo can still be saved.


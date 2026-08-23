# Cold Chain AI

SIH 2026, Problem Statement 215

Cold Chain AI monitors temperature-sensitive shipments, estimates spoilage risk, and gives operations teams an action path before cargo is lost.

## Current release status

| Area | Status | Notes |
|---|---|---|
| Frontend | Deployed | React, Vite, TypeScript, Tailwind CSS on Vercel |
| Backend | Deployed | FastAPI Python function on Vercel |
| Database | Connected | Supabase PostgreSQL through the transaction pooler |
| Authentication | Working | JWT login with Admin, Field Agent, and Client roles. Protected routes enforce bearer tokens and write roles |
| Telemetry ingestion | Working | ESP32 or simulator can send JSON over HTTP |
| Risk scoring | Working | Deterministic temperature, trend, delay, door, and speed scorer |
| FrostLink XGBoost model | Opt-in bridge implemented and locally verified | The full backend uses the CPU-only XGBoost package, derives all 40 features, and falls back to heuristics if inference fails. Vercel uses the lean heuristic dependency set |
| WebSocket telemetry | Available in the FastAPI code | Persistent sockets require a long-running host. Vercel deployments use authenticated HTTP polling if the socket closes |

The production API uses `backend/app/services/risk_service.py` by default. `backend/app/services/xgb_bridge.py` derives the model's 40 features from the rolling telemetry window and calls the packaged FrostLink model when `RISK_ENGINE_MODE=xgboost` is enabled in a full backend deployment. The bridge uses the native Booster API and `xgboost-cpu`. Vercel intentionally uses the lean root dependency set because its optimized Python function limit is 225 MB. If model loading or inference fails, the request falls back to the heuristic scorer.

## Repository layout

| Path | Purpose |
|---|---|
| `frontend/` | React user interface and role workspaces |
| `backend/app/` | FastAPI application, authentication, database models, routes, and services |
| `backend/app/services/risk_service.py` | Current production heuristic risk scorer |
| `ml_pipeline/service/` | Isolated FrostLink XGBoost and SHAP inference service |
| `ml_pipeline/model_artifacts/frostlink_xgb_v2/` | Frozen model, feature schema, threshold, and integrity manifest |
| `api/index.py` | Vercel entrypoint for FastAPI |
| `docs/ESP32_INTEGRATION.md` | Hardware setup and telemetry contract |
| `docs/PITCH_5_MINUTES.md` | Five minute presentation script |
| `vercel.json` | Frontend build, Python function, and API routing configuration |

## Local setup

### Requirements

| Tool | Recommended version |
|---|---|
| Node.js | 18 or newer |
| npm or pnpm | Current stable version |
| Python | 3.12 or newer |
| PostgreSQL | Supabase project or local PostgreSQL |

### Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Backend URLs:

| URL | Purpose |
|---|---|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/api/docs` | Interactive API documentation |
| `http://localhost:8000/api/health` | API health check |
| `ws://localhost:8000/ws` | Local telemetry WebSocket |

### Start the frontend

From the repository root:

```bash
npm install
npm run dev
```

Vite proxies `/api` and `/ws` to `http://127.0.0.1:8000`. For a separate backend host, set:

```text
VITE_API_URL=https://your-backend-host.example.com
VITE_WS_URL=wss://your-backend-host.example.com/ws
```

## Production deployment

The Vercel project is named `cold-chain-ai-ps215`. The project contains the Vite frontend and the FastAPI HTTP function.

| Setting | Value |
|---|---|
| Build command | `npm run build` |
| Frontend output | `dist/public` |
| FastAPI entrypoint | `api/index.py` |
| API route | `/api/*` |
| Database | Supabase PostgreSQL transaction pooler |
| Live socket recommendation | Deploy a persistent FastAPI host if continuous WebSocket telemetry is required. The Vercel frontend falls back to polling for authenticated dashboards |

Set these values in the Vercel project environment. Do not commit any value.

| Variable | Used by | Required |
|---|---|---|
| `DATABASE_URL` | FastAPI database connection | Yes |
| `JWT_SECRET` | JWT signing and verification | Yes |
| `CORS_ORIGINS` | Browser origin allowlist | Yes |
| `VERCEL` | Disables the local background demo loop in serverless execution | Yes |
| `RISK_ENGINE_MODE` | `heuristic` by default. `xgboost` is for a full backend deployment with `backend/requirements.txt` | No |
| `VITE_API_URL` | Optional separate API host | No, leave empty for same-domain API |
| `VITE_WS_URL` | Optional persistent WebSocket host | No |

The root `requirements.txt` is intentionally serverless-focused. It uses `asyncpg` for Supabase, plain `uvicorn`, and no scientific model runtime so the Vercel function stays below its optimized size limit. The fuller local or persistent-host backend setup, including `xgboost-cpu`, is in `backend/requirements.txt`.

The Supabase password supplied during setup was exposed in chat. Rotate it in Supabase and replace the Vercel `DATABASE_URL` secret before treating the deployment as production-ready.

## Authentication

The login screen includes demo buttons for the following seeded accounts.

| Role | Email | Password | Default workspace |
|---|---|---|---|
| Admin / Ops | `admin@coldchain.ai` | `admin123` | `/dashboard/admin` |
| Field Agent | `driver@coldchain.ai` | `driver123` | `/field-agent` |
| Client View | `client@coldchain.ai` | `client123` | `/client` |

These accounts are for demonstrations only. Replace them with managed accounts and stronger passwords before a real deployment.

## API contract

| Method | Endpoint | Authentication | Purpose |
|---|---|---|---|
| `GET` | `/api/health` | None | Backend and database health |
| `GET` | `/api/docs` | None | Deployed Swagger UI |
| `GET` | `/api/openapi.json` | None | Deployed OpenAPI schema |
| `GET` | `/api/redoc` | None | Deployed ReDoc UI |
| `POST` | `/api/auth/login` | None | Return a JWT |
| `POST` | `/api/auth/register` | None | Create a role account |
| `GET` | `/api/auth/me` | Bearer token | Return current user |
| `POST` | `/api/telemetry` | Hardware contract currently accepts direct ingestion | Store sensor reading and calculate risk. Response includes `modelVersion` |
| `GET` | `/api/shipments` | Bearer token | Fleet overview with latest risk |
| `GET` | `/api/shipments/{id}` | Bearer token | Shipment details and latest prediction |
| `GET` | `/api/products` | Bearer token | Product temperature profiles |
| `POST` | `/api/interventions/{id}/simulate` | Any Bearer token | Compare intervention scenarios |
| `POST` | `/api/interventions/{id}/approve` | Admin token | Approve a reroute |
| `POST` | `/api/interventions/{id}/field-accept` | Field Agent token | Accept a reroute |
| `POST` | `/api/interventions/{id}/backup-cooling` | Field Agent token | Record backup cooling action |
| `POST` | `/api/interventions/{id}/handoff` | Field Agent token | Record delivery handoff |
| `GET` | `/api/public/track/{id}` | None | Public tracking view |
| `GET` | `/api/audit/{id}` | Bearer token | Compliance history |

## Risk scoring and the XGBoost transition

The default production path is:

```text
ESP32 JSON
  -> POST /api/telemetry
  -> raw telemetry stored in Supabase
  -> configured risk scorer, heuristic by default or FrostLink XGBoost when enabled
  -> risk_predictions and alerts stored
  -> JSON returned to the frontend
```

The FrostLink model expects 40 features such as rolling temperature statistics, slopes, excursion area, sensor coverage, and valid probe count. A single raw ESP32 temperature reading does not contain those features. The implemented migration path is:

1. Store a rolling telemetry window per shipment.
2. Calculate the 40 features in the exact contract order.
3. Load and verify `frostlink_xgb_v2`.
4. Run CPU-only XGBoost probability inference and contribution-based explanations.
5. Map the model result into the existing `RiskPrediction` schema.
6. Keep the heuristic scorer as a fallback when the model or feature window is unavailable.
7. Set `RISK_ENGINE_MODE=xgboost` on a full backend host with `backend/requirements.txt`, then check live telemetry responses for `modelVersion: frostlink_xgb_v2`. Keep Vercel on `heuristic` unless the model runtime is moved to a separate service.

The swap is now available as a controlled configuration change. The default remains heuristic so an incomplete or sparse hardware history cannot silently produce an invalid model input.

## Hardware overview

The ESP32 should send an HTTP POST to the FastAPI ingestion endpoint. It should not connect directly to PostgreSQL. See `docs/ESP32_INTEGRATION.md` for wiring, payload fields, retry behavior, and a working `curl` example.

## Verification checklist

| Check | Command or action | Expected result |
|---|---|---|
| Frontend build | `npm run build` | Vite build completes |
| Backend import | `PYTHONPATH=backend python -c "from app.main import app"` | No import error |
| Health | `GET /api/health` | JSON with `status: ok` and `database: connected` |
| Login | Use any demo button | Redirect to the selected workspace |
| Telemetry | `POST /api/telemetry` | JSON with `riskScore`, `riskLevel`, and `shapFactors` |
| Fleet data | `GET /api/shipments` with Bearer token | JSON shipment list |
| Model status | On a full backend host, set `RISK_ENGINE_MODE=xgboost`, then send telemetry | Response `modelVersion` should identify `frostlink_xgb_v2`. Vercel currently reports `heuristic_v1` because of the function size limit |
| Public tracking | Open `/track/SHP-1042` while logged out | Data loads through `/api/public/track/{id}` without the protected fleet endpoint |
| Vercel API docs | Open `/api/docs` on the deployed domain | Swagger UI loads from the FastAPI function |

## Branch and deployment history

| Item | Value |
|---|---|
| Integration branch | `aiml-supabase-integration` |
| Latest documentation and demo login commit | See `git log --oneline main` |
| Remote | `origin` on the original GitHub repository |

# AI Cold Chain Optimisation Platform

SIH 2026 Prototype — Problem Statement #215 (Cold Chain)

Working prototype for an AI-powered cold-chain intelligence platform: shipment monitoring, risk views, and role-based workspaces.

## Tech Stack
- **Frontend**: React, Vite, TypeScript, Tailwind CSS
- **Backend**: Python, FastAPI, WebSocket
- **Data**: SQLite by default (PostgreSQL optional)

## Prerequisites
- Node.js (v18+)
- Python (3.10+)
- pnpm

## Running the Prototype

Backend and frontend run as separate processes and are wired through the Vite `/api` and `/ws` proxy in development.

### 1. Start the Backend
```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API docs: http://localhost:8000/docs  
Health: http://localhost:8000/health

### 2. Start the Frontend
From the **repo root** (not the `frontend/` folder):
```bash
pnpm install
pnpm dev
```
Open http://localhost:3000
# Cold Chain AI

## Integrated deployment

The repository now uses the modular FastAPI backend in `backend/` and the Vite frontend in `frontend/`. The AI/ML service and FrostLink model contract from the `aiml` branch live under `ml_pipeline/` and can be enabled by the backend service layer without exposing model files to the browser.

### Local development

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
npm install
npm run dev
```

The Vite proxy sends `/api` and `/ws` to `http://127.0.0.1:8000` by default.

### Production environment

Set `DATABASE_URL`, `JWT_SECRET`, and `CORS_ORIGINS` on the FastAPI host. Set `VITE_API_URL` and `VITE_WS_URL` in Vercel to the public backend HTTP and WebSocket URLs. Never put `DATABASE_URL`, the Postgres password, or a service-role key in frontend variables.

Vercel is configured for the static Vite frontend through `vercel.json`. Deploy the FastAPI service on a persistent Python host (Render, Railway, Fly.io, or equivalent) so `/ws` and the demo telemetry loop remain available. Vercel serverless functions are not a compatible replacement for that WebSocket service.

The Supabase password included in the project handoff was exposed in chat and must be rotated before production deployment. Store the replacement only in the backend host's secret manager.

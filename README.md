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

Backend and frontend are separate apps. They are not wired together yet.

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

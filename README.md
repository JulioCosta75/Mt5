# Forge Factory Lab — Sr. Atlas

> **Forge Factory Lab** is the engineering laboratory / company.
> **Sr. Atlas** is the AI supervisor and dashboard identity of the ecosystem.
>
> *Knowledge, validation and truth come before automation.*

Sr. Atlas is the real‑time supervision terminal for a MetaTrader 5 (MT5)
quantitative trading operation. Phase 1 delivers a production‑ready foundation:
an institutional dark trading dashboard, an MT5 Bridge for live account data, and
an n8n health‑monitoring workflow orchestrated under the Sr. Atlas identity.

---

## 1. Architecture

```
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  Frontend (React)            │        │  n8n — Sr. Atlas Health       │
│  Institutional dark terminal │        │  Monitor workflow             │
│  Dashboard · About · Docs    │        │  (polls the 3 health checks)  │
└──────────────┬───────────────┘        └───────────────┬──────────────┘
               │ REACT_APP_BACKEND_URL/api               │ HTTP
               ▼                                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI)  ·  /api/*                                          │
│  • mock mode (preview)  |  mt5 mode (MT5_BRIDGE_URL set)               │
│  • MongoDB / SQLite cache + per‑account overrides                     │
│  • /api/system/health · /healthcheck (standalone page)                │
└──────────────┬───────────────────────────────────────────────────────┘
               │ HTTP (mt5 mode)
               ▼
┌──────────────────────────────┐
│  MT5 Bridge (Windows)        │
│  bridge_server.py + MT5      │
│  account / positions / deals │
└──────────────────────────────┘
```

| Component      | Path            | Tech                                  |
|----------------|-----------------|---------------------------------------|
| Frontend       | `frontend/`     | React 19, React Router, Recharts      |
| Backend        | `backend/`      | FastAPI, Motor (MongoDB) / SQLite      |
| MT5 Bridge     | `mt5-bridge/`   | Python, MetaTrader5, FastAPI/uvicorn   |
| Windows setup  | `installer/`    | Inno Setup + Tkinter wizard + NSSM     |
| Supervision    | `ForgeFactoryLab_SrAtlas_HealthMonitor.json` | n8n workflow |

---

## 2. Installation

### Backend
```bash
cd backend
pip install -r requirements.txt
# runs under supervisor on 0.0.0.0:8001 in this environment
```
`backend/.env`:
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
CORS_ORIGINS=*
# Optional — switch from mock to live MT5 data:
# MT5_BRIDGE_URL=http://<bridge-host>:8002
```

### Frontend
```bash
cd frontend
yarn install
yarn start          # dev on :3000
```
`frontend/.env` uses `REACT_APP_BACKEND_URL` for all API calls.
Add `?noboot=1` to any URL to skip the welcome/loading splash (testing/deep links).

### MT5 Bridge (Windows)
```bat
cd mt5-bridge
copy .env.example .env   :: fill MT5 login / server
run.bat
```

### n8n Health Monitor
1. Open n8n → **Import from File** → `ForgeFactoryLab_SrAtlas_HealthMonitor.json`.
2. **Execute workflow** to run the first health check.
3. (Optional) enable the 5‑minute Schedule Trigger and activate the workflow.

---

## 3. Branding Guide

Official assets live in `frontend/src/assets/branding/` and are read through a
single module (`assets/branding/index.js`).

```
branding/
├── sr-atlas/logo-round.png     # favicon, app icon, header badge, boot, avatar
└── forge-factory/logo.png      # welcome, loading, about, documentation
```

| Where                       | Asset                     |
|-----------------------------|---------------------------|
| Browser tab / favicon       | Sr. Atlas round           |
| Dashboard header            | Sr. Atlas round + wordmark|
| Welcome / loading splash    | Forge Factory Lab + Sr. Atlas |
| About page                  | Forge Factory Lab + brand hierarchy |
| Documentation page          | Forge Factory Lab         |

**Rules:** use the supplied logos exactly as provided — do not redesign,
recreate, recolor or modify them. To update a logo, replace the file keeping
the same name; no code changes are required. Brand hierarchy: **Forge Factory
Lab** = company/laboratory, **Sr. Atlas** = supervising AI / dashboard identity.

---

## 4. Health Monitoring

Three health checks, all verified operational:

| Check                   | Endpoint                              |
|-------------------------|---------------------------------------|
| Atlas Backend Health    | `GET /api/system/health`              |
| Atlas Dashboard Health  | `GET /` (and `GET /api/`)             |
| MT5 Bridge Health       | `GET /health` on the bridge (`:8002`) |

A standalone status page is served at **`/healthcheck`**. The n8n workflow
(`Forge Factory Lab — Sr. Atlas Health Monitor`, 14 nodes) fans out to the three
probes, merges the responses and the **Sr. Atlas Report Builder** emits a
structured report; if any service is down, `status` becomes `ALERT` and the
operator notifier branch fires.

> In preview / mock mode the MT5 Bridge probe reports `n/a` because the Windows
> bridge is not running. Set `MT5_BRIDGE_URL` to enable live bridge health.

---

## 5. Phase 1 — Completed

- Institutional dark supervision terminal (accounts, risk, equity/drawdown, trades, alerts).
- FastAPI supervision API with mock + live (MT5 bridge) modes and cache/overrides.
- MT5 Bridge and Windows installer.
- n8n Sr. Atlas Health Monitor workflow (importable, no manual code).
- Full **Forge Factory Lab / Sr. Atlas** branding across the app.
- All three health checks operational.

## 6. Roadmap — Phase 2 (Monitoring → Intelligent Orchestration)

- Enable the 5‑minute schedule; wire **Telegram** notifications (state‑change only).
- MT5 telemetry probes: equity, margin, positions, pending orders, drawdown.
- **Sr. Atlas AI analysis** node: health + telemetry + economic calendar + news → risk assessment.
- Closed‑loop control (pause EA, flatten exposure) behind human/threshold gates.
- Per‑EA supervisors reporting up to Sr. Atlas (hierarchical orchestration).
- Audit trail & explainability for every AI decision.

---

## 7. Git — merging Phase 1 work into `main`

The repository had two branches with **unrelated histories**: `main` (the full
application) and a temporary `conflict_050726_1612` branch (the n8n workflow work).
Phase 1 consolidates everything onto `main`. Runbook (run once against the repo):

```bash
git checkout main

# Bring the unique Phase 1 n8n workflow files in from the conflict branch:
git checkout conflict_050726_1612 -- \
  ForgeFactoryLab_SrAtlas ForgeFactoryLab_SrAtlas_HealthMonitor.json ForgeFactoryLab_SrAtlas_README.md
git add -A
git commit -m "Phase 1: integrate Sr. Atlas Health Monitor workflow + branding into main"

git push origin main

# Remove the obsolete temporary conflict branch (remote + local):
git push origin --delete conflict_050726_1612
git branch -D conflict_050726_1612 2>/dev/null || true

git status   # should be clean; main is the single production branch
```

This preserves `main`'s history, adds the workflow, and leaves the repo clean
with `main` as the production branch. On the Emergent platform, use the
**“Save to GitHub”** button in the chat to push the current workspace to `main`.

---

© 2026 Forge Factory Lab · Sr. Atlas — Phase 1.

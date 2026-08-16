# Technical architecture (developers)

> This content previously lived in the in-app **Documentation** tab.
> End users now see **Help** (`/docs`) — the Portuguese user guide.
> Keep this file (and the root `README.md`) for engineering reference only;
> do not surface MongoDB / API / n8n internals in the main product navigation.

## Architecture

- **Frontend** — React institutional trading terminal (dashboard).
- **Backend** — FastAPI supervision API (`/api/*`), MongoDB / SQLite cache and per-account overrides.
- **MT5 Bridge** — Windows-side service exposing live MetaTrader 5 account, positions, deals and equity.
- **Sr. Atlas / n8n** — health-monitoring workflow that polls every core service and produces a structured supervision report.

## Health monitoring workflow

The Sr. Atlas Health Monitor (n8n) fans out to three probes in parallel:

- **Atlas Backend Health** — `GET /api/system/health`
- **MT5 Bridge Health** — `GET /health` on the bridge
- **Atlas Dashboard Health** — `GET /`

Responses are merged and the **Sr. Atlas Report Builder** emits a structured report
(`status`, `backend_ok`, `bridge_ok`, `dashboard_ok`). If any service is down, status
becomes `ALERT` and the operator notifier branch fires. Import
`ForgeFactoryLab_SrAtlas_HealthMonitor.json` into n8n and run *Execute workflow*.

## Installation (summary)

1. Backend: `pip install -r backend/requirements.txt` then run via supervisor / uvicorn.
2. Frontend: `yarn install` then `yarn start`.
3. MT5 Bridge (Windows): configure `mt5-bridge/.env` and run `run.bat`.
4. Set `MT5_BRIDGE_URL` in `backend/.env` to switch from mock to live data.
5. n8n: import the Sr. Atlas Health Monitor workflow and execute.

Full install and branding notes remain in the repository root `README.md`.

## Roadmap note (historical Phase 2 framing)

Sr. Atlas evolves from a monitoring dashboard into the intelligent supervisor of the
Forge Factory Lab ecosystem: state-change alerting, MT5 telemetry ingestion, Telegram
notifications, AI risk assessment and closed-loop control behind human confirmation gates.

See also root `README.md` § Architecture and § Installation.

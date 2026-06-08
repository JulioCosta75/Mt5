# QUANT.SUPERVISE — MT5 Quantitative Supervision Dashboard

## Original Problem Statement
User (Portuguese): "Olá. Estou a desenvolver um projeto de longo prazo relacionado com gestão quantitativa e supervisão de sistemas MT5. Gostaria de saber se dispõem de um endereço de e-mail para discussões mais detalhadas sobre arquitetura e planeamento de projeto."

After follow-up, user requested an MVP MT5 supervision dashboard with mock data:
- MT5 Accounts listing
- Equity curve, Drawdown
- Trade history, Alerts
- Risk management (kill switch + limits)
- Dark "trading terminal" visual (Bloomberg/TradingView)

## Architecture
- **Backend**: FastAPI (`/app/backend/server.py`) — in-memory mock data (8 accounts, deterministic seed). All routes under `/api`. MongoDB unused in this MVP.
- **Frontend**: React 19 + CRACO + Recharts + Geist/Geist Mono fonts. State managed via `useReducer` in `Dashboard.jsx`.
- **Persistence**: None — kill-switch toggles & risk-limit edits live in memory and reset on backend restart.

## User Personas
- **Professional quant trader / fund operator** — monitors multiple MT5 accounts running EAs across brokers; needs dense, real-time-feel data, sharp risk controls (kill switch, limits), and alert triage.

## Core Requirements
- Multi-account supervision (status, balance, equity, daily P&L, drawdown, margin)
- Equity curve & drawdown charts per account (90D)
- Filterable/sortable trade history table
- Severity-coded alerts with ACK (single + bulk)
- Risk management: kill switch + editable risk limits
- KPI ticker bar (total equity, daily P&L, alerts, server time)
- Manual refresh that hits /api/sim/tick to simulate live updates

## Implemented (Jan 2026)
### Backend (`/app/backend/server.py`)
- `GET /api/kpis` — aggregate KPIs across all accounts
- `GET /api/accounts` and `GET /api/accounts/{id}`
- `GET /api/accounts/{id}/equity` — 90D equity curve points
- `GET /api/accounts/{id}/drawdown` — drawdown series + max & current
- `GET /api/accounts/{id}/trades?limit&symbol&side` — filterable trades
- `GET /api/alerts?severity&unacknowledged_only` and `POST /api/alerts/{id}/ack`
- `POST /api/accounts/{id}/kill-switch` — toggle LIVE/PAUSED
- `PUT /api/accounts/{id}/risk-limits` — update risk limits
- `POST /api/sim/tick` — advance simulated equity for "live" feel

### Frontend (`/app/frontend/src/`)
- `Dashboard.jsx` — main shell, useReducer state, header with REFRESH FEED button
- `components/KpiTicker.jsx` — sticky ticker bar
- `components/AccountsTable.jsx` — 8 accounts, click to select
- `components/Charts.jsx` — EquityChart (area, green) + DrawdownChart (area, red)
- `components/TradesTable.jsx` — symbol/side filter, sortable columns, NET P&L + WIN%
- `components/RiskPanel.jsx` — kill switch + risk-limit form
- `components/AlertsPanel.jsx` — severity-coded list + single/bulk ACK
- `lib/api.js` — axios client + formatters (`fmt.money`, `fmt.pct`, `fmt.relative`, etc.)

### Visual
- Geist + Geist Mono fonts, custom CSS tokens (`--bg-base #0A0A0A`, signal greens/reds)
- All financial numbers monospace, right-aligned, tabular-nums
- Dense data layout (Control Room grid)
- Pulse-dot status indicators
- Status badges: LIVE green / PAUSED amber / ERROR red

### Testing — Iteration 1 (2026-06)
- Backend pytest: 17/17 pass (`/app/backend/tests/test_mt5_api.py`)
- Frontend Playwright flow: KPI ticker, account selection, charts render, trade filter, kill switch, risk-save, alert ACK, refresh button — all verified
- Success rate: 100% backend, 100% frontend

## Prioritized Backlog
### P0 (Next Action Items)
- Persist account state (kill switch + risk limits) to MongoDB so they survive backend restart
- WebSocket-based live tick stream (replace manual refresh button)
- Resync RiskPanel local form state after server-side refresh (code review note)

### P1
- Real MT5 bridge integration design (Python `MetaTrader5` SDK on a Windows worker → HTTP/ZeroMQ → this API)
- Authentication (user accounts; per-user account groups)
- Telegram / Email alert dispatcher (currently shown as enabled in System panel but not wired)
- Per-strategy performance breakdown view
- Audit log endpoint + Audit tab

### P2
- Multi-tenant orgs
- Compliance report exporter (PDF/CSV)
- Backtest viewer
- ML-Momentum / Strategy lab module

## Code Review Notes (from testing agent)
- `RiskPanel.jsx`: local `limits` state only initializes once; works for account switches (keyed remount) but not for parent-driven server refresh. Consider `useEffect(() => setLimits(account.risk_limits), [account.risk_limits])`.
- `Dashboard.jsx`: `selectedId || accounts[0]?.id` auto-reselects on deselect — fine for current UX.
- `TradesTable` sort comparator assumes consistent types — fine for current backend.
- Backend module-level `ACCOUNTS`/`ALERTS` reset on restart.

## Setup
- `sudo supervisorctl restart backend` after backend dependency changes
- Frontend hot-reloads automatically (CRACO)
- All URLs from env: `process.env.REACT_APP_BACKEND_URL` (frontend), no DB used in MVP

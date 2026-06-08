# QUANT.SUPERVISE — MT5 Quantitative Supervision Dashboard

## Original Problem Statement
User (Portuguese): asked about Emergent contact email, then requested an MVP MT5 supervision dashboard with mock data, then **Phase 1**: replace mock data with **real MT5 data** via the official `MetaTrader5` Python lib, while keeping the existing frontend exactly as-is.

## Phase 1 user decisions
1. MT5 terminal already running on a separate Windows host
2. 1 account now, design ready for N accounts
3. Bridge ↔ backend exposure to be decided later (local testing first)
4. Equity curve: both historical reconstruction AND going-forward snapshots
5. Fallback when bridge unreachable: cached last-known data in Mongo with `stale=true`

## Architecture
```
Frontend React (unchanged)
        │ /api/*
        ▼
Backend Linux (FastAPI)  ── MT5_MODE switch ──┐
   ├── mock data (default)                    │
   └── routes_mt5 → mt5_client (httpx)        │
                  → mt5_adapter (schema map)  │
                  → mt5_cache (Mongo)         │
                          │                   │
                          ▼  HTTPS + Bearer   │
                  Bridge Windows (FastAPI)    │
                  ├── mt5_service             │
                  ├── equity_reconstructor    │
                  ├── snapshot_recorder       │
                  └── storage (SQLite)        │
                          │ IPC               │
                          ▼                   │
                  MT5 Terminal ───────────────┘
```

## File layout
- `/app/backend/` — Linux FastAPI (`server.py`, `mt5_client.py`, `mt5_adapter.py`, `mt5_cache.py`, `routes_mt5.py`)
- `/app/mt5-bridge/` — Windows bridge project (deliver to user; runs on his Windows host)
- `/app/frontend/` — React 19 UI **(unchanged in Phase 1)**

## Implementation status
### Implemented (Jan 2026)
- ✅ MVP dashboard (mock 8 accounts) — iteration 1
- ✅ Phase 1 bridge architecture — iteration 2
  - Windows bridge: `MetaTrader5` wrapper + APScheduler 10s snapshots + SQLite + FastAPI server + bearer-token auth
  - Backend MT5 client (httpx, multi-bridge ready)
  - Adapter mapping MT5 schema → existing frontend schema (zero frontend changes)
  - Mongo cache with stale-data fallback + per-account kill-switch + risk-limits persistence
  - Mode switch via `MT5_BRIDGE_URL` env var (mock by default → real when configured)
  - 32/32 backend pytest cases passing (mock regression + adapter unit + MT5-mode activation)

### Endpoints
| Endpoint | Mock mode | MT5 mode |
|---|---|---|
| `GET /api/kpis` | ✅ 8 mock | ✅ aggregated from bridge |
| `GET /api/accounts` | ✅ | ✅ live (with cache fallback) |
| `GET /api/accounts/{id}` | ✅ ACC-001..008 | ✅ MT5-{login} |
| `GET /api/accounts/{id}/equity` | ✅ | ✅ reconstructed + snapshots |
| `GET /api/accounts/{id}/drawdown` | ✅ | ✅ derived |
| `GET /api/accounts/{id}/trades` | ✅ | ✅ from history_deals_get |
| `GET /api/accounts/{id}/positions` | (none) | ✅ pass-through (frontend Phase 2) |
| `GET /api/accounts/{id}/orders` | (none) | ✅ pass-through (frontend Phase 2) |
| `POST /api/accounts/{id}/kill-switch` | ✅ in-memory | ✅ Mongo (advisory; Phase 2 closes positions) |
| `PUT /api/accounts/{id}/risk-limits` | ✅ | ✅ Mongo |
| `GET /api/bridge/health` | n/a | ✅ |
| `POST /api/sim/tick` | ✅ | deprecated |

## Configuration
- **Default (preview)**: `/app/backend/.env` does **not** set `MT5_BRIDGE_URL` → mock mode → preview works
- **Production / real use**: set `MT5_BRIDGE_URL` and `MT5_BRIDGE_TOKEN` in `/app/backend/.env` → MT5 mode auto-activates on restart
- **Multi-account**: set `MT5_BRIDGE_URLS=url1,url2` and `MT5_BRIDGE_TOKENS=tok1,tok2`

## Prioritized backlog
### P0 (next session, when user has bridge running)
- Test end-to-end with real MT5 account: install bridge on Windows → tunnel → set env → verify dashboard
- Add `login_map` cache (login→bridge URL) to avoid O(N) bridge lookups per request (code review)
- Frontend: show `stale=true` indicator in System panel (subtle, no layout change)

### P1
- **Phase 2 kill-switch**: actually close MT5 positions via `mt5.order_send` (currently advisory-only)
- WebSocket from bridge → backend for sub-second tick feel
- Alerts rule engine (drawdown breach, margin level, daily-loss breach)
- Telegram/Email dispatcher
- Strategy grouping by magic number (currently every trade tagged "Live MT5")

### P2
- Multi-tenant + per-user account groups
- Audit log endpoint + Audit tab
- Compliance reports (PDF/CSV exporter)
- ML strategy lab (backtest viewer)

## Code review notes (from iter 2)
- [partially fixed] `list_accounts` no longer `break`s on first failure — tries all bridges then cache
- [fixed] `maybe_set_daily_anchor` now uses UTC date
- [open] Add login→bridge URL cache to avoid O(N) resolve cost
- [open] Status fallback on kill-switch disable can be stale
- [open] CORS middleware after router (cosmetic)

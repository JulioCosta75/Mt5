# Sr. Atlas — Forge Factory Lab Health Monitor & Supervisor (Phase 2)

> **Philosophy:** Knowledge, validation and truth come before automation.
> **Long-term objective:** *Sr. Atlas* is the intelligent orchestrator of the **Forge Factory Lab**; **n8n** executes the automations.

This package contains the first **importable** n8n workflow for the Forge Factory Lab.
Everything is pre-built as JSON — **no manual JavaScript typing is required** (safe for Android Remote Desktop operation).

- **Workflow file:** `ForgeFactoryLab_SrAtlas_HealthMonitor.json`
- **Supervisor name (fixed):** `Sr. Atlas`
- **Ecosystem name (fixed):** `Forge Factory Lab`

---

## 1. What it does

| Step | Node | Purpose |
|------|------|---------|
| Trigger | **When clicking 'Execute workflow'** | Manual run on demand |
| Trigger (optional) | **Schedule Trigger (Disabled)** | Auto-run every 5 min once enabled |
| Poll | **Atlas Backend Health** | `GET http://127.0.0.1:8001/api/system/health` |
| Poll | **MT5 Bridge Health** | `GET http://127.0.0.1:8002/health` |
| Poll | **Atlas Dashboard Health** | `GET http://127.0.0.1:8001/` |
| Merge | **Merge Health Responses** | Combines the 3 responses into one item |
| Logic | **Sr. Atlas Report Builder** | Builds the structured Sr. Atlas report |
| Decision | **All Core Services Healthy?** | Branches TRUE / FALSE |
| TRUE | **System Operational** | Marks the system healthy |
| FALSE | **System Alert / Degraded** | Marks degraded + routes to notifier |
| FALSE | **Notify Operator (Placeholder)** | Hook for Telegram / Slack / Email |
| Future | **Future AI Analysis (Disabled)** | Pre-wired AI call, key from env var |

### Sample report output
```json
{
  "supervisor": "Sr. Atlas",
  "ecosystem": "Forge Factory Lab",
  "status": "OK",
  "backend_ok": true,
  "bridge_ok": true,
  "dashboard_ok": true,
  "timestamp": "2026-06-01T10:00:00.000Z",
  "message": "All Forge Factory Lab core services are online and healthy."
}
```
When a service is down, `status` becomes `"ALERT"`, the matching `*_ok` flag turns `false`, and `message` lists exactly which services failed.

---

## 2. Step-by-step import instructions

1. Open n8n at **http://localhost:5678**.
2. Top-right **☰ (three dots)** menu → **Import from File...**
   *(or on the Workflows list: **Add workflow ▾ → Import from File**).*
3. Select **`ForgeFactoryLab_SrAtlas_HealthMonitor.json`**.
4. The canvas loads all nodes, notes and connections. Click **Save**.
5. Click **Execute workflow** (bottom bar) to run the first health check.
6. Open the **Sr. Atlas Report Builder** node → its output shows the structured report.

> ✅ No node needs manual code entry — the Code node ships pre-filled.

### Enable the 5-minute auto-check (optional)
- Click **Schedule Trigger (Disabled)** → toggle it **enabled** (top-right of the node, or right-click → *Activate*).
- Toggle the whole workflow **Active** (top-right switch) so the schedule runs in the background.

---

## 3. Explanation of every node

- **When clicking 'Execute workflow'** — Manual trigger. Fans out to all 3 health checks in parallel.
- **Schedule Trigger (Disabled)** — Same fan-out, but time-based (every 5 min). Shipped disabled so nothing runs unexpectedly on import.
- **Atlas Backend Health / MT5 Bridge Health / Atlas Dashboard Health** — HTTP Request (v4.2) nodes.
  - `fullResponse: true` so we capture the HTTP **status code**, not just the body.
  - `timeout: 8000ms` so a hung service fails fast.
  - `onError: continueRegularOutput` — **critical**: if one service is down, the workflow does **not** crash; it passes the error downstream so Sr. Atlas can report it truthfully.
- **Merge Health Responses** — Merge (v3.2, 3 inputs). Provides a single, visual convergence point for the three probes.
- **Sr. Atlas Report Builder** — Code node. Reads each health node **by name** (`$('Atlas Backend Health')` …) so a single failure never breaks evaluation. Produces the structured JSON report + an internal `all_ok` flag.
- **All Core Services Healthy?** — IF node. Passes when `all_ok === true`.
- **System Operational** (TRUE) — Tags the item `branch: SYSTEM OPERATIONAL`, `action_required: false`.
- **System Alert / Degraded** (FALSE) — Tags `branch: SYSTEM ALERT / DEGRADED`, `action_required: true`, then routes to the notifier.
- **Notify Operator (Placeholder)** — NoOp node. Replace with Telegram / Slack / Email node when ready (report is already on the input, ready to send).
- **Future AI Analysis (Disabled)** — HTTP Request, **disabled by default**. Pre-wired to POST the full context to your AI endpoint using the API key from an environment variable (never hardcoded). See section 4.

---

## 4. Where & how to insert the future AI API key (safely)

**The key is NEVER hardcoded.** The `Future AI Analysis` node reads it from an environment variable:

```
Authorization: Bearer {{$env.SR_ATLAS_AI_API_KEY}}
```

### Option A — Environment variable (matches your `SR_ATLAS_AI_API_KEY` suggestion)
On the Windows Server 2022 VPS, set the variable **before** n8n starts:

- **PowerShell (current session / service user):**
  ```powershell
  setx SR_ATLAS_AI_API_KEY "your_real_key_here"
  # optional custom endpoint:
  setx SR_ATLAS_AI_URL "https://api.your-provider.com/v1/analyze"
  ```
- **Or in an `.env` used by your n8n launcher**, add the line:
  ```
  SR_ATLAS_AI_API_KEY=your_real_key_here
  ```
- **Restart n8n** so it picks up the new variable.
- (n8n allows `$env` in expressions by default. If your instance sets `N8N_BLOCK_ENV_ACCESS_IN_NODE=true`, set it to `false` to allow this pattern — or use Option B.)

### Option B — n8n Credentials (recommended, encrypted at rest)
1. n8n → **Credentials → New → Header Auth** (or your provider's credential type).
2. Name: `Sr Atlas AI Key`. Header name `Authorization`, value `Bearer your_real_key_here`.
3. Open **Future AI Analysis** node → set **Authentication** to *Predefined/Generic Credential Type* → select `Sr Atlas AI Key`.
4. Remove the manual `Authorization` header so the credential provides it.

Then **enable** the node (right-click → *Activate*) once the AI endpoint is live.

The AI request body already ships with slots for everything Sr. Atlas will eventually reason over:
`health_report, trading_account_status, open_positions, pending_orders, equity, balance, margin, drawdown, trading_permissions, alerts, economic_calendar, market_news, specialised_eas`.

---

## 5. Recommended architecture improvements

1. **Dedicated dashboard health endpoint** — `GET /` returns HTML (heavy, no status semantics). Add a lightweight `GET /api/dashboard/health` returning `{ "status": "ok" }` and point the probe there.
2. **Standardise health payloads** — make Backend, Bridge and (future) Dashboard all return the same shape: `{ status, version, uptime_s, checks: {...} }`. Simplifies the Code node.
3. **Per-service latency capture** — record response time (ms) in the report to spot slow-but-alive services before they fail.
4. **Retry with backoff** on the HTTP nodes (2 retries, 2s) to avoid false alerts from transient blips.
5. **Persist reports** — append each report to a datastore (n8n Data Table / SQLite / Postgres) for history and trend analysis.
6. **Idempotent alerting** — only notify on *state change* (OK→ALERT / ALERT→OK), not every cycle, to avoid alert fatigue.
7. **Secrets policy** — all keys via Credentials or env vars only; enforce across every future workflow.

---

## 6. Phase 2 suggestions (Monitoring → Awareness)

- Enable the **5-minute schedule** and make the workflow Active.
- Wire the **Notify Operator** node to **Telegram** (ideal for Android): instant push alerts + `/status` command to run this workflow on demand.
- Add **MT5 account telemetry** probes: equity, balance, margin, open positions, pending orders, drawdown (via MT5 Bridge endpoints).
- Add **state-change alerting** and a daily "all-good" summary.
- Introduce a **Trading Permissions guard** node that reads whether auto-trading is enabled and flags mismatches.

---

## 7. Phase 3 suggestions (Awareness → Intelligent Orchestration)

- **Activate the Future AI Analysis node** — Sr. Atlas ingests health + trading telemetry + economic calendar + market news and returns a risk assessment with recommended actions.
- **Closed-loop control:** AI recommendations flow into action workflows (pause an EA, flatten exposure, widen stops) — always behind a human/threshold confirmation gate.
- **Economic calendar & news ingestion** (e.g., scheduled fetch) feeding the AI context.
- **Per-EA supervisors** reporting up to Sr. Atlas (hierarchical orchestration): Sr. Atlas = brain, specialised EA workflows = limbs.
- **Self-healing runbooks:** on known failure signatures, Sr. Atlas triggers restart/reconnect workflows automatically, then re-validates.
- **Audit trail & explainability:** log every AI decision + inputs for review — truth and validation before automation, at scale.

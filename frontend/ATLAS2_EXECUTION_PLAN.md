# Atlas 2 execution plan (A / B / C)

Executable split of the target-design report. Stacked on Stage 3 tip `b17af8e` (PR #44). **PR #46 stays paused** and is not a base.

This file is planning only. It does not enable Phase 3, change Revolution, or invent metrics.

**Gold is decorative/brand/selection/progress only, never a status signal.** Signal hex stays `--sig-pos/neg/warn/info`.

---

## Guardrails

- No merge to `main`. No production. No credentials, paid APIs, or new subscriptions.
- Do not delete recovery tags/branches.
- SAMPLE DATA / Configuration Mode stay explicit. Never present mock as live.
- Preserve existing `data-testid`s, payloads, and handlers unless a **C** contract is implemented in the same PR and documented.
- Revolution (`frontend/src/pages/Revolution.jsx`, purple nav, knowledge routes) stays isolated. Phase 3 correlation is **not** a Phase 2 data source.
- Stop and report (do not guess) if a change would pick a VaR/correlation/exposure **formula** that is not written below.

---

## A — Visual redesign using data that already exists

Each item is one draft PR, stacked on the previous **A** tip (not on #46). Tests + 1440 / 1024 / 768 captures.

| PR | Stage | What | Files (expected) | Not this PR |
|---|---|---|---|---|
| A0 | This document | Plan only | `frontend/ATLAS2_EXECUTION_PLAN.md` | CSS/JSX |
| A1 | Compact top nav | Primary tabs stay in the header. About / Docs / Settings move into a More menu. No `scale`/`zoom`. `nav-*` testids stay on the links. | `Dashboard.jsx`, `index.css`, nav tests | PageShell of Settings/About (optional later) |
| A2 | Overview hierarchy | Same widgets, less equal weight: hero first; table visually secondary; ticker compact; lower panels use card depth (gold top border / padding already used by `.hero-card`). | `Dashboard.jsx`, `index.css`, `KpiTicker.jsx` (class only) | Table columns, charts series color |
| A3 | Overview tables + 768 | Stronger selected row (class on `<tr>` scoped under `.overview-layout` so Risk stays frozen). Horizontal scroll **inside** `.scroll-area`; optional sticky Status+Account. Pager does not scroll X. | `index.css`; `AccountsTable.jsx` only if a `is-selected` class is required and **not** styled under `.risk-layout` | PR #46 CSS (do not merge it) |
| A4 | Equity / Drawdown chrome | Tokenize tooltip/grid; stack to 1 column at 768. Keep green/red **series** (result). Gold only on panel chrome. | `Charts.jsx`, `Dashboard.jsx`, `index.css` | 7D/30D (that is A5 / C1) |
| A5 | 7D / 30D / 90D window | Client filter of the **existing** equity/drawdown series by `t`. Formula: keep points with `t >= now − N days`. Empty window → unavailable, not fake points. Default remains 90D (current API). | `Charts.jsx`, tiny helper + tests | New backend history endpoint unless 90D series is too sparse (then C1) |
| A6 | Risk polish | Optional “within existing limits” badge using **only** current DD vs `max_daily_loss_pct` and open positions vs `max_open_positions` (same comparisons already drawn as bars). No exposure/VaR. Risk **table** still frozen unless founder lifts that freeze. | `RiskPanel.jsx`, tests | Sector/instrument % equity |
| A7 | Alerts + Supervision | Hierarchy (severity word, time, body). Replace leftover `#22C55E` hex in `SupervisionPanel` with `var(--sig-*)`. Scope alert CSS so Audit is reviewed in the same PR. | `AlertsPanel.jsx`, `SupervisionPanel.jsx`, `index.css` | New alert taxonomy |
| A8 | Reports + Audit | `.reports-layout` / `.audit-layout`; gold generate; expanded dossier uses `.section-heading`; Audit stacks at 768. Same generate/expand/filter/ACK. | `TabViews.jsx`, `index.css` | Four report-type products (B/C) |
| A9 | Recent activity (presentation) | Overview list built from **existing** `alerts` + `atlasReports`, sorted by timestamp, labeled as such. Sample prefix when `isSample`. | `Dashboard.jsx` or small component | New activity API |
| A10 | Settings / About / Docs chrome | Token leftover hex in `Settings.jsx`. | `pages/Settings.jsx`, `About.jsx` | License/MT5 behavior |
| A11 | Responsive pass | Header wrap, ticker overflow, charts 1-col, table inner scroll, no page X-scroll. | `index.css` | Mobile app |

---

## B — New functions (UI first: real data or **Unavailable**)

Build the surface in Atlas 2 chrome. If the source or formula is missing, render **Unavailable** with `data-testid` and a short reason. Do not fill with sample numbers in live mode.

| Function | Honest v1 (existing bytes) | Shows Unavailable until | Must not do |
|---|---|---|---|
| Instrument exposure | Group **open position rows** already stored on atlas reports (`symbol`, `volume` lots, `floating_pnl`). | `% of equity` / notional money — needs contract size / tick value (**C2**) | Invent USD notional from lots alone |
| Sector exposure | — | Symbol→sector map (**C3**) | Guess FX vs metals from letters |
| Position correlation | — | Returns series per symbol (**C4**). Not Phase 3 EA coincidence. | Call `/knowledge/v1/correlation` from Phase 2 Overview |
| VaR / portfolio risk | — | Documented VaR method + returns (**C5**) | Pick 95% historical VaR without founder formula |
| Report types + audit export | Same `postAtlasReport`; optional client export of the **already loaded** reports table (JSON of current rows, `isSample` watermark) | Separate PDF/CSV products, extra generators (**C6**) | Four fake report APIs |
| Real latency / system | Replace Dashboard hardcoded `"42 ms"` / `"6"` strategies. Use `/api/system/health` + `/api/supervision/snapshot` fields that **exist**. Latency: Unavailable until **C7**. Strategies count: use `api.eas()` length when loaded, else Unavailable (do not keep `"6"`). | RTT field on health (**C7**) | Keep `42 ms` as if measured |

---

## C — Data contracts (backend; separate PRs, flag-off or additive)

Do not implement C until the matching B surface exists showing Unavailable. No Phase 3 import.

### C1 — History window (only if A5 is insufficient)

```
GET /api/accounts/{id}/equity?days=7|30|90
GET /api/accounts/{id}/drawdown?days=7|30|90
```

Today: bridge `equity_history(days=90)` only. Response shape unchanged (`series: [{t, equity}]`). Mock mode must label sample.

### C2 — Instrument exposure (notional)

Requires per-position `volume`, `symbol`, `price_current`, and **contract size / tick value from the bridge**. Until the bridge sends those, UI stays lots + floating PnL only.

Proposed (not built): `GET /api/accounts/{id}/positions` passthrough of bridge `positions()` (already has ticket, symbol, side, volume, prices, profit, magic). Additive. No invented fields.

### C3 — Sector map

Static, documented table `symbol → sector` in repo **or** operator-editable store. Empty map ⇒ Unavailable. Do not infer.

### C4 — Position correlation

Needs a time series of mark-to-market or mid per symbol. **Not** EA-pair coincidence from Knowledge Engine. Contract TBD; stop rather than invent Pearson on two closing trades.

### C5 — VaR

Requires founder-written formula (horizon, confidence, series). Until then Unavailable. Implementing a default 95% 1-day historical VaR **is a product decision that changes calculation meaning — stop.**

### C6 — Report types / audit export

If product wants distinct generators, each must map to a `source` string already accepted by `postAtlasReport` or a new additive endpoint. File download of in-memory table is frontend-only (B).

### C7 — Health latency

Additive field, e.g. `bridge.rtt_ms` measured around the existing `client.health()` call in `system_health()`. Do not hardcode. Mock mode: omit field or `null` + sample presentation.

---

## Order and open PRs

| Open PR | Role |
|---|---|
| #42–#44 | Stages 1–3 visual language — review/merge only with founder screenshots |
| #45 | Design guide (doc) |
| **#46** | Overview table CSS — **paused, not approved, not a stack base** |
| A0+ | This plan, then A1… |

Stack: `b17af8e` → A0 → A1 → A2 → …  
C PRs are dedicated and must not mix with A visual PRs.

---

## Validation per PR

1. `CI=true yarn test --watchAll=false` — disclose pre-existing `Revolution.test.jsx` `@/` failure.
2. `git diff` empty for `Revolution.jsx`, `AGENTS.md`, backend (unless a C PR).
3. Captures 1440 / 1024 / 768 of the touched surface.
4. SAMPLE DATA still visible in mock.
5. Report: VERIFIED / INFERENCE / NOT VERIFIED.

# Atlas 2 design guide

Reference for the Atlas 2 dashboard visual language. **Every value below already exists in the codebase** (`frontend/src/index.css`, `RiskPanel.jsx`, `riskMetrics.js`) as of Stage 3 tip `b17af8e`. This document does not invent tokens, type sizes, breakpoints, or components.

Scope: Production Phase 2 dashboard chrome (Overview, Risk, and later Reports / Audit / remaining tables). Presentation only. No API, calculation, or navigation changes.

---

## 1. Color: brand gold vs signal

**Gold is decorative/brand only, never a status signal.**

Operational meaning (live / error / warning / info, P&amp;L up / down, alert severity, limit breach) uses `--sig-*` only. Gold is identity: titles, card accents, decorative bars, approved primary actions (generate / save) on restyled surfaces.

### Brand gold family (`frontend/src/index.css` `:root`)

| Token | Value |
|---|---|
| `--brand-gold` | `#C9A962` |
| `--brand-gold-bright` | `#E4D09A` |
| `--brand-gold-muted` | `#8C7344` |
| `--brand-gold-dim` | `#5C4B28` |
| `--brand-gold-soft` | `rgba(201, 169, 98, 0.12)` |
| `--brand-gold-border` | `rgba(201, 169, 98, 0.38)` |

### Signal tokens (operational; hex must not change)

| Token | Value | Typical use already in CSS |
|---|---|---|
| `--sig-pos` | `#22C55E` | `.cell-pos`, `.badge.live`, equity-up |
| `--sig-neg` | `#EF4444` | `.cell-neg`, `.badge.error`, `.alert-row.CRITICAL` |
| `--sig-warn` | `#F59E0B` | `.cell-warn`, `.badge.paused`, `.alert-row.WARNING`, config-mode dot |
| `--sig-info` | `#3B82F6` | `.cell-info`, `.alert-row.INFO` |

Soft companions exist: `--sig-pos-soft`, `--sig-neg-soft`, `--sig-warn-soft`, `--sig-info-soft` (10% alpha of the same hex).

`--sig-warn` `#F59E0B` is **not** brand gold `#C9A962`. Do not substitute one for the other.

### Surfaces already in `:root`

`--bg-base` `#0A0A0A`, `--bg-panel` `#121212`, `--bg-panel-hover` `#1A1A1A`, `--bd-default` `#27272A`, `--bd-subtle` `#18181B`, `--text-primary` `#F4F4F5`, `--text-secondary` `#A1A1AA`, `--text-tertiary` `#71717A`.

`--metal-sheen` `#1C1D21` and `--metal-edge` `#3A3B40` are declared and unused by panels as of Stage 3. Do not start using them without a dedicated stage.

Revolution nav stays purple (`#C4B5FD` / `#A855F7` on `.btn.nav-revolution`). Gold active-tab underline is `.btn.active:not(.nav-revolution)` only.

---

## 2. Type scale (as coded)

### Panel titles / section headings

`.panel-title` and `.section-heading` (shared rule):

| Viewport | `font-size` | `letter-spacing` |
|---|---|---|
| default | `11px` | `0.2em` |
| `max-width: 1024px` | `10.5px` | `0.16em` |
| `max-width: 768px` | `10px` | `0.12em` |

Always `text-transform: uppercase`, `font-weight: 600`, `color: var(--brand-gold)`.

### Hero numeric values (non-monotonic — document, do not “fix”)

`.hero-card-value` and `.risk-metric-value` share the same media-query steps:

| Viewport | `.hero-card-value` | `.risk-metric-value` |
|---|---|---|
| default (desktop) | `30px` | `28px` |
| `max-width: 1024px` | `26px` | `26px` |
| `max-width: 768px` | `28px` | `28px` |

The 30 → 26 → 28 step is what shipped in Stages 2–3. Later stages reuse it; they do not flatten it.

Both hero values: `font-weight: 700`, `line-height: 1.1`, `letter-spacing: -0.02em`.

`.hero-card-label` / `.risk-metric-label`: `11px`, `letter-spacing: 0.2em`, uppercase, gold, weight 600.

`.hero-card-detail`: `13px`, `--text-secondary`. `.risk-metric-limit`: `12px`, `--text-tertiary`.

### Body / tables (global vs wrappers)

Global `th, td`: `12px` cell, `10px` header, padding `8px 10px`.

`.overview-layout` and `.risk-layout` already raise cells to `13px` / padding `10px 12px` and headers to `11px` (Stages 2–3). Those bumps are **wrapper-scoped**, not a new global scale.

---

## 3. Card pattern

`.hero-card`:

- `background: var(--bg-panel)`
- `border: 1px solid var(--bd-default)`
- `border-top: 2px solid var(--brand-gold-border)` (2px gold top replaces the 1px top)
- `padding: 22px` (at `max-width: 768px`, padding becomes `20px`)
- `min-width: 0`

`.hero-strip`: 3-column grid, gap `18px`, padding `18px 20px 0`. Collapses to 2 columns at 1024px and 1 column at 768px (shared with `.risk-hero`).

---

## 4. Bar pattern

`.hero-bar-track`: height `3px`, `background: var(--bd-subtle)`.

`.hero-bar-fill`: `height: 100%`, `background: var(--brand-gold)` (decorative). Fill width is a percentage string from the display helper.

**A bar only renders when a real limit already exists to compare against. Never fabricate a limit.**

Coded today (`RiskMetric` `showBar`, `barPct` in `riskMetrics.js`):

- Overview compact: drawdown vs `max_daily_loss_pct`; margin level vs the existing 200% warn line; open positions vs `max_open_positions`.
- Risk full hero: margin level vs 200%; current drawdown vs `max_daily_loss_pct`. Equity, balance, margin used, daily P&amp;L, max DD, and leverage have **no** bar (no stored limit, or unit mismatch — daily P&amp;L money is not compared to `max_daily_loss_pct`).
- `barPct` returns `0` when the limit is missing, non-numeric, or `<= 0`. It clamps to 0–100. It does not invent risk rules.

---

## 5. Layout-wrapper convention

Shared components (`AccountsTable`, `AlertsPanel`, `RiskPanel`, …) stay structurally global. Visual upgrades that must not leak across tabs go on a **parent wrapper class**, not on the component’s root.

| Wrapper | Where | Purpose |
|---|---|---|
| `.overview-layout` | Overview `<main>` | Stage 2 column grid, table type bump, alert padding, gold generate-report |
| `.risk-layout` | Risk tab root | Stage 3 column stack, table type bump, gold save-limits |

Do **not** restyle `AccountsTable.jsx` globally to change Overview if the Risk tab must stay as Stage 3 left it. Scope Overview table work under `.overview-layout` only. Leave `.risk-layout th/td` rules unchanged unless a later stage is explicitly authorized to restyle the Risk table.

---

## 6. Breakpoints

Two existing scales only. **No third breakpoint.**

| Query | What already adapts |
|---|---|
| `max-width: 1024px` | Title size/tracking; `.hero-strip` / `.risk-hero` / `.risk-hero-full` → 2 columns; `.overview-layout` → 1 column; `.risk-limits-grid` → 2 columns; hero values `26px` |
| `max-width: 768px` | Title size/tracking; heroes → 1 column + `14px` horizontal padding; `.overview-layout` padding/gap `14px`; `.hero-card` padding `20px`; hero values `28px`; `.risk-limits-grid` → 1 column |

Desktop reference for review: **1440px**. Tablet: **1024px**. Narrow: **768px**.

Known leftover (not this guide): Overview charts grid is still inline `1fr 1fr` with no 768 collapse. That is a later stage, not a new breakpoint.

---

## 7. Approved references and concept direction

### Stage 2 / Stage 3 screenshots (founder attaches files)

Placeholders for the founder-captured desktop and narrow shots that approved the visual direction. The image bytes are not in the repo; names are the contract for where they belong:

| Stage | Viewport | Placeholder filename |
|---|---|---|
| Stage 2 Overview | 1440px | `atlas2-stage2-overview-1440.png` |
| Stage 2 Overview | 768px | `atlas2-stage2-overview-768.png` |
| Stage 3 Risk | 1440px | `atlas2-stage3-risk-1440.png` |
| Stage 3 Risk | 768px | `atlas2-stage3-risk-768.png` |

### Concept images (direction only — pixels were not available to the implementing agent)

Filenames as provided by the founder:

- `atlas2-overview-concept.png`
- `atlas2-risk-concept.png`
- `atlas2-alerts-reports-concept.png`

Written direction those files are meant to express: **dark/graphite background, gold brand accent, bold hero metrics, clear hierarchy**. Concept frames are not a license to add fields, merge tabs, change signal colors, or restyle Revolution.

---

## 8. Non-negotiables (every later stage)

- Presentation only: no new data, calculations, API calls, or props.
- Keep existing `data-testid`s. Keep SAMPLE DATA / configuration-mode indication.
- Top tab list unchanged (`Overview`, `Strategies`, `Risk`, `Reports`, `Audit`).
- `frontend/src/pages/Revolution.jsx` untouched. Revolution purple nav untouched.
- Signal hex values untouched.
- One purpose per branch. Draft PR. No merge without explicit founder authorization after reviewing images and tests.

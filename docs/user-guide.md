# Sr. Atlas — User Guide

Canonical text for the in-app **Guide** tab (`/guide`, `/docs`, `/help`).
If you change this file, update `frontend/src/pages/Guide.jsx` too.

## Why Sr. Atlas exists

Trading is often sold as a get-rich-quick promise. In reality, most people who try end up acting on impulse — which, without realizing it, looks a lot like gambling. Studying it properly is hard, almost like understanding how a plane flies.

Sr. Atlas was born out of a real need, not a business opportunity spotted from the outside: the need for something that helps **with every decision**, and helps you **learn from every decision** — not a tool that decides or trades for you.

**What Sr. Atlas does NOT do:**

- It does not decide for you.
- It does not buy or sell anything on its own.
- It never touches your money or your orders.

**What Sr. Atlas does:** it shows you the true state of your account, without filters or embellishment — even when that truth is uncomfortable (for example, warning you that data is outdated instead of pretending everything is fine). The decision is always yours; Atlas just helps you see clearly before you make it.

## The dashboard, element by element

### Top bar

- **Tabs** (Overview, Strategies, Risk, Reports, Audit, About, Guide, Settings) — the different views of Atlas.
- **REFRESH FEED** — forces an immediate data update instead of waiting for the next automatic cycle.
- **v0.3.0 · [code version] · session-XXXX** — the exact installed version and current session identifier, useful when reporting problems.

### Global stats bar

- **TOTAL EQUITY** — your account's real value right now (balance plus/minus the result of open positions).
- **DAILY P&L** — how much you've gained or lost today, in value and percentage.
- **AVG DD** — the average "drawdown" (how much the account has fallen since its most recent peak) across monitored accounts.
- **OPEN POS** — number of currently open positions.
- **ACCOUNTS** — how many accounts are "live" (connected and receiving real data) out of the total configured.
- **ALERTS** — number of active alerts needing your attention.
- **UTC, date/time** — the system's reference clock (universal time, not local time).

### "MT5 Accounts" table

One row per connected MT5 account. Columns: **Status**, **Account** (account number), **Broker**, **Strategy** (associated strategy name), **Balance**, **Equity** (real value, including open positions), **Daily P&L**, **DD** (current drawdown), **POS** (open positions), **LEV** (leverage, e.g. 1:30), **Margin %** (margin level — the higher it is, the more room you have before a broker "stop out").

### "Risk" section

Repeats the numbers for the selected account (Equity, Balance, Margin Used, Margin Lvl, Daily P&L, Cur DD, Max DD, Leverage), plus:

- **Risk Limits** — three fields you define: **Max Daily Loss (%)**, **Max Position Size (lots)**, **Max Open Positions** — with a **Save Limits** button.

### "Sr. Atlas Supervision" panel (right side)

- Overall status badge: **OK** or **WARNING**, with a sentence explaining why (e.g. "MT5 bridge is unavailable; displayed data comes from cache and may be outdated").
- Summary: Total Equity, Daily P&L, Accounts Live, Active Alerts.
- **Core Services** — the status of each internal Atlas component, one by one:
  - **Backend** — the "brain" that serves the dashboard.
  - **Store** — where the data is kept.
  - **Bridge** — the direct connection to your MT5 terminal.
  - **Dashboard** — the panel you're looking at right now.

  Each shows **OK** (green) or **DOWN** (red). If Bridge is "DOWN", the numbers you see come from a saved copy (cache), not live data — Atlas always warns you when this happens.
- **Generate Sr. Atlas Report** — button to create an account report.
- **Recent Reports** — list of reports already generated.

### Charts, below

- **Equity Curve · 90D** — your account's value over the last 90 days.
- **Drawdown · 90D** — drawdowns from peak over the same period.

### Trade history (bottom of Overview)

- **Trade History** — list of your already-closed trades: symbol, side (buy/sell), lots, open/close time, duration in minutes, result (P&L), and associated strategy. You can filter by symbol and side. At the top of the table: total net result (**NET**), win percentage (**WIN%**), and number of trades (**N**).

### Alerts panel (right side)

- **Alerts** — count of alerts by severity (red = critical, orange = warning, blue = info). Shows "No alerts" when there's nothing to flag.
- **System** — the technical "pulse" of the system: **API Latency**, **MT5 Bridge**, **Risk Engine**, **Telegram Notif**, **Last Heartbeat**, **Strategies Loaded**.

## The other tabs

### Strategies

Groups your accounts by strategy instead of by individual account — useful if you ever have multiple accounts following the same approach. Shows, per strategy: associated accounts, how many are live, total equity, daily P&L, open positions, average drawdown.

### Risk

The same "Risk" section described above (Risk Limits), as its own page.

### Reports

List of reports already generated via the "Generate Sr. Atlas Report" button, with status, message, and origin for each. Empty until you generate the first one.

### Audit

A historical log of system events (Atlas's "logbook") — separate from trade history. Empty until events are logged.

### About

Brand presentation page — the Forge Factory Lab logo and principles ("Knowledge, validation and truth come before automation") and Sr. Atlas's own. No functionality, identity only.

### Settings

Where you connect (or change, anytime, without reinstalling) your MT5 account:

- **MT5 Login** — your account number.
- **MT5 Password** — stored; leave blank to keep the current one.
- **Server / Broker** — your broker's server name (e.g. `PepperstoneUK-Demo`).
- **Terminal path** (optional) — where MT5 is installed; you usually don't need to touch this, Atlas finds it automatically.
- **Bridge port** — the technical port used for the connection (no need to change this unless you know exactly why).
- **Save & Connect** — saves and connects.
- **Clear** — clears the fields.

An indicator at the top always shows whether you're **Connected** or not, in real time.

## Before you start

You need:

1. A MetaTrader 5 account (demo or real) already created, with login, password, and server name (e.g. `PepperstoneUK-Demo`).
2. The MetaTrader 5 terminal installed on this computer.
3. In the MT5 terminal: go to **Tools → Options → Expert Advisors** and enable **"Allow algorithmic trading"**. Without this, Sr. Atlas connects to your account but can't confirm everything is ready.

## How to connect your account

1. Open Sr. Atlas.
2. Go to **Settings**.
3. Enter your MT5 login, password, and server.
4. Save. The dashboard should show your real data within seconds.

You don't need to open the MT5 terminal manually first — Sr. Atlas handles that on its own.

## What the dashboard states mean

| State | What it means |
|---|---|
| **OK / Healthy** | Everything connected and working normally. |
| **WARNING** | Connected, but something needs your attention — for example, "Allow algorithmic trading" disabled in the terminal. |
| **PAUSED** | Supervision is temporarily stopped — usually because the connection to the MT5 terminal was interrupted. |

Sr. Atlas never shows "all healthy" if your account connection is actually down — we'd rather warn you than lie to you about your account's status.

## Common problems

**"The dashboard isn't showing my data"**

- Confirm the MT5 terminal is installed on this computer.
- Confirm "Allow algorithmic trading" is enabled (see above).
- Confirm your login/password/server in Settings.

**"A warning about automated trading being disabled appears"**

- Go to the MT5 terminal → Tools → Options → Expert Advisors → enable "Allow algorithmic trading".

**"I installed it but nothing opens in the browser"**

- Wait a minute — the services may take a few seconds to start after installation.
- If it still doesn't open, try the "Start Atlas" shortcut in the Start menu.

## Where to get help

If the sections above don't solve it, use the **"Report Problem"** button on the dashboard. It automatically attaches the system's health status and relevant logs — never your credentials — and sends it directly to Forge Factory Lab, with one click.

---

*This document explains what Sr. Atlas does and doesn't do. If anything here doesn't match what you see on screen, trust what you see over this text — and please let us know.*

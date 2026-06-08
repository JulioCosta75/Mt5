import React from "react";
import { fmt } from "@/lib/api";

export default function KpiTicker({ kpis }) {
  if (!kpis) {
    return (
      <div className="ticker-row" data-testid="kpi-ticker-loading">
        <span className="ticker-item"><span className="label">Loading market state…</span></span>
      </div>
    );
  }
  const pnlClass = kpis.daily_pnl > 0 ? "cell-pos" : kpis.daily_pnl < 0 ? "cell-neg" : "";
  return (
    <div className="ticker-row" data-testid="kpi-ticker">
      <span className="ticker-item" data-testid="kpi-total-equity">
        <span className="label">Total Equity</span>
        <span className="val">{fmt.money(kpis.total_equity)}</span>
      </span>
      <span className="ticker-item" data-testid="kpi-daily-pnl">
        <span className="label">Daily P&amp;L</span>
        <span className={`val ${pnlClass}`}>{fmt.money(kpis.daily_pnl)} ({fmt.pct(kpis.daily_pnl_pct)})</span>
      </span>
      <span className="ticker-item" data-testid="kpi-avg-dd">
        <span className="label">Avg DD</span>
        <span className="val cell-neg">{fmt.pct(kpis.avg_drawdown)}</span>
      </span>
      <span className="ticker-item" data-testid="kpi-open-positions">
        <span className="label">Open Pos</span>
        <span className="val">{kpis.open_positions}</span>
      </span>
      <span className="ticker-item" data-testid="kpi-accounts">
        <span className="label">Accounts</span>
        <span className="val">
          <span className="cell-pos">{kpis.accounts_live}</span>
          <span style={{ color: "var(--text-tertiary)" }}> / {kpis.accounts_total}</span>
        </span>
      </span>
      <span className="ticker-item" data-testid="kpi-alerts">
        <span className="label">Alerts</span>
        <span className="val">
          {kpis.critical_alerts > 0 && <span className="cell-neg">{kpis.critical_alerts}c </span>}
          <span className="cell-warn">{kpis.active_alerts}</span>
          <span style={{ color: "var(--text-tertiary)" }}> active</span>
        </span>
      </span>
      <span className="ticker-item" style={{ marginLeft: "auto" }} data-testid="kpi-server-time">
        <span className="label">UTC</span>
        <span className="val">{fmt.time(kpis.server_time)}</span>
      </span>
    </div>
  );
}

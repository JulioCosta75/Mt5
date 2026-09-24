import React, { useState } from "react";
import { api, fmt, pnlClass } from "@/lib/api";

function Stat({ label, value, mono = true, cls = "" }) {
  return (
    <div style={{ padding: "8px 12px", borderRight: "1px solid var(--bd-default)" }}>
      <div style={{ fontSize: 9.5, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>
        {label}
      </div>
      <div className={`${mono ? "mono" : ""} ${cls}`} style={{ fontSize: 16, fontWeight: 500 }}>
        {value}
      </div>
    </div>
  );
}

function barPct(current, limit) {
  const c = Number(current);
  const l = Number(limit);
  if (!Number.isFinite(c) || !Number.isFinite(l) || l <= 0) return 0;
  return Math.min(100, Math.max(0, (c / l) * 100));
}

function RiskMetric({ label, value, valueClass, fill, limitLabel }) {
  return (
    <div>
      <div className="risk-metric-label">{label}</div>
      <div className={`risk-metric-value mono ${valueClass || ""}`}>{value}</div>
      <div className="hero-bar-track" aria-hidden="true">
        <div className="hero-bar-fill" style={{ width: `${fill}%` }} />
      </div>
      <div className="risk-metric-limit">{limitLabel}</div>
    </div>
  );
}

export default function RiskPanel({ account, onUpdate, isSample = false, showHeroBars = false }) {
  const [limits, setLimits] = useState(account.risk_limits);
  const [saving, setSaving] = useState(false);

  const saveLimits = async () => {
    setSaving(true);
    try {
      await api.updateRisk(account.id, {
        max_daily_loss_pct: parseFloat(limits.max_daily_loss_pct),
        max_position_size_lots: parseFloat(limits.max_position_size_lots),
        max_open_positions: parseInt(limits.max_open_positions, 10),
      });
      onUpdate();
    } finally { setSaving(false); }
  };

  return (
    <div className="panel" data-testid="risk-panel">
      <div className="panel-header">
        <span className="panel-title">
          Risk · {account.id} · {account.login}
          {isSample ? <span className="kbd" style={{ marginLeft: 8 }} data-testid="risk-sample-label">SAMPLE DATA</span> : null}
        </span>
      </div>
      {showHeroBars ? (
        <div className="risk-hero" data-testid="risk-hero">
          <RiskMetric
            label="Drawdown"
            value={fmt.pct(account.current_drawdown)}
            valueClass="cell-neg"
            fill={barPct(account.current_drawdown, limits.max_daily_loss_pct)}
            limitLabel={`limit ${limits.max_daily_loss_pct}%`}
          />
          <RiskMetric
            label="Margin level"
            value={`${fmt.num(account.margin_level, 1)}%`}
            valueClass={account.margin_level < 200 ? "cell-warn" : ""}
            fill={barPct(account.margin_level, 200)}
            limitLabel="warn below 200%"
          />
          <RiskMetric
            label="Open positions"
            value={String(account.open_positions)}
            fill={barPct(account.open_positions, limits.max_open_positions)}
            limitLabel={`limit ${limits.max_open_positions}`}
          />
        </div>
      ) : (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", borderBottom: "1px solid var(--bd-default)" }}>
        <Stat label="Equity" value={fmt.money(account.equity)} data-testid="account-equity-value" />
        <Stat label="Balance" value={fmt.money(account.balance)} />
        <Stat label="Margin Used" value={fmt.money(account.margin_used)} />
        <Stat
          label="Margin Lvl"
          value={`${fmt.num(account.margin_level, 1)}%`}
          cls={account.margin_level < 200 ? "cell-warn" : ""}
        />
        <Stat label="Daily P&L" value={fmt.money(account.daily_pnl)} cls={pnlClass(account.daily_pnl)} />
        <Stat label="Cur DD" value={fmt.pct(account.current_drawdown)} cls="cell-neg" />
        <Stat label="Max DD" value={fmt.pct(account.max_drawdown)} cls="cell-neg" />
        <Stat label="Leverage" value={`1:${account.leverage}`} />
      </div>
      )}
      <div style={{ padding: showHeroBars ? 22 : 14 }}>
        <div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10 }}>
          Risk Limits
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>
            Max Daily Loss (%)
            <input
              type="number"
              step="0.1"
              value={limits.max_daily_loss_pct}
              onChange={(e) => setLimits({ ...limits, max_daily_loss_pct: e.target.value })}
              data-testid="risk-max-daily-loss"
              style={{ marginTop: 4 }}
            />
          </label>
          <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>
            Max Position Size (lots)
            <input
              type="number"
              step="0.1"
              value={limits.max_position_size_lots}
              onChange={(e) => setLimits({ ...limits, max_position_size_lots: e.target.value })}
              data-testid="risk-max-position-size"
              style={{ marginTop: 4 }}
            />
          </label>
          <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>
            Max Open Positions
            <input
              type="number"
              step="1"
              value={limits.max_open_positions}
              onChange={(e) => setLimits({ ...limits, max_open_positions: e.target.value })}
              data-testid="risk-max-open-positions"
              style={{ marginTop: 4 }}
            />
          </label>
        </div>
        <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
          <button
            className="btn"
            onClick={saveLimits}
            disabled={saving}
            data-testid="risk-save-button"
          >
            {saving ? "Saving…" : "Save Limits"}
          </button>
        </div>
      </div>
    </div>
  );
}

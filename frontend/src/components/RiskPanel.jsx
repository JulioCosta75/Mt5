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

export default function RiskPanel({ account, onUpdate }) {
  const [limits, setLimits] = useState(account.risk_limits);
  const [saving, setSaving] = useState(false);
  const [killing, setKilling] = useState(false);

  const toggleKill = async () => {
    setKilling(true);
    try {
      await api.killSwitch(account.id, !account.kill_switch);
      onUpdate();
    } finally { setKilling(false); }
  };

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
        <span className="panel-title">Risk · {account.id} · {account.login}</span>
        <button
          className={`btn ${account.kill_switch ? "success" : "danger"}`}
          onClick={toggleKill}
          disabled={killing}
          data-testid="kill-switch-button"
        >
          {killing ? "…" : account.kill_switch ? "RESUME TRADING" : "KILL SWITCH"}
        </button>
      </div>
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
      <div style={{ padding: 14 }}>
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

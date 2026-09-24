import React, { useState } from "react";
import { api, fmt, pnlClass } from "@/lib/api";
import { barPct, resolveHeroLayout } from "./riskMetrics";

export { barPct, resolveHeroLayout };

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

function RiskMetric({ label, value, valueClass, fill, limitLabel, testId, showBar = false }) {
  return (
    <div data-testid={testId}>
      <div className="risk-metric-label">{label}</div>
      <div className={`risk-metric-value mono ${valueClass || ""}`}>{value}</div>
      {showBar ? (
        <>
          <div className="hero-bar-track" aria-hidden="true">
            <div className="hero-bar-fill" style={{ width: `${fill}%` }} />
          </div>
          {limitLabel ? <div className="risk-metric-limit">{limitLabel}</div> : null}
        </>
      ) : null}
    </div>
  );
}

function OverviewHeroMetrics({ account, limits }) {
  return (
    <div className="risk-hero" data-testid="risk-hero">
      <RiskMetric
        label="Drawdown"
        value={fmt.pct(account.current_drawdown)}
        valueClass="cell-neg"
        showBar
        fill={barPct(account.current_drawdown, limits.max_daily_loss_pct)}
        limitLabel={`limit ${limits.max_daily_loss_pct}%`}
      />
      <RiskMetric
        label="Margin level"
        value={`${fmt.num(account.margin_level, 1)}%`}
        valueClass={account.margin_level < 200 ? "cell-warn" : ""}
        showBar
        fill={barPct(account.margin_level, 200)}
        limitLabel="warn below 200%"
      />
      <RiskMetric
        label="Open positions"
        value={String(account.open_positions)}
        showBar
        fill={barPct(account.open_positions, limits.max_open_positions)}
        limitLabel={`limit ${limits.max_open_positions}`}
      />
    </div>
  );
}

function FullHeroMetrics({ account, limits }) {
  return (
    <div className="risk-hero risk-hero-full" data-testid="risk-hero-full">
      <RiskMetric
        label="Equity"
        value={fmt.money(account.equity)}
        testId="account-equity-value"
      />
      <RiskMetric
        label="Balance"
        value={fmt.money(account.balance)}
      />
      <RiskMetric
        label="Margin used"
        value={fmt.money(account.margin_used)}
      />
      <RiskMetric
        label="Margin level"
        value={`${fmt.num(account.margin_level, 1)}%`}
        valueClass={account.margin_level < 200 ? "cell-warn" : ""}
        showBar
        fill={barPct(account.margin_level, 200)}
        limitLabel="warn below 200%"
      />
      <RiskMetric
        label="Daily P&L"
        value={fmt.money(account.daily_pnl)}
        valueClass={pnlClass(account.daily_pnl)}
      />
      <RiskMetric
        label="Current DD"
        value={fmt.pct(account.current_drawdown)}
        valueClass="cell-neg"
        showBar
        fill={barPct(account.current_drawdown, limits.max_daily_loss_pct)}
        limitLabel={`limit ${limits.max_daily_loss_pct}%`}
      />
      <RiskMetric
        label="Max DD"
        value={fmt.pct(account.max_drawdown)}
        valueClass="cell-neg"
      />
      <RiskMetric
        label="Leverage"
        value={`1:${account.leverage}`}
      />
    </div>
  );
}

function ClassicStatGrid({ account }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", borderBottom: "1px solid var(--bd-default)" }}>
      <Stat label="Equity" value={fmt.money(account.equity)} />
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
  );
}

export default function RiskPanel({
  account,
  onUpdate,
  isSample = false,
  showHeroBars = false,
  heroLayout = null,
}) {
  const [limits, setLimits] = useState(account.risk_limits);
  const [saving, setSaving] = useState(false);
  const layout = resolveHeroLayout(heroLayout, showHeroBars);

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
      {layout === "full" ? (
        <FullHeroMetrics account={account} limits={limits} />
      ) : layout === "overview" ? (
        <OverviewHeroMetrics account={account} limits={limits} />
      ) : (
        <ClassicStatGrid account={account} />
      )}
      <div className={layout === "full" ? "risk-limits-card" : undefined} style={layout === "full" ? undefined : { padding: layout === "overview" ? 22 : 14 }}>
        <div className={layout === "full" ? "section-heading" : undefined} style={layout === "full" ? { marginBottom: 16 } : { fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10 }}>
          Risk Limits
        </div>
        <div className={layout === "full" ? "risk-limits-grid" : undefined} style={layout === "full" ? undefined : { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          <label className={layout === "full" ? "risk-limits-label" : undefined} style={layout === "full" ? undefined : { fontSize: 11, color: "var(--text-secondary)" }}>
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
          <label className={layout === "full" ? "risk-limits-label" : undefined} style={layout === "full" ? undefined : { fontSize: 11, color: "var(--text-secondary)" }}>
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
          <label className={layout === "full" ? "risk-limits-label" : undefined} style={layout === "full" ? undefined : { fontSize: 11, color: "var(--text-secondary)" }}>
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
        <div style={{ marginTop: layout === "full" ? 18 : 12, display: "flex", justifyContent: "flex-end" }}>
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

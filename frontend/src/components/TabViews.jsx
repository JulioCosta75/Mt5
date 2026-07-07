import React, { useCallback, useEffect, useState } from "react";
import { api, fmt, pnlClass } from "@/lib/api";
import AccountsTable from "@/components/AccountsTable";
import RiskPanel from "@/components/RiskPanel";
import AlertsPanel from "@/components/AlertsPanel";

const STATUS_CLASS = { OK: "cell-pos", WARNING: "cell-warn", ALERT: "cell-neg" };

function statusColor(status) {
  if (status === "OK") return "var(--sig-pos, #22C55E)";
  if (status === "WARNING") return "var(--sig-warn, #F59E0B)";
  if (status === "ALERT") return "var(--sig-neg, #EF4444)";
  return "var(--text-tertiary)";
}

/* ------------------------------------------------------------------ */
/* STRATEGIES                                                          */
/* ------------------------------------------------------------------ */
export function StrategiesView({ accounts }) {
  const groups = {};
  accounts.forEach((a) => {
    const key = a.strategy || "Unassigned";
    if (!groups[key]) {
      groups[key] = { strategy: key, total: 0, live: 0, equity: 0, daily_pnl: 0, positions: 0, ddSum: 0 };
    }
    const g = groups[key];
    g.total += 1;
    if (a.status === "LIVE") g.live += 1;
    g.equity += a.equity || 0;
    g.daily_pnl += a.daily_pnl || 0;
    g.positions += a.open_positions || 0;
    g.ddSum += a.current_drawdown || 0;
  });
  const rows = Object.values(groups).sort((a, b) => b.equity - a.equity);

  return (
    <div className="panel" data-testid="strategies-panel">
      <div className="panel-header">
        <span className="panel-title">Strategies · {rows.length}</span>
        <span className="kbd">grouped by strategy</span>
      </div>
      <div className="scroll-area" style={{ overflow: "auto" }}>
        <table data-testid="strategies-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th className="num">Accounts</th>
              <th className="num">Live</th>
              <th className="num">Total Equity</th>
              <th className="num">Daily P&L</th>
              <th className="num">Open Pos</th>
              <th className="num">Avg DD</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>No strategies.</td></tr>
            )}
            {rows.map((g) => (
              <tr key={g.strategy} data-testid={`strategy-row-${g.strategy}`}>
                <td style={{ color: "var(--text-primary)" }}>{g.strategy}</td>
                <td className="num">{g.total}</td>
                <td className="num cell-pos">{g.live}</td>
                <td className="num">{fmt.money(g.equity)}</td>
                <td className={`num ${pnlClass(g.daily_pnl)}`}>{fmt.money(g.daily_pnl)}</td>
                <td className="num">{g.positions}</td>
                <td className="num cell-neg">{fmt.pct(g.total ? g.ddSum / g.total : 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* RISK                                                                */
/* ------------------------------------------------------------------ */
export function RiskView({ accounts, selectedId, onSelect, selectedAccount, onUpdate }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <AccountsTable accounts={accounts} selectedId={selectedId} onSelect={onSelect} />
      {selectedAccount ? (
        <RiskPanel key={selectedAccount.id} account={selectedAccount} onUpdate={onUpdate} />
      ) : (
        <div className="panel" data-testid="risk-empty">
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
            Select an account to manage its risk limits and kill switch.
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* REPORTS (Sr. Atlas)                                                 */
/* ------------------------------------------------------------------ */
export function ReportsView() {
  const [reports, setReports] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await api.atlasReports({ limit: 50 });
      setReports(data.reports || []);
    } catch (e) {
      /* non-fatal */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onGenerate = async () => {
    setBusy(true);
    try {
      await api.postAtlasReport({ source: "reports-tab" });
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel" data-testid="reports-panel">
      <div className="panel-header">
        <span className="panel-title">Sr. Atlas Reports · {reports.length}</span>
        <button
          className="btn"
          onClick={onGenerate}
          disabled={busy}
          data-testid="reports-generate-button"
        >
          {busy ? "GENERATING…" : "GENERATE REPORT"}
        </button>
      </div>
      <div className="scroll-area" style={{ overflow: "auto" }}>
        <table data-testid="reports-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Message</th>
              <th>Source</th>
              <th className="num">Created</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={4} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>Loading reports…</td></tr>
            )}
            {!loading && reports.length === 0 && (
              <tr><td colSpan={4} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>No reports yet. Generate one above.</td></tr>
            )}
            {reports.map((r) => (
              <tr key={r.id} data-testid="reports-row">
                <td>
                  <span className={`mono ${STATUS_CLASS[r.status] || ""}`} style={{ fontWeight: 600 }}>{r.status}</span>
                </td>
                <td style={{ color: "var(--text-secondary)" }}>{r.message}</td>
                <td className="mono" style={{ color: "var(--text-tertiary)" }}>{r.source}</td>
                <td className="num mono" style={{ color: "var(--text-tertiary)" }}>{fmt.relative(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* AUDIT                                                               */
/* ------------------------------------------------------------------ */
export function AuditView({ alerts, onAck }) {
  const [reports, setReports] = useState([]);

  useEffect(() => {
    let cancelled = false;
    api.atlasReports({ limit: 50 })
      .then((data) => { if (!cancelled) setReports(data.reports || []); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 360px", gap: 14 }}>
      <div className="panel" data-testid="audit-panel">
        <div className="panel-header">
          <span className="panel-title">Audit Trail · Sr. Atlas Reports ({reports.length})</span>
        </div>
        <div className="scroll-area" style={{ overflow: "auto" }}>
          <table data-testid="audit-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Event</th>
                <th>Source</th>
                <th className="num">When</th>
              </tr>
            </thead>
            <tbody>
              {reports.length === 0 && (
                <tr><td colSpan={4} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>No audit records yet.</td></tr>
              )}
              {reports.map((r) => (
                <tr key={r.id} data-testid="audit-row">
                  <td><span className={`mono ${STATUS_CLASS[r.status] || ""}`} style={{ fontWeight: 600 }}>{r.status}</span></td>
                  <td style={{ color: "var(--text-secondary)" }}>{r.message}</td>
                  <td className="mono" style={{ color: "var(--text-tertiary)" }}>{r.source}</td>
                  <td className="num mono" style={{ color: "var(--text-tertiary)" }}>{fmt.relative(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <aside style={{ minWidth: 0 }}>
        <AlertsPanel alerts={alerts} onAck={onAck} />
      </aside>
    </div>
  );
}

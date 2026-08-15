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
/* STRATEGIES — one row per EA (magic number)                          */
/* ------------------------------------------------------------------ */
export function StrategiesView({ accounts, isSample = false }) {
  const [eas, setEas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null); // { account_id, magic, label }
  const [trades, setTrades] = useState([]);
  const [tradesLoading, setTradesLoading] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.eas();
      setEas(Array.isArray(data?.eas) ? data.eas : []);
    } catch (e) {
      setError(e?.message || "Failed to load EAs");
      setEas([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const onSelectEa = async (ea) => {
    setSelected(ea);
    setTradesLoading(true);
    try {
      const data = await api.trades(ea.account_id, { magic: ea.magic, limit: 100 });
      setTrades(Array.isArray(data?.trades) ? data.trades : []);
    } catch {
      setTrades([]);
    } finally {
      setTradesLoading(false);
    }
  };

  const onRename = async (ea) => {
    const next = window.prompt("Nome do EA (deixe vazio para remover o override manual):", ea.label || "");
    if (next === null) return;
    try {
      await api.renameEa(ea.account_id, ea.magic, next.trim() === "" ? null : next.trim());
      await reload();
      if (selected && selected.account_id === ea.account_id && selected.magic === ea.magic) {
        const refreshed = (await api.eas()).eas?.find(
          (r) => r.account_id === ea.account_id && r.magic === ea.magic
        );
        if (refreshed) setSelected(refreshed);
      }
    } catch (e) {
      window.alert(e?.message || "Falha ao renomear EA");
    }
  };

  // Sample / mock mode: keep legacy account.strategy grouping as a fallback.
  if (isSample) {
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
          <span className="panel-title">
            Strategies · {rows.length}
            <span className="kbd" style={{ marginLeft: 8 }} data-testid="strategies-sample-label">SAMPLE DATA</span>
          </span>
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
              {rows.map((g) => (
                <tr key={g.strategy} data-testid={`strategy-row-${g.strategy}`}>
                  <td style={{ color: "var(--text-primary)" }}>{g.strategy}</td>
                  <td className="num">{g.total}</td>
                  <td className="num cell-live">{g.live}</td>
                  <td className="num cell-live">{fmt.money(g.equity)}</td>
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="panel" data-testid="strategies-panel">
        <div className="panel-header">
          <span className="panel-title">
            Expert Advisors · {eas.length}
          </span>
          <span className="kbd">grouped by magic number</span>
        </div>
        <div className="scroll-area" style={{ overflow: "auto" }}>
          {loading ? (
            <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
              Loading EAs…
            </div>
          ) : error ? (
            <div style={{ padding: 24, textAlign: "center", color: "var(--sig-neg)", fontSize: 12 }} data-testid="strategies-error">
              {error}
            </div>
          ) : (
            <table data-testid="strategies-table">
              <thead>
                <tr>
                  <th>EA</th>
                  <th className="num">Magic</th>
                  <th>Account</th>
                  <th className="num">Open Pos</th>
                  <th className="num">Floating</th>
                  <th className="num">Realized</th>
                  <th className="num">Net P&L</th>
                  <th className="num">Trades</th>
                  <th className="num">DD</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {eas.length === 0 && (
                  <tr>
                    <td colSpan={10} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>
                      No EAs found yet. Open trades or history with a magic number will appear here.
                    </td>
                  </tr>
                )}
                {eas.map((ea) => {
                  const active =
                    selected
                    && selected.account_id === ea.account_id
                    && selected.magic === ea.magic;
                  return (
                    <tr
                      key={ea.id}
                      data-testid={`strategy-row-${ea.magic}`}
                      onClick={() => onSelectEa(ea)}
                      style={{
                        cursor: "pointer",
                        background: active ? "var(--bg-elevated, rgba(255,255,255,0.04))" : undefined,
                      }}
                    >
                      <td style={{ color: "var(--text-primary)" }}>
                        {ea.label}
                        {ea.label_source === "manual" ? (
                          <span className="kbd" style={{ marginLeft: 8 }}>renamed</span>
                        ) : null}
                      </td>
                      <td className="num mono">{ea.magic}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{ea.account_id}</td>
                      <td className="num cell-live">{ea.open_positions}</td>
                      <td className={`num ${pnlClass(ea.floating_pnl)}`}>{fmt.money(ea.floating_pnl)}</td>
                      <td className={`num ${pnlClass(ea.realized_pnl)}`}>{fmt.money(ea.realized_pnl)}</td>
                      <td className={`num ${pnlClass(ea.net_pnl)}`}>{fmt.money(ea.net_pnl)}</td>
                      <td className="num">{ea.trade_count}</td>
                      <td className="num cell-neg">
                        {ea.drawdown_unit === "money"
                          ? fmt.money(-(ea.current_drawdown_money || 0))
                          : fmt.pct(ea.current_drawdown)}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn"
                          data-testid={`ea-rename-${ea.magic}`}
                          style={{ padding: "2px 8px", fontSize: 11 }}
                          onClick={(ev) => { ev.stopPropagation(); onRename(ea); }}
                        >
                          Rename
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selected && (
        <div className="panel" data-testid="ea-trades-panel">
          <div className="panel-header">
            <span className="panel-title">
              Trades · {selected.label}
              <span className="kbd" style={{ marginLeft: 8 }}>magic {selected.magic}</span>
            </span>
            <button type="button" className="btn" style={{ padding: "2px 8px", fontSize: 11 }} onClick={() => setSelected(null)}>
              Close
            </button>
          </div>
          <div className="scroll-area" style={{ overflow: "auto", maxHeight: 360 }}>
            {tradesLoading ? (
              <div style={{ padding: 20, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>Loading trades…</div>
            ) : (
              <table data-testid="ea-trades-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th className="num">Lots</th>
                    <th className="num">P&L</th>
                    <th>Closed</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ textAlign: "center", padding: 16, color: "var(--text-tertiary)" }}>
                        No closed trades for this EA in the history window.
                      </td>
                    </tr>
                  )}
                  {trades.map((t) => (
                    <tr key={t.id}>
                      <td>{t.symbol}</td>
                      <td>{t.side}</td>
                      <td className="num">{fmt.num(t.lots, 2)}</td>
                      <td className={`num ${pnlClass(t.pnl)}`}>{fmt.money(t.pnl)}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{fmt.time(t.close_time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* RISK                                                                */
/* ------------------------------------------------------------------ */
export function RiskView({ accounts, selectedId, onSelect, selectedAccount, onUpdate, isSample = false }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <AccountsTable accounts={accounts} selectedId={selectedId} onSelect={onSelect} isSample={isSample} />
      {selectedAccount ? (
        <RiskPanel key={selectedAccount.id} account={selectedAccount} onUpdate={onUpdate} isSample={isSample} />
      ) : (
        <div className="panel" data-testid="risk-empty">
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
            Select an account to manage its risk limits.
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
          className="btn primary"
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
export function AuditView({ alerts, onAck, isSample = false }) {
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
          <span className="panel-title">
            Audit Trail · Sr. Atlas Reports ({reports.length})
            {isSample ? <span className="kbd" style={{ marginLeft: 8 }} data-testid="audit-sample-label">SAMPLE DATA</span> : null}
          </span>
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
        <AlertsPanel alerts={alerts} onAck={onAck} isSample={isSample} />
      </aside>
    </div>
  );
}

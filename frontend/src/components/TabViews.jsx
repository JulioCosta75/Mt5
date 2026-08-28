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
                      <td className="num">{ea.open_positions}</td>
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
/* REPORTS (Sr. Atlas) — Part 5: filter + expandable enriched rows     */
/* ------------------------------------------------------------------ */
function LimitCell({ label, breached, detail }) {
  return (
    <div style={{ fontSize: 11, lineHeight: 1.4 }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}: </span>
      <span className={`mono ${breached ? "cell-warn" : "cell-pos"}`}>
        {breached ? "BREACHED" : "OK"}
      </span>
      {detail ? (
        <span className="mono" style={{ color: "var(--text-tertiary)", marginLeft: 6 }}>
          {detail}
        </span>
      ) : null}
    </div>
  );
}

function ReportExpanded({ report }) {
  const limits = report.limits_status || {};
  const comparison = report.comparison_to_previous;
  const openPos = report.open_positions || [];
  const closed = report.closed_trades_since_previous || [];
  const alertEvents = report.alerts_since_previous || [];
  const metrics = report.metrics || {};

  return (
    <div
      data-testid={`reports-expanded-${report.id}`}
      style={{
        padding: "10px 12px 14px",
        background: "var(--bg-elevated, rgba(255,255,255,0.02))",
        borderTop: "1px solid var(--bd-subtle)",
        display: "grid",
        gap: 12,
        fontSize: 12,
      }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 8 }}>
        <div>
          <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 2 }}>Account</div>
          <div className="mono">{report.account_id || "—"} · login {report.login ?? "—"}</div>
        </div>
        <div>
          <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 2 }}>Server</div>
          <div className="mono">{report.server || "—"}</div>
        </div>
        <div>
          <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 2 }}>Origin</div>
          <div className="mono">{report.data_origin || "—"} · {report.source || "—"}</div>
        </div>
        <div>
          <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 2 }}>Type / Session</div>
          <div className="mono">{report.account_type || "not_available"} / {report.session || "not_available"}</div>
        </div>
      </div>

      <div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 4 }}>Metrics</div>
        <div className="mono" style={{ display: "flex", flexWrap: "wrap", gap: "8px 14px" }}>
          <span>equity {fmt.money(metrics.equity, report.currency)}</span>
          <span className={pnlClass(metrics.daily_pnl)}>daily PnL {fmt.money(metrics.daily_pnl, report.currency)}</span>
          <span>open pos {metrics.open_positions ?? "—"}</span>
          <span>DD {fmt.pct(metrics.current_drawdown)}</span>
        </div>
      </div>

      <div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 4 }}>Limits</div>
        <div style={{ display: "grid", gap: 4 }}>
          <LimitCell
            label="Drawdown"
            breached={!!limits.drawdown?.breached}
            detail={
              limits.drawdown
                ? `${limits.drawdown.current_pct}% / ${limits.drawdown.limit_pct}%`
                : null
            }
          />
          <LimitCell
            label="Open positions"
            breached={!!limits.open_positions?.breached}
            detail={
              limits.open_positions
                ? `${limits.open_positions.current} / ${limits.open_positions.limit}`
                : null
            }
          />
          <LimitCell
            label="Volume"
            breached={!!limits.position_volume?.breached}
            detail={
              limits.position_volume
                ? `${limits.position_volume.largest_open_lots} / ${limits.position_volume.limit_lots} lots`
                : null
            }
          />
        </div>
      </div>

      {comparison ? (
        <div>
          <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 4 }}>
            vs previous ({comparison.previous_report_id || "—"})
          </div>
          <div className="mono" style={{ display: "flex", flexWrap: "wrap", gap: "8px 14px" }}>
            <span>equity Δ {comparison.equity?.delta ?? "—"}</span>
            <span>daily PnL Δ {comparison.daily_pnl?.delta ?? "—"}</span>
            <span>open pos Δ {comparison.open_positions?.delta ?? "—"}</span>
            <span>DD Δ {comparison.current_drawdown?.delta ?? "—"}</span>
            <span>bridge {comparison.bridge_link || "—"}</span>
          </div>
        </div>
      ) : (
        <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>No previous same-account report for comparison.</div>
      )}

      <div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 4 }}>
          Open positions ({openPos.length})
        </div>
        {openPos.length === 0 ? (
          <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>None</div>
        ) : (
          <div className="mono" style={{ display: "grid", gap: 2, maxHeight: 120, overflow: "auto" }}>
            {openPos.slice(0, 40).map((p, i) => (
              <div key={`${p.ticket || i}`}>
                {p.symbol} {p.side} {p.volume} · float {p.floating_pnl} · magic {p.magic ?? "—"}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 4 }}>
          Closed since previous ({closed.length})
        </div>
        {closed.length === 0 ? (
          <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>None</div>
        ) : (
          <div className="mono" style={{ display: "grid", gap: 2, maxHeight: 120, overflow: "auto" }}>
            {closed.slice(0, 40).map((t, i) => (
              <div key={`${t.close_time || i}-${t.symbol}`}>
                {t.symbol} {t.side} {t.lots} · PnL {t.pnl} · {fmt.timeShort(t.close_time)}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 4 }}>
          Alerts since previous ({alertEvents.length})
        </div>
        {alertEvents.length === 0 ? (
          <div style={{ color: "var(--text-tertiary)", fontSize: 11 }}>None</div>
        ) : (
          <div className="mono" style={{ display: "grid", gap: 2, maxHeight: 120, overflow: "auto" }} data-testid="reports-alerts-since-previous">
            {alertEvents.slice(0, 40).map((a, i) => (
              <div key={`${a.event_at || i}-${a.rule_key}-${a.state}`}>
                <span className={a.severity === "CRITICAL" ? "cell-neg" : "cell-warn"}>{a.severity}</span>
                {" "}{a.state} · {a.rule_key} · {a.message} · {fmt.timeShort(a.event_at)}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <div style={{ color: "var(--text-tertiary)", fontSize: 10, marginBottom: 4 }}>Conclusion</div>
        <div style={{ color: "var(--text-secondary)", lineHeight: 1.45 }}>
          {report.conclusion || report.message || "—"}
        </div>
      </div>
    </div>
  );
}

export function ReportsView({ accounts = [], onAfterGenerate } = {}) {
  const [reports, setReports] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [accountFilter, setAccountFilter] = useState("ALL");
  const [expandedId, setExpandedId] = useState(null);

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

  const accountOptions = React.useMemo(() => {
    const fromReports = [...new Set(reports.map((r) => r.account_id).filter(Boolean))];
    const fromAccounts = (accounts || []).map((a) => a.id).filter(Boolean);
    return [...new Set([...fromAccounts, ...fromReports])].sort();
  }, [reports, accounts]);

  const showAccountFilter = accountOptions.length > 1;

  const filtered = React.useMemo(() => {
    if (accountFilter === "ALL") return reports;
    return reports.filter((r) => r.account_id === accountFilter);
  }, [reports, accountFilter]);

  const onGenerate = async () => {
    setBusy(true);
    try {
      await api.postAtlasReport({ source: "reports-tab" });
      await load();
      // Report generation also reconciles alerts — refresh the Alerts panel.
      if (typeof onAfterGenerate === "function") {
        await onAfterGenerate();
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel" data-testid="reports-panel">
      <div className="panel-header" style={{ gap: 10, flexWrap: "wrap" }}>
        <span className="panel-title">
          Sr. Atlas Reports · {filtered.length}
          {showAccountFilter && accountFilter !== "ALL" ? ` · ${accountFilter}` : ""}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto" }}>
          {showAccountFilter && (
            <select
              className="btn"
              value={accountFilter}
              onChange={(e) => setAccountFilter(e.target.value)}
              data-testid="reports-account-filter"
              style={{ padding: "4px 8px", fontSize: 11 }}
            >
              <option value="ALL">All accounts</option>
              {accountOptions.map((id) => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
          )}
          <button
            className="btn"
            onClick={onGenerate}
            disabled={busy}
            data-testid="reports-generate-button"
          >
            {busy ? "GENERATING…" : "GENERATE REPORT"}
          </button>
        </div>
      </div>
      <div className="scroll-area" style={{ overflow: "auto" }}>
        <table data-testid="reports-table">
          <thead>
            <tr>
              <th style={{ width: 28 }} />
              <th>Status</th>
              {showAccountFilter && <th>Account</th>}
              <th>Message</th>
              <th>Source</th>
              <th className="num">Created</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={showAccountFilter ? 6 : 5} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>
                  Loading reports…
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={showAccountFilter ? 6 : 5} style={{ textAlign: "center", padding: 20, color: "var(--text-tertiary)" }}>
                  No reports yet. Generate one above.
                </td>
              </tr>
            )}
            {filtered.map((r) => {
              const open = expandedId === r.id;
              return (
                <React.Fragment key={r.id}>
                  <tr
                    data-testid="reports-row"
                    data-report-id={r.id}
                    onClick={() => setExpandedId(open ? null : r.id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td className="mono" style={{ color: "var(--text-tertiary)", fontSize: 10 }}>
                      {open ? "▼" : "▶"}
                    </td>
                    <td>
                      <span className={`mono ${STATUS_CLASS[r.status] || ""}`} style={{ fontWeight: 600 }}>{r.status}</span>
                    </td>
                    {showAccountFilter && (
                      <td className="mono" style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{r.account_id}</td>
                    )}
                    <td style={{ color: "var(--text-secondary)" }}>{r.message}</td>
                    <td className="mono" style={{ color: "var(--text-tertiary)" }}>{r.source}</td>
                    <td className="num mono" style={{ color: "var(--text-tertiary)" }}>{fmt.relative(r.created_at)}</td>
                  </tr>
                  {open && (
                    <tr data-testid="reports-row-expanded">
                      <td colSpan={showAccountFilter ? 6 : 5} style={{ padding: 0 }}>
                        <ReportExpanded report={r} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
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

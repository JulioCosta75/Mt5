import React, { useCallback, useEffect, useState } from "react";
import { api, fmt } from "@/lib/api";

const STATUS_CLASS = {
  OK: "cell-pos",
  WARNING: "cell-warn",
  ALERT: "cell-neg",
};

function statusColor(status) {
  if (status === "OK") return "var(--sig-pos, #22C55E)";
  if (status === "WARNING") return "var(--sig-warn, #F59E0B)";
  if (status === "ALERT") return "var(--sig-neg, #EF4444)";
  return "var(--text-tertiary)";
}

function ServiceDot({ label, ok }) {
  const color = ok === true ? "#22C55E" : ok === false ? "#EF4444" : "#71717A";
  const text = ok === true ? "OK" : ok === false ? "DOWN" : "N/A";
  return (
    <div
      style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--bd-subtle)" }}
      data-testid={`supervision-service-${label.toLowerCase()}`}
    >
      <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{label}</span>
      <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }} className="mono">
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block" }} />
        {text}
      </span>
    </div>
  );
}

function Stat({ label, value, cls }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "6px 8px", background: "var(--bg-base)", border: "1px solid var(--bd-subtle)", borderRadius: 3 }}>
      <span style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
      <span className={`mono ${cls || ""}`} style={{ fontSize: 14, fontWeight: 500 }}>{value}</span>
    </div>
  );
}

export default function SupervisionPanel({ serverTime }) {
  const [snapshot, setSnapshot] = useState(null);
  const [reports, setReports] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const loadSnapshot = useCallback(async () => {
    try {
      const snap = await api.supervisionSnapshot();
      setSnapshot(snap);
      setError(null);
    } catch (e) {
      setError("Supervision feed unavailable");
    }
  }, []);

  const loadReports = useCallback(async () => {
    try {
      const data = await api.atlasReports({ limit: 8 });
      setReports(data.reports || []);
    } catch (e) {
      /* non-fatal */
    }
  }, []);

  useEffect(() => { loadSnapshot(); loadReports(); }, [loadSnapshot, loadReports]);
  // Re-sync the snapshot whenever the dashboard refreshes (server_time changes).
  useEffect(() => { if (serverTime) loadSnapshot(); }, [serverTime, loadSnapshot]);
  // Automatic supervision snapshot: poll the live snapshot every 30s.
  useEffect(() => {
    const id = setInterval(() => { loadSnapshot(); }, 30000);
    return () => clearInterval(id);
  }, [loadSnapshot]);

  const onGenerateReport = async () => {
    setBusy(true);
    try {
      await api.postAtlasReport({ source: "dashboard" });
      await loadReports();
      await loadSnapshot();
    } finally {
      setBusy(false);
    }
  };

  const status = snapshot?.status || "—";
  const svc = snapshot?.services || {};

  return (
    <div className="panel" data-testid="supervision-panel">
      <div className="panel-header">
        <span className="panel-title">Sr. Atlas Supervision</span>
        <span
          data-testid="supervision-status-badge"
          className="mono"
          style={{
            fontSize: 10.5,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 3,
            color: statusColor(status),
            border: `1px solid ${statusColor(status)}`,
            background: "transparent",
          }}
        >
          {status}
        </span>
      </div>

      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ fontSize: 11, color: "var(--text-secondary)" }} data-testid="supervision-message">
          {error ? error : (snapshot?.message || "Loading supervision snapshot…")}
        </div>

        {snapshot && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <Stat label="Total Equity" value={fmt.money(snapshot.kpis.total_equity)} />
              <Stat
                label="Daily P&L"
                value={fmt.money(snapshot.kpis.daily_pnl)}
                cls={snapshot.kpis.daily_pnl >= 0 ? "cell-pos" : "cell-neg"}
              />
              <Stat label="Accounts Live" value={`${snapshot.accounts.live}/${snapshot.accounts.total}`} />
              <Stat
                label="Active Alerts"
                value={snapshot.alerts.active}
                cls={snapshot.alerts.critical > 0 ? "cell-neg" : ""}
              />
            </div>

            <div>
              <div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
                Core Services
              </div>
              <ServiceDot label="Backend" ok={svc.backend_ok} />
              <ServiceDot label="Store" ok={svc.store_ok} />
              <ServiceDot label="Bridge" ok={svc.bridge_ok} />
              <ServiceDot label="Dashboard" ok={svc.dashboard_ok} />
            </div>
          </>
        )}

        <button
          className="btn"
          onClick={onGenerateReport}
          disabled={busy}
          data-testid="supervision-generate-report"
          style={{ width: "100%", justifyContent: "center" }}
        >
          {busy ? "GENERATING…" : "GENERATE SR. ATLAS REPORT"}
        </button>

        <div data-testid="supervision-reports">
          <div style={{ fontSize: 10, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            Recent Reports ({reports.length})
          </div>
          {reports.length === 0 ? (
            <div style={{ fontSize: 11, color: "var(--text-tertiary)" }}>No reports yet.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 220, overflowY: "auto" }}>
              {reports.map((r) => (
                <div
                  key={r.id}
                  data-testid="supervision-report-item"
                  style={{
                    display: "flex", flexDirection: "column", gap: 2,
                    padding: "6px 8px",
                    borderLeft: `2px solid ${statusColor(r.status)}`,
                    background: "var(--bg-base)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className={`mono ${STATUS_CLASS[r.status] || ""}`} style={{ fontSize: 10.5, fontWeight: 600 }}>
                      {r.status}
                    </span>
                    <span className="mono" style={{ fontSize: 10, color: "var(--text-tertiary)" }}>
                      {fmt.relative(r.created_at)}
                    </span>
                  </div>
                  <span style={{ fontSize: 10.5, color: "var(--text-secondary)", lineHeight: 1.35 }}>
                    {r.message}
                  </span>
                  <span className="mono" style={{ fontSize: 9.5, color: "var(--text-tertiary)" }}>
                    src: {r.source}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

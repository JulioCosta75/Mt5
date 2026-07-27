import React from "react";
import { fmt } from "@/lib/api";

export default function AlertsPanel({ alerts, onAck }) {
  const unack = alerts.filter(a => !a.acknowledged);
  return (
    <div className="panel" data-testid="alerts-panel">
      <div className="panel-header">
        <span className="panel-title">Alerts</span>
        <span style={{ fontSize: 11 }}>
          <span className="cell-neg mono">{alerts.filter(a => a.severity === "CRITICAL" && !a.acknowledged).length}</span>
          <span style={{ color: "var(--text-tertiary)", margin: "0 6px" }}>·</span>
          <span className="cell-warn mono">{alerts.filter(a => a.severity === "WARNING" && !a.acknowledged).length}</span>
          <span style={{ color: "var(--text-tertiary)", margin: "0 6px" }}>·</span>
          <span className="cell-info mono">{alerts.filter(a => a.severity === "INFO" && !a.acknowledged).length}</span>
        </span>
      </div>
      <div className="scroll-area divide-bd" style={{ maxHeight: 360, overflow: "auto" }}>
        {alerts.length === 0 && (
          <div style={{ padding: 20, color: "var(--text-tertiary)", fontSize: 12, textAlign: "center" }}>
            No alerts.
          </div>
        )}
        {alerts.map(a => (
          <div
            key={a.id}
            className={`alert-row ${a.severity} ${a.acknowledged ? "ack" : ""}`}
            data-testid={`alert-${a.id}`}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                <span style={{
                  fontSize: 9.5, fontWeight: 700, letterSpacing: "0.1em",
                  color: a.severity === "CRITICAL" ? "var(--sig-neg)" : a.severity === "WARNING" ? "var(--sig-warn)" : "var(--sig-info)",
                }}>{a.severity}</span>
                <span className="mono" style={{ fontSize: 10, color: "var(--text-tertiary)" }}>{a.account_id}</span>
                <span className="mono" style={{ fontSize: 10, color: "var(--text-tertiary)", marginLeft: "auto" }}>
                  {fmt.relative(a.timestamp)}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: 1.4 }}>
                {a.message}
              </div>
            </div>
            {!a.acknowledged && (
              <button
                className="btn"
                onClick={() => onAck(a.id)}
                data-testid={`alert-ack-${a.id}`}
                style={{ padding: "3px 8px", fontSize: 10 }}
              >
                ACK
              </button>
            )}
          </div>
        ))}
      </div>
      {unack.length > 0 && (
        <div style={{ padding: "8px 12px", borderTop: "1px solid var(--bd-default)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 10, color: "var(--text-tertiary)" }}>
            {unack.length} unacknowledged
          </span>
          <button
            className="btn"
            onClick={() => unack.forEach(a => onAck(a.id))}
            data-testid="alert-ack-all"
          >
            ACK ALL
          </button>
        </div>
      )}
    </div>
  );
}

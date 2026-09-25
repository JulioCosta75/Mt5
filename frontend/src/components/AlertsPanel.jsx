import React from "react";
import { fmt } from "@/lib/api";
import { SIMULATED_ALERTS_TITLE } from "@/lib/sampleMode";

export default function AlertsPanel({ alerts, onAck, isSample = false }) {
  const unack = alerts.filter(a => !a.acknowledged);
  return (
    <div className="panel" data-testid="alerts-panel">
      <div className="panel-header">
        <span className="panel-title" data-testid="alerts-panel-title">
          {isSample ? SIMULATED_ALERTS_TITLE : "Alerts"}
        </span>
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
              <div className="alert-meta">
                <span
                  className="alert-severity"
                  style={{
                    color: a.severity === "CRITICAL" ? "var(--sig-neg)" : a.severity === "WARNING" ? "var(--sig-warn)" : "var(--sig-info)",
                  }}
                >
                  {isSample ? `SIM · ${a.severity}` : a.severity}
                </span>
                <span className="mono alert-account">{a.account_id}</span>
                <span className="mono alert-time">
                  {fmt.relative(a.timestamp)}
                </span>
              </div>
              <div className="alert-body">
                {isSample ? `[SAMPLE] ${a.message}` : a.message}
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

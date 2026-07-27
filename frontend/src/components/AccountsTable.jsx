import React from "react";
import { fmt, pnlClass } from "@/lib/api";

function StatusBadge({ status }) {
  const cls = status === "LIVE" ? "live" : status === "PAUSED" ? "paused" : "error";
  const dot = status === "LIVE" ? "" : status === "PAUSED" ? "warn" : "neg";
  return (
    <span className={`badge ${cls}`}>
      <span className={`pulse-dot ${dot}`} />
      {status}
    </span>
  );
}

export default function AccountsTable({ accounts, selectedId, onSelect }) {
  return (
    <div className="panel" data-testid="accounts-panel">
      <div className="panel-header">
        <span className="panel-title">MT5 Accounts · {accounts.length}</span>
        <span className="kbd">ENTER to select</span>
      </div>
      <div className="scroll-area" style={{ maxHeight: 320, overflow: "auto" }}>
        <table data-testid="accounts-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Account</th>
              <th>Broker</th>
              <th>Strategy</th>
              <th className="num">Balance</th>
              <th className="num">Equity</th>
              <th className="num">Daily P&L</th>
              <th className="num">DD</th>
              <th className="num">Pos</th>
              <th className="num">Lev</th>
              <th className="num">Margin %</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map(acc => {
              const active = acc.id === selectedId;
              return (
                <tr
                  key={acc.id}
                  data-testid={`account-row-${acc.id}`}
                  onClick={() => onSelect(acc.id)}
                  style={{
                    cursor: "pointer",
                    background: active ? "rgba(244,244,245,0.04)" : undefined,
                    borderLeft: active ? "2px solid var(--text-primary)" : "2px solid transparent",
                  }}
                >
                  <td><StatusBadge status={acc.status} /></td>
                  <td className="mono" style={{ color: "var(--text-primary)" }}>{acc.login}</td>
                  <td style={{ color: "var(--text-secondary)" }}>{acc.broker}</td>
                  <td style={{ color: "var(--text-secondary)" }}>{acc.strategy}</td>
                  <td className="num">{fmt.money(acc.balance)}</td>
                  <td className="num" style={{ color: "var(--text-primary)" }}>{fmt.money(acc.equity)}</td>
                  <td className={`num ${pnlClass(acc.daily_pnl)}`}>{fmt.money(acc.daily_pnl)}</td>
                  <td className="num cell-neg">{fmt.pct(acc.current_drawdown)}</td>
                  <td className="num">{acc.open_positions}</td>
                  <td className="num" style={{ color: "var(--text-secondary)" }}>1:{acc.leverage}</td>
                  <td className="num" style={{ color: acc.margin_level < 200 ? "var(--sig-warn)" : "var(--text-primary)" }}>
                    {fmt.num(acc.margin_level, 1)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

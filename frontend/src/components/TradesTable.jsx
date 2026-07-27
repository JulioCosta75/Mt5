import React, { useMemo, useState } from "react";
import { fmt, pnlClass } from "@/lib/api";

function SortHeader({ sortKey, sortDir, onSort, k, num, children }) {
  return (
    <th
      className={num ? "num" : ""}
      onClick={() => onSort(k)}
      style={{ cursor: "pointer", userSelect: "none" }}
      data-testid={`trades-sort-${k}`}
    >
      {children} {sortKey === k && (sortDir === "asc" ? "↑" : "↓")}
    </th>
  );
}

export default function TradesTable({ trades, accountId }) {
  const [symbolFilter, setSymbolFilter] = useState("");
  const [sideFilter, setSideFilter] = useState("");
  const [sortKey, setSortKey] = useState("close_time");
  const [sortDir, setSortDir] = useState("desc");

  const symbols = useMemo(() => {
    const s = new Set(trades.map(t => t.symbol));
    return Array.from(s).sort();
  }, [trades]);

  const filtered = useMemo(() => {
    let out = trades;
    if (symbolFilter) out = out.filter(t => t.symbol === symbolFilter);
    if (sideFilter) out = out.filter(t => t.side === sideFilter);
    out = [...out].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      const cmp = av > bv ? 1 : av < bv ? -1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return out;
  }, [trades, symbolFilter, sideFilter, sortKey, sortDir]);

  const totalPnl = useMemo(() => filtered.reduce((s, t) => s + t.pnl, 0), [filtered]);
  const wins = filtered.filter(t => t.pnl > 0).length;
  const winRate = filtered.length ? (wins / filtered.length) * 100 : 0;

  const toggleSort = (k) => {
    if (sortKey === k) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir("desc"); }
  };

  return (
    <div className="panel" data-testid="trades-panel">
      <div className="panel-header" style={{ flexWrap: "wrap", gap: 12 }}>
        <span className="panel-title">Trade History · {accountId}</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            data-testid="trades-symbol-filter"
            style={{ width: 120 }}
          >
            <option value="">All Symbols</option>
            {symbols.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            value={sideFilter}
            onChange={(e) => setSideFilter(e.target.value)}
            data-testid="trades-side-filter"
            style={{ width: 100 }}
          >
            <option value="">All Sides</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
          <span style={{ display: "flex", gap: 12, fontSize: 11 }}>
            <span style={{ color: "var(--text-tertiary)" }}>NET</span>
            <span className={`mono ${pnlClass(totalPnl)}`} data-testid="trades-net-pnl">{fmt.money(totalPnl)}</span>
            <span style={{ color: "var(--text-tertiary)" }}>WIN%</span>
            <span className="mono" data-testid="trades-win-rate">{fmt.num(winRate, 1)}%</span>
            <span style={{ color: "var(--text-tertiary)" }}>N</span>
            <span className="mono">{filtered.length}</span>
          </span>
        </div>
      </div>
      <div className="scroll-area" style={{ maxHeight: 340, overflow: "auto" }}>
        <table>
          <thead>
            <tr>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="close_time">Close Time</SortHeader>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="symbol">Symbol</SortHeader>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="side">Side</SortHeader>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="lots" num>Lots</SortHeader>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="open_price" num>Open</SortHeader>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="close_price" num>Close</SortHeader>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="duration_min" num>Dur (m)</SortHeader>
              <SortHeader sortKey={sortKey} sortDir={sortDir} onSort={toggleSort} k="pnl" num>P&L</SortHeader>
              <th>Strategy</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 80).map(t => (
              <tr key={t.id} data-testid={`trade-row-${t.id}`}>
                <td className="mono" style={{ color: "var(--text-secondary)" }}>{fmt.time(t.close_time)}</td>
                <td className="mono">{t.symbol}</td>
                <td>
                  <span style={{
                    color: t.side === "BUY" ? "var(--sig-pos)" : "var(--sig-neg)",
                    fontWeight: 600, fontSize: 10, letterSpacing: "0.08em"
                  }}>{t.side}</span>
                </td>
                <td className="num">{fmt.num(t.lots, 2)}</td>
                <td className="num" style={{ color: "var(--text-secondary)" }}>{fmt.num(t.open_price, 4)}</td>
                <td className="num" style={{ color: "var(--text-secondary)" }}>{fmt.num(t.close_price, 4)}</td>
                <td className="num" style={{ color: "var(--text-tertiary)" }}>{t.duration_min}</td>
                <td className={`num ${pnlClass(t.pnl)}`} style={{ fontWeight: 600 }}>{fmt.money(t.pnl)}</td>
                <td style={{ color: "var(--text-secondary)" }}>{t.strategy}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

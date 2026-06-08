import React, { useEffect, useState, useCallback, useRef, useReducer } from "react";
import { api, fmt } from "@/lib/api";
import KpiTicker from "@/components/KpiTicker";
import AccountsTable from "@/components/AccountsTable";
import { EquityChart, DrawdownChart } from "@/components/Charts";
import TradesTable from "@/components/TradesTable";
import AlertsPanel from "@/components/AlertsPanel";
import RiskPanel from "@/components/RiskPanel";

function Header({ refreshing, onRefresh, sessionId }) {
  return (
    <header
      data-testid="app-header"
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 20px",
        background: "var(--bg-base)",
        borderBottom: "1px solid var(--bd-default)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 22, height: 22,
            background: "linear-gradient(135deg, #22C55E, #16A34A)",
            display: "grid", placeItems: "center",
            fontFamily: "Geist Mono", fontSize: 11, fontWeight: 700, color: "#0A0A0A",
          }}>
            Q
          </div>
          <span style={{ fontSize: 14, letterSpacing: "-0.01em", fontWeight: 600 }}>
            QUANT<span style={{ color: "var(--text-tertiary)" }}>.</span>SUPERVISE
          </span>
          <span className="kbd" style={{ marginLeft: 8 }}>MT5</span>
        </div>
        <nav style={{ display: "flex", gap: 4, marginLeft: 16 }}>
          {["Overview", "Strategies", "Risk", "Reports", "Audit"].map((n, i) => (
            <button
              key={n}
              className={`btn ${i === 0 ? "active" : ""}`}
              data-testid={`nav-${n.toLowerCase()}`}
              style={{ border: "none", padding: "4px 10px" }}
            >
              {n}
            </button>
          ))}
        </nav>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          className="btn success"
          onClick={onRefresh}
          data-testid="refresh-button"
          disabled={refreshing}
        >
          <span className={`pulse-dot ${refreshing ? "warn" : ""}`} />
          {refreshing ? "REFRESHING…" : "REFRESH FEED"}
        </button>
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }} className="mono">
          v0.1.0 · session-{sessionId}
        </span>
      </div>
    </header>
  );
}

const initialState = {
  kpis: null,
  accounts: [],
  selectedId: null,
  equity: [],
  drawdown: { series: [], max_drawdown: 0, current_drawdown: 0 },
  trades: [],
  alerts: [],
  refreshing: false,
  loading: true,
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_GLOBALS":
      return {
        ...state,
        kpis: action.kpis,
        accounts: action.accounts,
        alerts: action.alerts,
        selectedId: state.selectedId || (action.accounts[0]?.id ?? null),
      };
    case "SET_DETAIL":
      return { ...state, equity: action.equity, drawdown: action.drawdown, trades: action.trades };
    case "SELECT":
      return { ...state, selectedId: action.id };
    case "ACK_ALERT":
      return { ...state, alerts: state.alerts.map(a => a.id === action.id ? { ...a, acknowledged: true } : a) };
    case "REFRESHING":
      return { ...state, refreshing: action.value };
    case "LOADING":
      return { ...state, loading: action.value };
    default:
      return state;
  }
}

export default function Dashboard() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { kpis, accounts, selectedId, equity, drawdown, trades, alerts, refreshing, loading } = state;
  const [sessionId] = useState(() => Math.floor(Math.random() * 9000 + 1000));
  const selectedIdRef = useRef(null);
  useEffect(() => { selectedIdRef.current = selectedId; }, [selectedId]);

  const loadGlobals = useCallback(async () => {
    const [k, a, al] = await Promise.all([api.kpis(), api.accounts(), api.alerts()]);
    dispatch({ type: "SET_GLOBALS", kpis: k, accounts: a, alerts: al.alerts || [] });
  }, []);

  const loadAccountDetail = useCallback(async (id) => {
    if (!id) return;
    const [eq, dd, tr] = await Promise.all([
      api.equity(id, 220),
      api.drawdown(id, 220),
      api.trades(id, { limit: 100 }),
    ]);
    dispatch({ type: "SET_DETAIL", equity: eq.series || [], drawdown: dd, trades: tr.trades || [] });
  }, []);

  // initial load
  useEffect(() => {
    let cancelled = false;
    (async () => {
      await loadGlobals();
      if (!cancelled) dispatch({ type: "LOADING", value: false });
    })();
    return () => { cancelled = true; };
  }, [loadGlobals]);

  useEffect(() => {
    if (selectedId) loadAccountDetail(selectedId);
  }, [selectedId, loadAccountDetail]);

  const onRefresh = async () => {
    dispatch({ type: "REFRESHING", value: true });
    try {
      await api.tick();
      await loadGlobals();
      const sid = selectedIdRef.current;
      if (sid) await loadAccountDetail(sid);
    } finally {
      dispatch({ type: "REFRESHING", value: false });
    }
  };

  const onAckAlert = async (id) => {
    await api.ackAlert(id, true);
    dispatch({ type: "ACK_ALERT", id });
  };

  const selectedAccount = accounts.find(a => a.id === selectedId);

  return (
    <div className="App" data-testid="dashboard">
      <Header refreshing={refreshing} onRefresh={onRefresh} sessionId={sessionId} />
      <KpiTicker kpis={kpis} />

      {loading ? (
        <div style={{ padding: 60, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
          Connecting to supervision feed…
        </div>
      ) : (
        <main
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr) 360px",
            gap: 14,
            padding: 14,
          }}
        >
          {/* LEFT COLUMN */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
            <AccountsTable accounts={accounts} selectedId={selectedId} onSelect={(id) => dispatch({ type: "SELECT", id })} />
            {selectedAccount && (
              <>
                <RiskPanel
                  key={selectedAccount.id}
                  account={selectedAccount}
                  onUpdate={() => { loadGlobals(); loadAccountDetail(selectedId); }}
                />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                  <EquityChart data={equity} />
                  <DrawdownChart
                    data={drawdown.series}
                    maxDD={drawdown.max_drawdown}
                    currentDD={drawdown.current_drawdown}
                  />
                </div>
                <TradesTable trades={trades} accountId={selectedId} />
              </>
            )}
          </div>

          {/* RIGHT COLUMN */}
          <aside style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
            <AlertsPanel alerts={alerts} onAck={onAckAlert} />
            <div className="panel" data-testid="system-panel">
              <div className="panel-header">
                <span className="panel-title">System</span>
                <span className="pulse-dot" />
              </div>
              <div style={{ padding: 14, fontSize: 11, color: "var(--text-secondary)" }}>
                <Row label="API Latency" value="42 ms" />
                <Row label="MT5 Bridge" value={<span className="cell-pos">CONNECTED</span>} />
                <Row label="Risk Engine" value={<span className="cell-pos">ACTIVE</span>} />
                <Row label="Telegram Notif" value={<span className="cell-pos">ENABLED</span>} />
                <Row label="Last Heartbeat" value={kpis ? fmt.timeShort(kpis.server_time) : "—"} />
                <Row label="Strategies Loaded" value={<span className="mono">6</span>} />
              </div>
            </div>
          </aside>
        </main>
      )}
      <footer
        data-testid="footer"
        style={{
          padding: "10px 20px",
          borderTop: "1px solid var(--bd-default)",
          fontSize: 10.5,
          color: "var(--text-tertiary)",
          display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap",
        }}
      >
        <span>QUANT.SUPERVISE — MT5 Quantitative Supervision Platform. Mock data for MVP preview.</span>
        <span className="mono">© 2026 · Built on Emergent</span>
      </footer>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--bd-subtle)" }}>
      <span style={{ color: "var(--text-tertiary)" }}>{label}</span>
      <span className="mono">{value}</span>
    </div>
  );
}

import React, { useEffect, useState, useCallback, useRef, useReducer } from "react";
import { Link } from "react-router-dom";
import { api, fmt } from "@/lib/api";
import { srAtlasRound } from "@/assets/branding";
import { isSamplePresentation } from "@/lib/sampleMode";
import KpiTicker from "@/components/KpiTicker";
import OverviewHero from "@/components/OverviewHero";
import AccountsTable from "@/components/AccountsTable";
import { EquityChart, DrawdownChart } from "@/components/Charts";
import TradesTable from "@/components/TradesTable";
import AlertsPanel from "@/components/AlertsPanel";
import RiskPanel from "@/components/RiskPanel";
import SupervisionPanel from "@/components/SupervisionPanel";
import { StrategiesView, RiskView, ReportsView, AuditView } from "@/components/TabViews";
import RevolutionView from "@/pages/Revolution";

const TABS = ["Overview", "Strategies", "Risk", "Reports", "Audit"];

function Header({ refreshing, onRefresh, sessionId, activeTab, onTabChange, buildInfo, showRevolution }) {
  const versionLabel = buildInfo && buildInfo.version ? `v${buildInfo.version}` : "v…";
  const buildLabel = buildInfo && buildInfo.build && buildInfo.build !== "release"
    ? ` · ${buildInfo.build}` : "";
  const buildTitle = buildInfo
    ? `Running build ${buildInfo.version}${buildInfo.build ? " (" + buildInfo.build + ")" : ""}${buildInfo.built_at ? " · built " + buildInfo.built_at : ""}${buildInfo.channel ? " · " + buildInfo.channel : ""}`
    : "Fetching running build…";
  return (
    <header
      data-testid="app-header"
      className="app-header"
    >
      <div className="app-header-left">
        <div className="app-header-brand">
          <img
            src={srAtlasRound}
            alt="Sr. Atlas"
            height={30}
            width={30}
            style={{ borderRadius: 6, objectFit: "cover", background: "#000" }}
            data-testid="header-sr-atlas-logo"
          />
          <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "-0.01em" }}>
            Sr. Atlas
          </span>
          <span className="kbd" style={{ marginLeft: 4 }}>MT5</span>
        </div>
        <nav className="app-nav" data-testid="app-nav">
          {TABS.map((n) => (
            <button
              key={n}
              type="button"
              className={`btn ${activeTab === n ? "active" : ""}`}
              data-testid={`nav-${n.toLowerCase()}`}
              aria-current={activeTab === n ? "page" : undefined}
              onClick={() => onTabChange(n)}
              style={{ border: "none", padding: "4px 10px" }}
            >
              {n}
            </button>
          ))}
          {showRevolution ? (
            <button
              type="button"
              className={`btn nav-revolution ${activeTab === "Revolution" ? "active" : ""}`}
              data-testid="nav-revolution"
              aria-current={activeTab === "Revolution" ? "page" : undefined}
              onClick={() => onTabChange("Revolution")}
              style={{ border: "none", padding: "4px 10px" }}
            >
              <span className="nav-revolution-mark" aria-hidden="true">◆</span>
              Revolution
            </button>
          ) : null}
          <details className="app-nav-more" data-testid="nav-more">
            <summary className="btn" data-testid="nav-more-toggle" style={{ border: "none", padding: "4px 10px" }}>
              More
            </summary>
            <div className="app-nav-more-panel">
              <Link to="/about" className="btn" data-testid="nav-about">About</Link>
              <Link to="/docs" className="btn" data-testid="nav-docs">Docs</Link>
              <Link to="/settings" className="btn" data-testid="nav-settings">Settings</Link>
            </div>
          </details>
        </nav>
      </div>
      <div className="app-header-right">
        <button
          className="btn success"
          onClick={onRefresh}
          data-testid="refresh-button"
          disabled={refreshing}
        >
          <span className={`pulse-dot ${refreshing ? "warn" : ""}`} />
          {refreshing ? "REFRESHING…" : "REFRESH FEED"}
        </button>
        <span
          style={{ fontSize: 11, color: "var(--text-tertiary)" }}
          className="mono"
          data-testid="app-version"
          title={buildTitle}
        >
          {versionLabel}{buildLabel} · session-{sessionId}
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
  const [activeTab, setActiveTab] = useState("Overview");
  const [buildInfo, setBuildInfo] = useState(null);
  const [mt5Status, setMt5Status] = useState(null);
  const [knowledgeEnabled, setKnowledgeEnabled] = useState(false);
  const [healthMode, setHealthMode] = useState(null);
  const selectedIdRef = useRef(null);
  useEffect(() => { selectedIdRef.current = selectedId; }, [selectedId]);

  const isSample = isSamplePresentation(mt5Status, healthMode);
  const loadGlobals = useCallback(async () => {
    const settled = await Promise.allSettled([api.kpis(), api.accounts(), api.alerts()]);
    const kpis = settled[0].status === "fulfilled" ? settled[0].value : null;
    const accountsRaw = settled[1].status === "fulfilled" ? settled[1].value : [];
    const accounts = Array.isArray(accountsRaw) ? accountsRaw : [];
    const alertsPayload = settled[2].status === "fulfilled" ? settled[2].value : null;
    const alerts = Array.isArray(alertsPayload?.alerts) ? alertsPayload.alerts : [];
    dispatch({ type: "SET_GLOBALS", kpis, accounts, alerts });
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

  // initial load — always leave the connecting state, even if one feed fails
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadGlobals();
      } finally {
        if (!cancelled) dispatch({ type: "LOADING", value: false });
      }
    })();
    return () => { cancelled = true; };
  }, [loadGlobals]);

  // running build/version + connection mode (verifies which deployment is live)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const v = await api.systemVersion();
        if (!cancelled) setBuildInfo(v);
      } catch (e) {
        if (!cancelled) setBuildInfo(null);
      }
      try {
        const c = await api.getMt5Config();
        if (!cancelled) setMt5Status(c.status || null);
      } catch (e) {
        if (!cancelled) setMt5Status(null);
      }
      try {
        const h = await api.systemHealth();
        if (!cancelled) setHealthMode(h.mode || null);
      } catch (e) {
        if (!cancelled) setHealthMode(null);
      }
      try {
        const k = await api.knowledgeStatus();
        if (!cancelled) setKnowledgeEnabled(!!(k && k.enabled));
      } catch (e) {
        if (!cancelled) setKnowledgeEnabled(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (selectedId) loadAccountDetail(selectedId);
  }, [selectedId, loadAccountDetail]);

  const onRefresh = async () => {
    dispatch({ type: "REFRESHING", value: true });
    try {
      // /sim/tick exists only in mock mode. Never let a 404 abort the real
      // feed refresh — otherwise Alerts/KPIs stay stale while relative times
      // still update from the refreshing state re-render.
      try {
        await api.tick();
      } catch (_) {
        /* live MT5: ignore */
      }
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
      <Header refreshing={refreshing} onRefresh={onRefresh} sessionId={sessionId} activeTab={activeTab} onTabChange={setActiveTab} buildInfo={buildInfo} showRevolution={knowledgeEnabled} />
      {isSample && (
        <div
          data-testid="config-mode-banner"
          className="config-mode-banner"
        >
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--sig-warn)", display: "inline-block", flexShrink: 0 }} />
          <span>
            <b>Configuration Mode — Simulated Sample Data</b>
            {" "}Atlas is not connected to MetaTrader 5.
            All trading accounts, trades, alerts, charts, risk values, and strategy activity shown here are simulated sample data — not verified live activity.
          </span>
          <Link
            to="/settings"
            data-testid="config-mode-cta"
            className="btn"
            style={{ marginLeft: "auto", textDecoration: "none", padding: "3px 10px", flexShrink: 0 }}
          >
            Open Settings →
          </Link>
        </div>
      )}
      {activeTab === "Overview" ? (
        <>
          <OverviewHero kpis={kpis} mt5Status={mt5Status} isSample={isSample} />
          <KpiTicker kpis={kpis} className="ticker-row-compact" />
        </>
      ) : (
        <KpiTicker kpis={kpis} />
      )}

      {loading ? (
        <div style={{ padding: 60, textAlign: "center", color: "var(--text-tertiary)", fontSize: 12 }}>
          Connecting to supervision feed…
        </div>
      ) : activeTab === "Overview" ? (
        <main
          className="overview-layout"
          data-testid="overview-layout"
        >
          {/* LEFT COLUMN */}
          <div style={{ display: "flex", flexDirection: "column", gap: 18, minWidth: 0 }}>
            <AccountsTable accounts={accounts} selectedId={selectedId} onSelect={(id) => dispatch({ type: "SELECT", id })} isSample={isSample} />
            {selectedAccount && (
              <>
                <RiskPanel
                  key={selectedAccount.id}
                  account={selectedAccount}
                  onUpdate={() => { loadGlobals(); loadAccountDetail(selectedId); }}
                  isSample={isSample}
                  showHeroBars
                />
                <div className="overview-charts" data-testid="overview-charts">
                  <EquityChart data={equity} isSample={isSample} />
                  <DrawdownChart
                    data={drawdown.series}
                    maxDD={drawdown.max_drawdown}
                    currentDD={drawdown.current_drawdown}
                    isSample={isSample}
                  />
                </div>
                <TradesTable trades={trades} accountId={selectedId} isSample={isSample} />
              </>
            )}
          </div>

          {/* RIGHT COLUMN */}
          <aside style={{ display: "flex", flexDirection: "column", gap: 18, minWidth: 0 }}>
            <SupervisionPanel
              serverTime={kpis?.server_time}
              onAfterGenerate={loadGlobals}
            />
            <AlertsPanel alerts={alerts} onAck={onAckAlert} isSample={isSample} />
            <div className="panel" data-testid="system-panel">
              <div className="panel-header">
                <span className="panel-title">System</span>
                <span className="pulse-dot" />
              </div>
              <div style={{ padding: 22, fontSize: 13, color: "var(--text-secondary)" }}>
                {isSample ? (
                  <>
                    <Row label="API Latency" value={<span className="cell-warn" data-testid="system-api-latency">SAMPLE · —</span>} />
                    <Row label="MT5 Bridge" value={<span className="cell-warn" data-testid="system-mt5-bridge">NOT CONNECTED</span>} />
                    <Row label="Risk Engine" value={<span className="cell-warn" data-testid="system-risk-engine">SIMULATION</span>} />
                    <Row label="Telegram Notif" value={<span className="cell-warn" data-testid="system-telegram">NOT CONFIGURED</span>} />
                    <Row label="Last Heartbeat" value={<span data-testid="system-heartbeat">{kpis ? `SAMPLE · ${fmt.timeShort(kpis.server_time)}` : "SAMPLE · —"}</span>} />
                    <Row label="Strategies Loaded" value={<span className="mono cell-warn" data-testid="system-strategies">SAMPLE · —</span>} />
                    <Row label="Backend" value={<span className="cell-pos" data-testid="system-backend">OK</span>} />
                    <Row label="Store" value={<span className="cell-pos" data-testid="system-store">OK</span>} />
                    <Row label="Dashboard" value={<span className="cell-pos" data-testid="system-dashboard">OK</span>} />
                  </>
                ) : (
                  <>
                    <Row label="API Latency" value={<span className="cell-warn" data-testid="system-api-latency">Unavailable<span className="kbd" style={{ marginLeft: 6 }}>C7</span></span>} />
                    <Row label="MT5 Bridge" value={<span className="cell-pos">CONNECTED</span>} />
                    <Row label="Risk Engine" value={<span className="cell-pos">ACTIVE</span>} />
                    <Row label="Telegram Notif" value={<span className="cell-pos">ENABLED</span>} />
                    <Row label="Last Heartbeat" value={kpis ? fmt.timeShort(kpis.server_time) : "—"} />
                    <Row label="Strategies Loaded" value={<span className="mono cell-warn" data-testid="system-strategies">Unavailable</span>} />
                  </>
                )}
              </div>
            </div>
          </aside>
        </main>
      ) : (
        <main style={{ padding: 14 }} data-testid={`tab-content-${activeTab.toLowerCase()}`}>
          {activeTab === "Strategies" && <StrategiesView accounts={accounts} isSample={isSample} />}
          {activeTab === "Risk" && (
            <RiskView
              accounts={accounts}
              selectedId={selectedId}
              onSelect={(id) => dispatch({ type: "SELECT", id })}
              selectedAccount={selectedAccount}
              onUpdate={() => { loadGlobals(); loadAccountDetail(selectedId); }}
              isSample={isSample}
            />
          )}
          {activeTab === "Reports" && (
            <ReportsView
              accounts={accounts}
              onAfterGenerate={loadGlobals}
            />
          )}
          {activeTab === "Audit" && <AuditView alerts={alerts} onAck={onAckAlert} isSample={isSample} />}
          {activeTab === "Revolution" && knowledgeEnabled && (
            <RevolutionView
              accounts={accounts}
              selectedId={selectedId}
              onSelect={(id) => dispatch({ type: "SELECT", id })}
            />
          )}
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
        <span>Forge Factory Lab · Sr. Atlas — MT5 Quantitative Supervision. Phase 2.</span>
        <span className="mono">© 2026 Forge Factory Lab · Sr. Atlas</span>
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

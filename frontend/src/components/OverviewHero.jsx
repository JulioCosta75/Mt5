import React from "react";
import { Cable, Shield, Users } from "lucide-react";

export function healthFromKpis(kpis) {
  const critical = Number(kpis?.critical_alerts || 0);
  const active = Number(kpis?.active_alerts || 0);
  if (critical > 0) {
    return { word: "ALERT", signal: "cell-neg", fill: 30, detail: `${critical} critical · ${active} active` };
  }
  if (active > 0) {
    return { word: "WARNING", signal: "cell-warn", fill: 60, detail: `${active} active alerts` };
  }
  return { word: "OK", signal: "cell-pos", fill: 100, detail: "No active critical alerts" };
}

export function mt5FromStatus(mt5Status, isSample) {
  const state = mt5Status?.state;
  if (isSample || !state || state === "unconfigured") {
    return { word: "OFFLINE", signal: "cell-warn", fill: 8, detail: "No MetaTrader 5 account connected yet." };
  }
  if (state === "pending_restart") {
    return { word: "PENDING", signal: "cell-warn", fill: 50, detail: "Settings saved. Atlas is restarting." };
  }
  if (state === "connected") {
    return { word: "CONNECTED", signal: "cell-pos", fill: 100, detail: "Atlas is connected to your MetaTrader 5 account." };
  }
  return { word: String(state).toUpperCase(), signal: "cell-warn", fill: 20, detail: "MT5 connection status from the existing config feed." };
}

function HeroCard({ testId, icon, label, word, wordClass, detail, fill }) {
  return (
    <article className="hero-card" data-testid={testId}>
      <div className="hero-card-icon" aria-hidden="true">{icon}</div>
      <div className="hero-card-label">{label}</div>
      <div className={`hero-card-value ${wordClass}`}>{word}</div>
      <p className="hero-card-detail">{detail}</p>
      <div className="hero-bar-track" aria-hidden="true">
        <div className="hero-bar-fill" style={{ width: `${fill}%` }} />
      </div>
    </article>
  );
}

export default function OverviewHero({ kpis, mt5Status, isSample = false }) {
  const health = healthFromKpis(kpis);
  const mt5 = mt5FromStatus(mt5Status, isSample);
  const live = kpis?.accounts_live;
  const total = kpis?.accounts_total;
  const liveKnown = live !== null && live !== undefined && total;
  const accountsFill = liveKnown && Number(total) > 0
    ? Math.min(100, Math.max(0, (Number(live) / Number(total)) * 100))
    : 0;
  const accountsWord = liveKnown ? String(live) : "—";
  const accountsDetail = liveKnown
    ? `${live} of ${total} live`
    : "Waiting for accounts feed";

  return (
    <section className="hero-strip" data-testid="overview-hero">
      <HeroCard
        testId="overview-hero-health"
        icon={<Shield size={16} strokeWidth={1.75} />}
        label="Account Health"
        word={health.word}
        wordClass={health.signal}
        detail={health.detail}
        fill={health.fill}
      />
      <HeroCard
        testId="overview-hero-mt5"
        icon={<Cable size={16} strokeWidth={1.75} />}
        label="MT5 Connection"
        word={mt5.word}
        wordClass={mt5.signal}
        detail={mt5.detail}
        fill={mt5.fill}
      />
      <HeroCard
        testId="overview-hero-accounts"
        icon={<Users size={16} strokeWidth={1.75} />}
        label="Active Accounts"
        word={accountsWord}
        wordClass="mono"
        detail={accountsDetail}
        fill={accountsFill}
      />
    </section>
  );
}

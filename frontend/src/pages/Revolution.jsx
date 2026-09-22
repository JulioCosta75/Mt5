import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Gate 5 Stage 2 — Atlas Revolution (read-only Knowledge view).
 * No action buttons. Level A facts + Level B context match only.
 */
export default function RevolutionView({ accounts, selectedId, onSelect }) {
  const accountId = selectedId || "";
  const [insights, setInsights] = useState([]);
  const [graveyard, setGraveyard] = useState([]);
  const [counts, setCounts] = useState({ validated: 0, active_now: 0, graveyard: 0 });
  const [eaA, setEaA] = useState("");
  const [eaB, setEaB] = useState("");
  const [correlation, setCorrelation] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!accountId) {
      setInsights([]);
      setGraveyard([]);
      setCounts({ validated: 0, active_now: 0, graveyard: 0 });
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const [ins, gra] = await Promise.all([
          api.knowledgeInsights(accountId),
          api.knowledgeGraveyard(accountId),
        ]);
        if (cancelled) return;
        const list = ins.insights || [];
        const entries = gra.entries || [];
        setInsights(list);
        setGraveyard(entries);
        setCounts({
          validated: (ins.counts && ins.counts.validated) || list.length,
          active_now: (ins.counts && ins.counts.active_now) || 0,
          graveyard: gra.count != null ? gra.count : entries.length,
        });
      } catch {
        if (cancelled) return;
        setInsights([]);
        setGraveyard([]);
        setCounts({ validated: 0, active_now: 0, graveyard: 0 });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [accountId]);

  useEffect(() => {
    if (!accountId || !eaA.trim() || !eaB.trim()) {
      setCorrelation(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await api.knowledgeCorrelation(accountId, eaA.trim(), eaB.trim());
        if (!cancelled) setCorrelation(data);
      } catch {
        if (!cancelled) {
          setCorrelation({
            insufficient: true,
            coincidence: null,
            reason: "dados insuficientes",
            status: "insufficient_data",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [accountId, eaA, eaB]);

  const active = insights.filter((row) => row.is_context_active_now);
  const inputStyle = {
    background: "#140A1F",
    border: "1px solid rgba(168,85,247,0.35)",
    color: "#F5F3FF",
    padding: "6px 10px",
    fontSize: 12,
    minWidth: 160,
  };

  return (
    <div className="revolution-page" data-testid="revolution-page">
      <div className="revolution-strip" data-testid="revolution-summary">
        <Metric testId="revolution-metric-validated" label="Validated facts" value={counts.validated} />
        <Metric testId="revolution-metric-active" label="Active patterns now" value={counts.active_now} />
        <Metric testId="revolution-metric-graveyard" label="Graveyard" value={counts.graveyard} />
      </div>

      <label className="revolution-account" data-testid="revolution-account-wrap">
        <span>Account</span>
        <select
          data-testid="revolution-account-select"
          value={accountId}
          onChange={(e) => onSelect && onSelect(e.target.value || null)}
          style={inputStyle}
        >
          <option value="">Select account</option>
          {(accounts || []).map((acc) => (
            <option key={acc.id} value={acc.id}>
              {acc.id}{acc.login ? ` · ${acc.login}` : ""}
            </option>
          ))}
        </select>
      </label>

      {loading ? (
        <p className="revolution-empty" data-testid="revolution-loading">Reading knowledge…</p>
      ) : null}

      <section data-testid="revolution-insights">
        <h2>Validated facts</h2>
        {insights.length === 0 ? (
          <p className="revolution-empty" data-testid="revolution-empty-insights">
            No validated knowledge for this account.
          </p>
        ) : (
          insights.map((row) => (
            <article
              key={row.knowledge_record_id}
              className="revolution-card"
              data-testid="revolution-insight-card"
            >
              <p>{row.formatted || row.statement}</p>
              {row.is_stale ? (
                <span className="revolution-stale" data-testid="revolution-stale-flag">stale</span>
              ) : null}
            </article>
          ))
        )}
      </section>

      <section data-testid="revolution-active">
        <h2>Active pattern matches</h2>
        {active.length === 0 ? (
          <p className="revolution-empty" data-testid="revolution-empty-active">
            No pattern is active in the current context.
          </p>
        ) : (
          active.map((row) => (
            <article key={`active-${row.knowledge_record_id}`} className="revolution-card">
              <p>{row.statement}</p>
            </article>
          ))
        )}
      </section>

      <section data-testid="revolution-correlation">
        <h2>Coincidence of negative days</h2>
        <div className="revolution-pair">
          <label>
            EA A
            <input
              data-testid="revolution-ea-a"
              value={eaA}
              onChange={(e) => setEaA(e.target.value)}
              placeholder="ea_key"
              style={inputStyle}
            />
          </label>
          <label>
            EA B
            <input
              data-testid="revolution-ea-b"
              value={eaB}
              onChange={(e) => setEaB(e.target.value)}
              placeholder="ea_key"
              style={inputStyle}
            />
          </label>
        </div>
        {!eaA.trim() || !eaB.trim() ? (
          <p className="revolution-empty" data-testid="revolution-correlation-need-pair">
            dados insuficientes — both EA keys are required.
          </p>
        ) : correlation && correlation.insufficient ? (
          <p className="revolution-empty" data-testid="revolution-correlation-insufficient">
            {correlation.reason || "dados insuficientes"}
          </p>
        ) : correlation && correlation.coincidence == null ? (
          <p className="revolution-empty">dados insuficientes</p>
        ) : correlation ? (
          <article className="revolution-card" data-testid="revolution-correlation-card">
            <p>
              {correlation.ea_a_key} and {correlation.ea_b_key}
              {correlation.is_paired ? " are paired" : " are not paired"}
              {correlation.coincidence != null
                ? ` (coincidence ${correlation.coincidence}).`
                : "."}
            </p>
            <p className="revolution-reason">{correlation.reason}</p>
          </article>
        ) : (
          <p className="revolution-empty">dados insuficientes</p>
        )}
      </section>

      <section data-testid="revolution-graveyard">
        <h2>Graveyard</h2>
        {graveyard.length === 0 ? (
          <p className="revolution-empty" data-testid="revolution-empty-graveyard">
            No invalidated conclusions.
          </p>
        ) : (
          graveyard.map((row) => (
            <article
              key={row.knowledge_record_id}
              className="revolution-card revolution-grave"
              data-testid="revolution-grave-card"
            >
              <p className="revolution-strike">{row.statement}</p>
              <p className="revolution-reason">
                {row.decided_by || "unknown"} · {row.justification || "no justification recorded"}
              </p>
            </article>
          ))
        )}
      </section>
    </div>
  );
}

function Metric({ testId, label, value }) {
  return (
    <div className="revolution-metric" data-testid={testId}>
      <span className="revolution-metric-value">{value}</span>
      <span className="revolution-metric-label">{label}</span>
    </div>
  );
}

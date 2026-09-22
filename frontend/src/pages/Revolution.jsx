import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Gate 5 Stage 2b — Atlas Revolution (read-only EA dossiers).
 * No action buttons. Level A facts + Level B context match only.
 */

const PIPELINE = [
  { key: "raw_observation", label: "Raw" },
  { key: "repeated_pattern", label: "Pattern" },
  { key: "hypothesis", label: "Hypothesis" },
  { key: "evidence_under_review", label: "Review" },
  { key: "provisionally_validated_conclusion", label: "Provisional" },
  { key: "fully_validated_conclusion", label: "Full" },
  { key: "knowledge", label: "Knowledge" },
];

const PIPELINE_INDEX = PIPELINE.reduce((acc, step, i) => {
  acc[step.key] = i;
  return acc;
}, {});

const STATE_LABEL = {
  raw_observation: "Raw",
  repeated_pattern: "Pattern",
  hypothesis: "Hypothesis",
  evidence_under_review: "Review",
  provisionally_validated_conclusion: "Provisional",
  fully_validated_conclusion: "Full",
  knowledge_candidate: "Candidate",
  knowledge: "Knowledge",
  invalidated_conclusion: "Invalidated",
};

const STATE_TONE = {
  raw_observation: "neutral",
  repeated_pattern: "neutral",
  hypothesis: "blue",
  evidence_under_review: "amber",
  provisionally_validated_conclusion: "amber",
  fully_validated_conclusion: "gold",
  knowledge_candidate: "gold",
  knowledge: "gold",
  invalidated_conclusion: "muted",
};

const EMPTY_COUNTS = {
  under_review: 0,
  candidates: 0,
  validated: 0,
  graveyard: 0,
};

const FACT_STATES = new Set([
  "provisionally_validated_conclusion",
  "fully_validated_conclusion",
  "knowledge_candidate",
  "knowledge",
]);

const PATTERN_STATES = new Set([
  "raw_observation",
  "repeated_pattern",
  "hypothesis",
  "evidence_under_review",
]);

function pipelineIndex(state) {
  if (state === "knowledge_candidate") return PIPELINE_INDEX.knowledge;
  if (state in PIPELINE_INDEX) return PIPELINE_INDEX[state];
  return -1;
}

function furthestIndex(records) {
  let max = -1;
  (records || []).forEach((row) => {
    const i = pipelineIndex(row.validation_state);
    if (i > max) max = i;
  });
  return max;
}

export default function RevolutionView({ accounts, selectedId, onSelect }) {
  const accountId = selectedId || "";
  const [profiles, setProfiles] = useState([]);
  const [counts, setCounts] = useState(EMPTY_COUNTS);
  const [eaA, setEaA] = useState("");
  const [eaB, setEaB] = useState("");
  const [correlation, setCorrelation] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!accountId) {
      setProfiles([]);
      setCounts(EMPTY_COUNTS);
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const data = await api.knowledgeEaProfiles(accountId);
        if (cancelled) return;
        const list = data.profiles || [];
        setProfiles(list);
        setCounts({
          under_review: (data.counts && data.counts.under_review) || 0,
          candidates: (data.counts && data.counts.candidates) || 0,
          validated: (data.counts && data.counts.validated) || 0,
          graveyard: (data.counts && data.counts.graveyard) || 0,
        });
      } catch {
        if (cancelled) return;
        setProfiles([]);
        setCounts(EMPTY_COUNTS);
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
        <h1 className="revolution-memory-title">Memory — what survived validation</h1>
        <div className="revolution-metrics">
          <Metric testId="revolution-metric-review" label="Under review" value={counts.under_review} />
          <Metric testId="revolution-metric-candidates" label="Candidates" value={counts.candidates} />
          <Metric testId="revolution-metric-validated" label="Validated" value={counts.validated} />
          <Metric testId="revolution-metric-graveyard" label="Graveyard" value={counts.graveyard} />
        </div>
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

      <section data-testid="revolution-dossiers">
        {profiles.length === 0 ? (
          <p className="revolution-empty" data-testid="revolution-empty-dossiers">
            No EA profiles for this account.
          </p>
        ) : (
          profiles.map((profile) => (
            <DossierCard key={profile.ea_key || profile.id} profile={profile} />
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
    </div>
  );
}

function DossierCard({ profile }) {
  const records = profile.records || [];
  const occupied = new Set(
    records
      .map((row) => pipelineIndex(row.validation_state))
      .filter((i) => i >= 0)
  );
  const current = furthestIndex(records);
  const hasCandidate = records.some((row) => row.validation_state === "knowledge_candidate");
  const facts = records.filter((row) => FACT_STATES.has(row.validation_state));
  const patterns = records.filter((row) => PATTERN_STATES.has(row.validation_state));
  const graves = records.filter((row) => row.validation_state === "invalidated_conclusion");
  const symbols = (profile.permitted_symbols || []).join(", ") || "—";
  const sessions = (profile.permitted_sessions || []).join(", ") || "—";

  return (
    <article className="revolution-dossier" data-testid="revolution-dossier">
      <header className="revolution-dossier-header">
        <div className="revolution-dossier-title">
          <h2 data-testid="revolution-dossier-name">{profile.name || profile.ea_key}</h2>
          <span className="revolution-meta">{profile.ea_key}</span>
        </div>
        <div className="revolution-dossier-badges">
          <span className="revolution-badge revolution-badge-version" data-testid="revolution-version-badge">
            v{profile.version}
          </span>
          <span
            className={`revolution-badge revolution-badge-status revolution-status-${profile.status || "testing"}`}
            data-testid="revolution-status-badge"
          >
            {profile.status || "testing"}
          </span>
          <span className="revolution-badge revolution-badge-scope">
            {symbols} · {sessions}
          </span>
        </div>
      </header>
      <p className="revolution-purpose" data-testid="revolution-purpose">
        {profile.purpose || "No purpose recorded."}
      </p>

      <ol className="revolution-pipeline" data-testid="revolution-pipeline">
        {PIPELINE.map((step, i) => {
          const isCurrent = i === current;
          const isOccupied = occupied.has(i);
          let cls = "revolution-pipeline-step";
          if (isOccupied) cls += " is-occupied";
          if (isCurrent) cls += " is-current";
          if (step.key === "knowledge" && hasCandidate && isCurrent) cls += " is-candidate";
          return (
            <li key={step.key} className={cls} data-state={step.key}>
              <span className="revolution-pipeline-dot" />
              <span className="revolution-pipeline-label">{step.label}</span>
            </li>
          );
        })}
      </ol>

      <div className="revolution-dossier-body">
        <div className="revolution-dossier-col" data-testid="revolution-insights">
          <h3>Validated facts</h3>
          {facts.length === 0 ? (
            <p className="revolution-empty" data-testid="revolution-empty-insights">
              No validated knowledge for this EA.
            </p>
          ) : (
            facts.map((row) => (
              <FactRow key={row.knowledge_record_id} row={row} />
            ))
          )}
        </div>
        <div className="revolution-dossier-col" data-testid="revolution-active">
          <h3>Active pattern flags</h3>
          {patterns.length === 0 ? (
            <p className="revolution-empty" data-testid="revolution-empty-active">
              No pattern is in the pipeline for this EA.
            </p>
          ) : (
            patterns.map((row) => (
              <FactRow key={row.knowledge_record_id} row={row} />
            ))
          )}
        </div>
      </div>

      <div className="revolution-dossier-graveyard" data-testid="revolution-graveyard">
        <h3>Graveyard</h3>
        {graves.length === 0 ? (
          <p className="revolution-empty" data-testid="revolution-empty-graveyard">
            No invalidated conclusions.
          </p>
        ) : (
          graves.map((row) => (
            <div
              key={row.knowledge_record_id}
              className="revolution-fact-row revolution-grave"
              data-testid="revolution-grave-card"
            >
              <StateBadge state={row.validation_state} />
              <div>
                <p className="revolution-strike">{row.statement}</p>
                <p className="revolution-reason">
                  {row.decided_by || "unknown"} · {row.justification || "no justification recorded"}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

function FactRow({ row }) {
  return (
    <div className="revolution-fact-row" data-testid="revolution-insight-card">
      <StateBadge state={row.validation_state} />
      <div>
        <p>{row.statement}</p>
        {row.is_stale ? (
          <span className="revolution-stale" data-testid="revolution-stale-flag">stale</span>
        ) : null}
      </div>
    </div>
  );
}

function StateBadge({ state }) {
  const tone = STATE_TONE[state] || "neutral";
  return (
    <span className={`revolution-state revolution-state-${tone}`} data-testid="revolution-state-badge">
      {STATE_LABEL[state] || state}
    </span>
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

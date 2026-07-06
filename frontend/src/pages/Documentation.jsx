import React from "react";
import PageShell from "@/pages/PageShell";
import { forgeFactoryLogo } from "@/assets/branding";

function Doc({ title, children, testId }) {
  return (
    <div className="panel doc-block" data-testid={testId}>
      <div className="panel-header">
        <span className="panel-title">{title}</span>
      </div>
      <div className="doc-body">{children}</div>
    </div>
  );
}

export default function Documentation() {
  return (
    <PageShell active="documentation" testId="documentation-page">
      <section className="doc-hero">
        <img
          src={forgeFactoryLogo}
          alt="Forge Factory Lab"
          className="doc-hero-logo"
          data-testid="docs-forge-logo"
        />
        <div>
          <h1>Documentation</h1>
          <p className="mono">Forge Factory Lab · Sr. Atlas — Phase 1</p>
        </div>
      </section>

      <Doc title="Architecture" testId="doc-architecture">
        <ul>
          <li><b>Frontend</b> — React institutional trading terminal (this dashboard).</li>
          <li><b>Backend</b> — FastAPI supervision API (<code>/api/*</code>), MongoDB / SQLite cache and per-account overrides.</li>
          <li><b>MT5 Bridge</b> — Windows-side service exposing live MetaTrader 5 account, positions, deals and equity.</li>
          <li><b>Sr. Atlas / n8n</b> — health-monitoring workflow that polls every core service and produces a structured supervision report.</li>
        </ul>
      </Doc>

      <Doc title="Health Monitoring Workflow" testId="doc-workflow">
        <p>The Sr. Atlas Health Monitor (n8n) fans out to three probes in parallel:</p>
        <ul>
          <li><b>Atlas Backend Health</b> — <code>GET /api/system/health</code></li>
          <li><b>MT5 Bridge Health</b> — <code>GET /health</code> on the bridge</li>
          <li><b>Atlas Dashboard Health</b> — <code>GET /</code></li>
        </ul>
        <p>
          Responses are merged and the <b>Sr. Atlas Report Builder</b> emits a
          structured report (<code>status</code>, <code>backend_ok</code>,
          <code>bridge_ok</code>, <code>dashboard_ok</code>). If any service is
          down, status becomes <code>ALERT</code> and the operator notifier branch
          fires. Import <code>ForgeFactoryLab_SrAtlas_HealthMonitor.json</code> into
          n8n and run <i>Execute workflow</i>.
        </p>
      </Doc>

      <Doc title="Installation (summary)" testId="doc-install">
        <ol>
          <li>Backend: <code>pip install -r backend/requirements.txt</code> then run via supervisor / uvicorn.</li>
          <li>Frontend: <code>yarn install</code> then <code>yarn start</code>.</li>
          <li>MT5 Bridge (Windows): configure <code>mt5-bridge/.env</code> and run <code>run.bat</code>.</li>
          <li>Set <code>MT5_BRIDGE_URL</code> in <code>backend/.env</code> to switch from mock to live data.</li>
          <li>n8n: import the Sr. Atlas Health Monitor workflow and execute.</li>
        </ol>
        <p className="mono">Full guide in the repository README.</p>
      </Doc>

      <Doc title="Roadmap — Phase 2" testId="doc-roadmap">
        <p>
          Sr. Atlas evolves from a monitoring dashboard into the intelligent
          supervisor of the entire Forge Factory Lab ecosystem: state-change
          alerting, MT5 telemetry ingestion, Telegram notifications, AI risk
          assessment and closed-loop control behind human confirmation gates.
        </p>
      </Doc>
    </PageShell>
  );
}

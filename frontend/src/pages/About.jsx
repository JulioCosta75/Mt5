import React from "react";
import PageShell from "@/pages/PageShell";
import { forgeFactoryLogo, srAtlasRound } from "@/assets/branding";

export default function About() {
  return (
    <PageShell active="about" testId="about-page">
      <section className="about-hero">
        <img
          src={forgeFactoryLogo}
          alt="Forge Factory Lab"
          className="about-hero-logo"
          data-testid="about-forge-logo"
        />
        <p className="about-tagline">
          Knowledge, validation and truth come before automation.
        </p>
      </section>

      <div className="panel about-block">
        <div className="panel-header">
          <span className="panel-title">Brand Hierarchy</span>
        </div>
        <div className="about-grid">
          <div className="about-card" data-testid="about-forge-card">
            <img src={forgeFactoryLogo} alt="Forge Factory Lab" height="56" style={{ borderRadius: 10 }} />
            <h3>Forge Factory Lab</h3>
            <ul>
              <li>Company</li>
              <li>Laboratory</li>
              <li>Engineering environment</li>
            </ul>
            <p>
              Forge Factory Lab is the company and engineering laboratory that
              builds, validates and operates the quantitative trading ecosystem.
            </p>
          </div>
          <div className="about-card" data-testid="about-atlas-card">
            <img src={srAtlasRound} alt="Sr. Atlas" height="52" style={{ borderRadius: 10 }} />
            <h3>Sr. Atlas</h3>
            <ul>
              <li>AI Supervisor</li>
              <li>Orchestration system</li>
              <li>Dashboard identity</li>
            </ul>
            <p>
              Sr. Atlas is the supervising AI. In Phase 1 it monitors the health
              and performance of every MT5 account; in Phase 2 it evolves into the
              intelligent orchestrator of the entire Forge Factory Lab ecosystem.
            </p>
          </div>
        </div>
      </div>

      <div className="panel about-block">
        <div className="panel-header">
          <span className="panel-title">Phase 1 — Stable Production Foundation</span>
        </div>
        <div className="about-body">
          <p>
            Phase 1 delivers a production-ready supervision terminal: a real-time
            MT5 dashboard, an MT5 Bridge for live account data, and an n8n health
            monitoring workflow orchestrated under the Sr. Atlas identity.
          </p>
          <p className="mono about-meta">
            © 2026 Forge Factory Lab · Sr. Atlas · Phase 1 complete
          </p>
        </div>
      </div>
    </PageShell>
  );
}

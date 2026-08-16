import React, { useState } from "react";
import { Link } from "react-router-dom";
import { srAtlasRound, srAtlasIcon } from "@/assets/branding";
import { api } from "@/lib/api";

/** Shared top navigation for the secondary pages (About, Help, Settings). */
export default function PageShell({ children, active, testId }) {
  const links = [
    { to: "/", label: "Terminal" },
    { to: "/settings", label: "Settings" },
    { to: "/about", label: "About" },
    { to: "/docs", label: "Help" },
  ];
  const [reporting, setReporting] = useState(false);
  const [banner, setBanner] = useState(null);

  const onReportProblem = async () => {
    if (reporting) return;
    setReporting(true);
    setBanner(null);
    try {
      const res = await api.reportProblem();
      setBanner({ type: "ok", text: res?.message || "Relatório guardado e enviado, obrigado" });
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setBanner({
        type: "error",
        text: typeof detail === "string" && detail.trim()
          ? detail
          : "Não foi possível enviar — tenta mais tarde ou contacta diretamente.",
      });
    } finally {
      setReporting(false);
    }
  };

  return (
    <div className="page-shell" data-testid={testId}>
      <header className="page-shell-header" data-testid="page-header">
        <Link to="/" className="page-shell-brand" data-testid="page-brand-link">
          <img src={srAtlasRound} alt="Sr. Atlas" height="34" width="34" className="brand-mark" style={{ borderRadius: 7 }} />
          <span style={{ fontSize: 16, fontWeight: 600, letterSpacing: "-0.01em" }}>
            Sr. <span className="brand-word">Atlas</span>
          </span>
        </Link>
        <nav className="page-shell-nav">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={`btn ${l.label.toLowerCase() === active ? "active" : ""}`}
              style={{ textDecoration: "none" }}
              data-testid={`pagenav-${l.label.toLowerCase()}`}
            >
              {l.label}
            </Link>
          ))}
          <button
            type="button"
            className="btn"
            data-testid="report-problem-button"
            onClick={onReportProblem}
            disabled={reporting}
            title="Envia um diagnóstico automático à Forge Factory Lab (sem passwords nem tokens)"
          >
            {reporting ? "A enviar…" : "Reportar problema"}
          </button>
        </nav>
        <div className="page-shell-badge">
          <img src={srAtlasIcon} alt="" width="18" height="18" />
          <span className="mono">FORGE FACTORY LAB</span>
        </div>
      </header>
      {banner && (
        <div
          data-testid="report-problem-banner"
          role="status"
          style={{
            padding: "10px 20px",
            fontSize: 13,
            borderBottom: "1px solid var(--bd-default)",
            background: banner.type === "error" ? "rgba(239,68,68,0.10)" : "rgba(245,166,35,0.10)",
            color: banner.type === "error" ? "var(--sig-neg)" : "var(--accent, #F5A623)",
          }}
        >
          {banner.text}
        </div>
      )}
      <main className="page-shell-main">{children}</main>
    </div>
  );
}

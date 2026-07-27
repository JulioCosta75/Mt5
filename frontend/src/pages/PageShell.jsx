import React from "react";
import { Link } from "react-router-dom";
import { srAtlasRound, srAtlasIcon } from "@/assets/branding";

/** Shared top navigation for the secondary pages (About, Documentation). */
export default function PageShell({ children, active, testId }) {
  const links = [
    { to: "/", label: "Terminal" },
    { to: "/settings", label: "Settings" },
    { to: "/about", label: "About" },
    { to: "/docs", label: "Documentation" },
  ];
  return (
    <div className="page-shell" data-testid={testId}>
      <header className="page-shell-header" data-testid="page-header">
        <Link to="/" className="page-shell-brand" data-testid="page-brand-link">
          <img src={srAtlasRound} alt="Sr. Atlas" height="34" width="34" style={{ borderRadius: 7, background: "#000" }} />
          <span style={{ fontSize: 16, fontWeight: 600, letterSpacing: "-0.01em" }}>Sr. Atlas</span>
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
        </nav>
        <div className="page-shell-badge">
          <img src={srAtlasIcon} alt="" width="18" height="18" />
          <span className="mono">FORGE FACTORY LAB</span>
        </div>
      </header>
      <main className="page-shell-main">{children}</main>
    </div>
  );
}

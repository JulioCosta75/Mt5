import React, { useEffect, useState } from "react";
import { forgeFactoryLogo, srAtlasRound } from "@/assets/branding";

/**
 * BrandBoot — combined Welcome + Loading screen.
 * Forge Factory Lab (company) leads the welcome; Sr. Atlas (AI supervisor)
 * initializes with a progress indicator, then the splash fades into the terminal.
 */
export default function BrandBoot({ onDone }) {
  const [progress, setProgress] = useState(0);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const DURATION = 1700;
    const start = Date.now();
    const tick = setInterval(() => {
      setProgress(Math.min(100, Math.round(((Date.now() - start) / DURATION) * 100)));
    }, 50);
    // Guaranteed dismissal — independent of interval throttling in background tabs.
    const done = setTimeout(() => {
      setProgress(100);
      setLeaving(true);
      setTimeout(() => onDone && onDone(), 450);
    }, DURATION);
    return () => {
      clearInterval(tick);
      clearTimeout(done);
    };
  }, [onDone]);

  return (
    <div
      className={`brand-boot ${leaving ? "leaving" : ""}`}
      data-testid="brand-boot"
      role="status"
      aria-live="polite"
    >
      <div className="brand-boot-inner">
        <img
          src={forgeFactoryLogo}
          alt="Forge Factory Lab"
          className="brand-boot-logo"
          data-testid="boot-forge-logo"
        />
        <div className="brand-boot-supervisor" data-testid="boot-sr-atlas">
          <img src={srAtlasRound} alt="Sr. Atlas" width="26" height="26" />
          <span>
            <b>Sr. Atlas</b> · AI Supervisor
          </span>
        </div>

        <div className="brand-boot-bar">
          <div className="brand-boot-bar-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="brand-boot-status mono">
          INITIALIZING SUPERVISION FEED · {progress}%
        </div>
      </div>
      <div className="brand-boot-footer mono">
        FORGE FACTORY LAB — ENGINEERING LABORATORY · PHASE 1
      </div>
    </div>
  );
}

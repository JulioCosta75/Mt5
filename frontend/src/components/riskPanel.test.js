import fs from "fs";
import path from "path";
import { barPct, resolveHeroLayout } from "./riskMetrics";

const panelSrc = fs.readFileSync(path.join(__dirname, "RiskPanel.jsx"), "utf8");
const viewsSrc = fs.readFileSync(path.join(__dirname, "TabViews.jsx"), "utf8");

function extractFunction(src, name) {
  const start = src.indexOf(`function ${name}`);
  expect(start).toBeGreaterThan(-1);
  let i = src.indexOf("{", start);
  let depth = 0;
  const from = start;
  for (; i < src.length; i += 1) {
    if (src[i] === "{") depth += 1;
    else if (src[i] === "}") {
      depth -= 1;
      if (depth === 0) return src.slice(from, i + 1);
    }
  }
  throw new Error(`unclosed function ${name}`);
}

describe("barPct is display-only and never invents a limit", () => {
  test("returns 0 when limit is missing, zero, or non-numeric", () => {
    expect(barPct(10, 0)).toBe(0);
    expect(barPct(10, null)).toBe(0);
    expect(barPct(10, undefined)).toBe(0);
    expect(barPct(10, "x")).toBe(0);
  });

  test("clamps to 0–100", () => {
    expect(barPct(-4, 10)).toBe(0);
    expect(barPct(5, 10)).toBe(50);
    expect(barPct(20, 10)).toBe(100);
  });
});

describe("heroLayout mapping keeps Overview compact and Risk tab full", () => {
  test("heroLayout=full wins over showHeroBars", () => {
    expect(resolveHeroLayout("full", true)).toBe("full");
    expect(resolveHeroLayout("full", false)).toBe("full");
  });

  test("showHeroBars still maps to overview when heroLayout is omitted", () => {
    expect(resolveHeroLayout(null, true)).toBe("overview");
    expect(resolveHeroLayout(undefined, true)).toBe("overview");
  });

  test("classic grid remains the default when neither flag is set", () => {
    expect(resolveHeroLayout(null, false)).toBe(null);
  });
});

describe("Risk tab full hero is the original 8 cells, bars only where a limit exists", () => {
  test("RiskView mounts the full hero, not the Overview compact strip", () => {
    expect(viewsSrc).toMatch(/heroLayout=["']full["']/);
    expect(viewsSrc).toMatch(/data-testid=["']risk-layout["']/);
    expect(viewsSrc).not.toMatch(/showHeroBars/);
  });

  test("FullHeroMetrics keeps equity testid and does not bar daily P&L against % loss", () => {
    const full = extractFunction(panelSrc, "FullHeroMetrics");
    expect(full).toMatch(/label="Equity"/);
    expect(full).toMatch(/testId="account-equity-value"/);
    expect(full).toMatch(/label="Balance"/);
    expect(full).toMatch(/label="Margin used"/);
    expect(full).toMatch(/label="Margin level"/);
    expect(full).toMatch(/label="Daily P&L"/);
    expect(full).toMatch(/label="Current DD"/);
    expect(full).toMatch(/label="Max DD"/);
    expect(full).toMatch(/label="Leverage"/);
    expect(full).not.toMatch(/barPct\(account\.daily_pnl/);
    expect(full).not.toMatch(/barPct\(account\.equity/);
    expect(full).not.toMatch(/barPct\(account\.balance/);
    expect(full).not.toMatch(/barPct\(account\.margin_used/);
    expect(full).not.toMatch(/barPct\(account\.max_drawdown/);
    expect(full).not.toMatch(/barPct\(account\.leverage/);
    expect(full).toMatch(/barPct\(account\.margin_level,\s*200\)/);
    expect(full).toMatch(/barPct\(account\.current_drawdown,\s*limits\.max_daily_loss_pct\)/);
    const showBarCount = (full.match(/showBar/g) || []).length;
    expect(showBarCount).toBe(2);
  });

  test("Overview compact strip still has the Stage 2 three metrics with bars", () => {
    const overview = extractFunction(panelSrc, "OverviewHeroMetrics");
    expect(overview).toMatch(/label="Drawdown"/);
    expect(overview).toMatch(/label="Margin level"/);
    expect(overview).toMatch(/label="Open positions"/);
    expect((overview.match(/showBar/g) || []).length).toBe(3);
  });

  test("saveLimits still posts the same three fields and testids", () => {
    expect(panelSrc).toMatch(/data-testid="risk-max-daily-loss"/);
    expect(panelSrc).toMatch(/data-testid="risk-max-position-size"/);
    expect(panelSrc).toMatch(/data-testid="risk-max-open-positions"/);
    expect(panelSrc).toMatch(/data-testid="risk-save-button"/);
    expect(panelSrc).toMatch(/data-testid="risk-sample-label"/);
    const saveCall = panelSrc.match(/api\.updateRisk\([\s\S]*?\}\);/);
    expect(saveCall).toBeTruthy();
    expect(saveCall[0]).toMatch(/max_daily_loss_pct:\s*parseFloat\(limits\.max_daily_loss_pct\)/);
    expect(saveCall[0]).toMatch(/max_position_size_lots:\s*parseFloat\(limits\.max_position_size_lots\)/);
    expect(saveCall[0]).toMatch(/max_open_positions:\s*parseInt\(limits\.max_open_positions,\s*10\)/);
    expect(saveCall[0]).not.toMatch(/max_drawdown|leverage|margin_level|equity|daily_pnl/);
    expect(panelSrc.match(/api\.updateRisk/g) || []).toHaveLength(1);
  });
});

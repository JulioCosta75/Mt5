import fs from "fs";
import path from "path";
import { barPct, resolveHeroLayout, withinExistingLimits } from "./riskMetrics";
describe("withinExistingLimits uses only current DD and open positions vs existing limits", () => {
  const account = { current_drawdown: -3, open_positions: 2 };
  const limits = { max_daily_loss_pct: 5, max_open_positions: 4, max_position_size_lots: 1 };

  test("true when abs(DD) and open positions are within the two existing limits", () => {
    expect(withinExistingLimits(account, limits)).toBe(true);
    expect(withinExistingLimits({ ...account, current_drawdown: 5 }, limits)).toBe(true);
  });

  test("false when DD or open positions exceed those limits", () => {
    expect(withinExistingLimits({ ...account, current_drawdown: -6 }, limits)).toBe(false);
    expect(withinExistingLimits({ ...account, open_positions: 5 }, limits)).toBe(false);
  });

  test("null when a comparator is missing — does not invent a third rule", () => {
    expect(withinExistingLimits(account, { max_daily_loss_pct: 5 })).toBe(null);
    expect(withinExistingLimits(account, { max_open_positions: 4 })).toBe(null);
    expect(withinExistingLimits(null, limits)).toBe(null);
    expect(withinExistingLimits(account, { max_daily_loss_pct: 0, max_open_positions: 4 })).toBe(null);
  });
});

const panelSrc = fs.readFileSync(path.join(__dirname, "RiskPanel.jsx"), "utf8");
const viewsSrc = fs.readFileSync(path.join(__dirname, "TabViews.jsx"), "utf8");

function sliceBetween(src, startMarker, endMarker) {
  const start = src.indexOf(startMarker);
  const end = src.indexOf(endMarker, start + 1);
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return src.slice(start, end);
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
    const full = sliceBetween(panelSrc, "function FullHeroMetrics", "function ClassicStatGrid");
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
    const overview = sliceBetween(panelSrc, "function OverviewHeroMetrics", "function FullHeroMetrics");
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

  test("full layout shows Unavailable contracts C2–C5 and does not call Phase 3 correlation", () => {
    expect(panelSrc).toMatch(/data-testid="risk-within-limits"/);
    expect(panelSrc).toMatch(/testId: "risk-unavailable-instrument-pct"/);
    expect(panelSrc).toMatch(/testId: "risk-unavailable-sector"/);
    expect(panelSrc).toMatch(/testId: "risk-unavailable-correlation"/);
    expect(panelSrc).toMatch(/testId: "risk-unavailable-var"/);
    expect(panelSrc).toMatch(/data-testid=\{item\.testId\}/);
    expect(panelSrc).not.toMatch(/knowledge\/v1\/correlation/);
    expect(panelSrc).not.toMatch(/api\.knowledge/);
    expect(panelSrc).toMatch(/layout === "full" \? <UnavailableContracts \/>/);
  });
});

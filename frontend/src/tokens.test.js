import fs from "fs";
import path from "path";

const cssPath = path.join(__dirname, "index.css");
const css = fs.readFileSync(cssPath, "utf8");

function tokenValue(name) {
  const match = css.match(new RegExp(`${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}:\\s*([^;]+);`));
  return match ? match[1].trim() : null;
}

describe("Atlas 2 Stage 1 color tokens", () => {
  test("signal colors keep their operational hex values", () => {
    expect(tokenValue("--sig-pos")).toBe("#22C55E");
    expect(tokenValue("--sig-neg")).toBe("#EF4444");
    expect(tokenValue("--sig-warn")).toBe("#F59E0B");
    expect(tokenValue("--sig-info")).toBe("#3B82F6");
  });

  test("brand gold exists and is not a signal color", () => {
    const gold = tokenValue("--brand-gold");
    expect(gold).toBe("#C9A962");
    expect(gold).not.toBe(tokenValue("--sig-warn"));
    expect(gold).not.toBe(tokenValue("--sig-neg"));
    expect(gold).not.toBe(tokenValue("--sig-pos"));
    expect(gold).not.toBe(tokenValue("--sig-info"));
  });

  test("section heading class is uppercase with wide tracking", () => {
    expect(css).toMatch(/\.section-heading/);
    expect(css).toMatch(/\.panel-title,\s*\n\.section-heading/);
    expect(css).toMatch(/text-transform:\s*uppercase/);
    expect(css).toMatch(/letter-spacing:\s*0\.2em/);
  });

  test("alert and badge signal classes still use signal tokens, not brand gold", () => {
    expect(css).toMatch(/\.alert-row\.WARNING\s*\{\s*border-left-color:\s*var\(--sig-warn\)/);
    expect(css).toMatch(/\.alert-row\.CRITICAL\s*\{\s*border-left-color:\s*var\(--sig-neg\)/);
    expect(css).toMatch(/\.badge\.paused\s*\{[^}]*var\(--sig-warn\)/s);
    expect(css).toMatch(/\.badge\.error\s*\{[^}]*var\(--sig-neg\)/s);
    expect(css).toMatch(/\.badge\.live\s*\{[^}]*var\(--sig-pos\)/s);
    expect(css).not.toMatch(/\.alert-row\.WARNING[^}]*--brand-gold/);
    expect(css).not.toMatch(/\.badge\.paused[^}]*--brand-gold/);
  });

  test("Revolution purple identity in this stylesheet is unchanged", () => {
    expect(css).toMatch(/\.btn\.nav-revolution \{\s*color: #C4B5FD;/);
    expect(css).toMatch(/border-bottom: 2px solid #A855F7;/);
  });
});

describe("Atlas 2 Stage 2 Overview chrome", () => {
  test("featured hero cards use brand gold accent, not signal warn", () => {
    expect(css).toMatch(/\.hero-card \{/);
    expect(css).toMatch(/border-top: 2px solid var\(--brand-gold-border\)/);
    expect(css).toMatch(/\.hero-bar-fill \{[^}]*background: var\(--brand-gold\)/s);
    expect(css).toMatch(/\.overview-layout \{/);
  });
});

describe("Atlas 2 Stage 3 Risk tab chrome", () => {
  test("full hero and limits form reuse established type scale and 768 breakpoint", () => {
    expect(css).toMatch(/\.risk-hero-full \{/);
    expect(css).toMatch(/\.risk-layout \{/);
    expect(css).toMatch(/\.risk-limits-card \{/);
    expect(css).toMatch(/\.risk-limits-grid \{/);
    expect(css).toMatch(/\.risk-hero,\s*\n\s*\.risk-hero-full \{[^}]*grid-template-columns:\s*1fr;/);
    expect(css).toMatch(/\.risk-limits-grid \{\s*\n\s*grid-template-columns:\s*1fr;/);
  });

  test("Risk save button uses brand gold, not a signal color", () => {
    expect(css).toMatch(/\.risk-layout \[data-testid="risk-save-button"\] \{[^}]*background:\s*var\(--brand-gold\)/s);
    expect(css).not.toMatch(/\.risk-layout \[data-testid="risk-save-button"\] \{[^}]*--sig-/s);
  });
});

describe("Atlas 2 Stage 4 Overview tables", () => {
  test("table chrome is scoped to overview-layout, not risk-layout", () => {
    expect(css).toMatch(/\.overview-layout \[data-testid="accounts-table"\] th/);
    expect(css).toMatch(/\.overview-layout \[data-testid="trades-panel"\] th/);
    expect(css).not.toMatch(/\.risk-layout \[data-testid="accounts-table"\]/);
    expect(css).not.toMatch(/\.risk-layout \[data-testid="trades-panel"\]/);
  });

  test("Risk layout table type bump is unchanged from Stage 3", () => {
    expect(css).toMatch(/\.risk-layout th,\s*\n\.risk-layout td \{\s*\n\s*font-size: 13px;\s*\n\s*padding: 10px 12px;/);
  });

  test("Overview selected account row uses brand gold, not a signal token", () => {
    const selected = css.match(/\.overview-layout \[data-testid="accounts-table"\] tbody tr\[style\*=["']--text-primary["']\] \{[^}]+\}/);
    expect(selected).toBeTruthy();
    expect(selected[0]).toMatch(/var\(--brand-gold-soft\)/);
    expect(selected[0]).toMatch(/border-left-color:\s*var\(--brand-gold\)/);
    expect(selected[0]).not.toMatch(/--sig-/);
  });

  test("narrow breakpoint tightens Overview table padding only", () => {
    expect(css).toMatch(/@media \(max-width: 768px\)[\s\S]*\.overview-layout \[data-testid="accounts-table"\] td[\s\S]*padding:\s*10px 12px;/);
  });
});

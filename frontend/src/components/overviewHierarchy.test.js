import fs from "fs";
import path from "path";

const css = fs.readFileSync(path.join(__dirname, "..", "index.css"), "utf8");
const dashboardSrc = fs.readFileSync(path.join(__dirname, "..", "Dashboard.jsx"), "utf8");

describe("A2 Overview hierarchy is wrapper CSS, not new metrics", () => {
  test("Overview panels get hero-card gold top border; Risk layout does not copy it", () => {
    expect(css).toMatch(/\.overview-layout \.panel \{[^}]*border-top: 2px solid var\(--brand-gold-border\)/s);
    expect(css).not.toMatch(/\.risk-layout \.panel \{[^}]*border-top: 2px solid var\(--brand-gold-border\)/s);
  });

  test("charts stack to one column at 768 without changing series props", () => {
    expect(dashboardSrc).toMatch(/className="overview-charts"/);
    expect(dashboardSrc).toMatch(/<EquityChart data=\{equity\} isSample=\{isSample\} \/>/);
    expect(dashboardSrc).toMatch(/maxDD=\{drawdown\.max_drawdown\}/);
    expect(css).toMatch(/\.overview-charts \{[^}]*grid-template-columns: 1fr 1fr/s);
    expect(css).toMatch(/\.overview-charts \{\s*grid-template-columns: 1fr;/);
  });
});

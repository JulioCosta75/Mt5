import fs from "fs";
import path from "path";

const chartsSrc = fs.readFileSync(path.join(__dirname, "Charts.jsx"), "utf8");
const dashSrc = fs.readFileSync(path.join(__dirname, "..", "Dashboard.jsx"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "..", "index.css"), "utf8");
const alertsSrc = fs.readFileSync(path.join(__dirname, "AlertsPanel.jsx"), "utf8");
const supervisionSrc = fs.readFileSync(path.join(__dirname, "SupervisionPanel.jsx"), "utf8");
const viewsSrc = fs.readFileSync(path.join(__dirname, "TabViews.jsx"), "utf8");
const settingsSrc = fs.readFileSync(path.join(__dirname, "..", "pages", "Settings.jsx"), "utf8");

describe("A4/A5 chart chrome tokens and existing-series window", () => {
  test("tooltip and grid use tokens; series stay signal green/red", () => {
    expect(chartsSrc).toMatch(/background:\s*"var\(--bg-base\)"/);
    expect(chartsSrc).toMatch(/border:\s*"1px solid var\(--bd-default\)"/);
    expect(chartsSrc).toMatch(/stroke="var\(--bd-subtle\)"/);
    expect(chartsSrc).toMatch(/stroke="var\(--sig-pos\)"/);
    expect(chartsSrc).toMatch(/stroke="var\(--sig-neg\)"/);
    expect(chartsSrc).not.toMatch(/stroke="#22C55E"/);
    expect(chartsSrc).not.toMatch(/#C9A962/);
    expect(chartsSrc).not.toMatch(/Equity Curve · 90D/);
  });

  test("7D/30D/90D toggles filter existing series; empty window is Unavailable", () => {
    expect(chartsSrc).toMatch(/windowByDays\(data, days\)/);
    expect(chartsSrc).toMatch(/data-testid=\{\`\$\{prefix\}-window-\$\{d\}\`\}/);
    expect(chartsSrc).toMatch(/testId="equity-window-unavailable"/);
    expect(chartsSrc).toMatch(/testId="drawdown-window-unavailable"/);
    expect(chartsSrc).not.toMatch(/fake|synthetic|invent/i);
  });

  test("Dashboard still passes the existing equity/drawdown series unchanged", () => {
    expect(dashSrc).toMatch(/<EquityChart data=\{equity\} isSample=\{isSample\} \/>/);
    expect(dashSrc).toMatch(/maxDD=\{drawdown\.max_drawdown\}/);
  });
});

describe("A7 alerts hierarchy and supervision signal tokens", () => {
  test("alert row is severity, time, then body", () => {
    expect(alertsSrc).toMatch(/className="alert-severity"/);
    expect(alertsSrc).toMatch(/className="mono alert-time"/);
    expect(alertsSrc).toMatch(/className="alert-body"/);
    expect(alertsSrc).toMatch(/data-testid=\{`alert-ack-\$\{a\.id\}`\}/);
    expect(alertsSrc).toMatch(/data-testid="alert-ack-all"/);
    expect(css).toMatch(/\.alert-severity \{/);
    expect(css).toMatch(/\.alert-body \{/);
  });

  test("ServiceDot uses signal tokens, not leftover hex", () => {
    expect(supervisionSrc).toMatch(/ok === true \? "var\(--sig-pos\)"/);
    expect(supervisionSrc).toMatch(/ok === false \? "var\(--sig-neg\)"/);
    expect(supervisionSrc).not.toMatch(/#22C55E|#EF4444|#71717A/);
    expect(supervisionSrc).toMatch(/api\.postAtlasReport\(\{ source: "dashboard" \}\)/);
  });
});

describe("A8 reports and audit layouts", () => {
  test("reports keep generate/filter/expand and gold generate chrome", () => {
    expect(viewsSrc).toMatch(/data-testid="reports-layout"/);
    expect(viewsSrc).toMatch(/data-testid="reports-generate-button"/);
    expect(viewsSrc).toMatch(/data-testid="reports-account-filter"/);
    expect(viewsSrc).toMatch(/data-testid="reports-row-expanded"/);
    expect(viewsSrc).toMatch(/api\.postAtlasReport\(\{ source: "reports-tab" \}\)/);
    expect(css).toMatch(/\.reports-layout \[data-testid="reports-generate-button"\] \{[^}]*background:\s*var\(--brand-gold\)/s);
  });

  test("audit stacks at 768 and still hosts AlertsPanel", () => {
    expect(viewsSrc).toMatch(/data-testid="audit-layout"/);
    expect(viewsSrc).toMatch(/<AlertsPanel alerts=\{alerts\} onAck=\{onAck\} isSample=\{isSample\} \/>/);
    expect(css).toMatch(/\.audit-layout \{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) 360px/s);
    expect(css).toMatch(/\.audit-layout \{\s*grid-template-columns:\s*1fr;/);
  });
});

describe("A10 settings tokens and system telemetry Unavailable", () => {
  test("Settings leftover hex is replaced with tokens; handlers stay", () => {
    expect(settingsSrc).not.toMatch(/#[0-9A-Fa-f]{3,8}/);
    expect(settingsSrc).toMatch(/color: "var\(--sig-pos\)"/);
    expect(settingsSrc).toMatch(/data-testid="mt5-save"/);
    expect(settingsSrc).toMatch(/data-testid="mt5-clear"/);
    expect(settingsSrc).toMatch(/data-testid="license-activate"/);
    expect(settingsSrc).toMatch(/api\.saveMt5Config/);
    expect(settingsSrc).toMatch(/api\.activateLicense/);
  });

  test("live System latency/strategies are Unavailable, not 42 ms or 6", () => {
    expect(dashSrc).not.toMatch(/42 ms/);
    expect(dashSrc).not.toMatch(/SAMPLE · 6/);
    expect(dashSrc).toMatch(/data-testid="system-api-latency"/);
    expect(dashSrc).toMatch(/data-testid="system-strategies"/);
    expect(dashSrc).toMatch(/Unavailable<span className="kbd"[^>]*>C7/);
    expect(dashSrc).toMatch(/data-testid="system-strategies">Unavailable</);
  });
});

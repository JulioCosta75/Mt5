import fs from "fs";
import path from "path";

const dashboardSrc = fs.readFileSync(path.join(__dirname, "..", "Dashboard.jsx"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "..", "index.css"), "utf8");

describe("A1 compact top nav keeps primary tabs and secondary testids", () => {
  test("primary TABS list is unchanged", () => {
    expect(dashboardSrc).toMatch(/const TABS = \["Overview", "Strategies", "Risk", "Reports", "Audit"\];/);
  });

  test("About, Docs, and Settings keep their testids inside More", () => {
    expect(dashboardSrc).toMatch(/data-testid="nav-more"/);
    expect(dashboardSrc).toMatch(/data-testid="nav-more-toggle"/);
    expect(dashboardSrc).toMatch(/data-testid="nav-about"/);
    expect(dashboardSrc).toMatch(/data-testid="nav-docs"/);
    expect(dashboardSrc).toMatch(/data-testid="nav-settings"/);
    expect(dashboardSrc).toMatch(/data-testid="nav-revolution"/);
    expect(dashboardSrc).toMatch(/data-testid="refresh-button"/);
  });

  test("More menu is decorative gold chrome, not a signal color", () => {
    expect(css).toMatch(/\.app-nav-more-panel \{/);
    expect(css).toMatch(/border-top: 2px solid var\(--brand-gold-border\)/);
    const panel = css.match(/\.app-nav-more-panel \{[^}]+\}/);
    expect(panel).toBeTruthy();
    expect(panel[0]).not.toMatch(/--sig-/);
  });

  test("768 header wraps instead of scaling the app", () => {
    expect(css).toMatch(/\.app-header \{/);
    expect(css).not.toMatch(/\.app-header[^}]*transform:\s*scale/);
    expect(css).not.toMatch(/\.App[^}]*zoom:/);
  });
});

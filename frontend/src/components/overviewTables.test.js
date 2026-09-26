import fs from "fs";
import path from "path";

const accountsSrc = fs.readFileSync(path.join(__dirname, "AccountsTable.jsx"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "..", "index.css"), "utf8");

describe("A3 Overview tables keep Risk pixel-identical except unused class", () => {
  test("selected row still uses the original inline marker plus is-selected class", () => {
    expect(accountsSrc).toMatch(/className=\{active \? "is-selected" : undefined\}/);
    expect(accountsSrc).toMatch(/background: active \? "rgba\(244,244,245,0\.04\)" : undefined/);
    expect(accountsSrc).toMatch(/borderLeft: active \? "2px solid var\(--text-primary\)" : "2px solid transparent"/);
    expect(accountsSrc).toMatch(/onClick=\{\(\) => onSelect\(acc\.id\)\}/);
  });

  test("gold selected chrome is scoped to overview-layout, not risk-layout", () => {
    expect(css).toMatch(/\.overview-layout \[data-testid="accounts-table"\] tbody tr\.is-selected \{/);
    expect(css).not.toMatch(/\.risk-layout \[data-testid="accounts-table"\]/);
    expect(css).not.toMatch(/\.risk-layout .is-selected/);
  });

  test("Overview table min-width enables inner horizontal scroll, not page zoom", () => {
    expect(css).toMatch(/\.overview-layout \[data-testid="accounts-table"\],\s*\n\.overview-layout \[data-testid="trades-panel"\] table \{\s*\n\s*min-width: 960px;/);
    expect(css).not.toMatch(/\.App \{[^}]*transform:\s*scale/s);
  });
});

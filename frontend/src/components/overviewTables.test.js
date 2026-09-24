import fs from "fs";
import path from "path";

const accountsSrc = fs.readFileSync(path.join(__dirname, "AccountsTable.jsx"), "utf8");
const tradesSrc = fs.readFileSync(path.join(__dirname, "TradesTable.jsx"), "utf8");
const dashboardSrc = fs.readFileSync(path.join(__dirname, "..", "Dashboard.jsx"), "utf8");

describe("Stage 4 does not change AccountsTable / TradesTable behavior", () => {
  test("AccountsTable keeps columns, testids, select handler, and inline selected marker", () => {
    expect(accountsSrc).toMatch(/data-testid="accounts-table"/);
    expect(accountsSrc).toMatch(/data-testid=\{`account-row-\$\{acc\.id\}`\}/);
    expect(accountsSrc).toMatch(/onClick=\{\(\) => onSelect\(acc\.id\)\}/);
    expect(accountsSrc).toMatch(/background: active \? "rgba\(244,244,245,0\.04\)" : undefined/);
    expect(accountsSrc).toMatch(/borderLeft: active \? "2px solid var\(--text-primary\)" : "2px solid transparent"/);
    expect(accountsSrc).toMatch(/data-testid="accounts-sample-label"/);
    expect(accountsSrc).toMatch(/fmt\.money\(acc\.balance\)/);
    expect(accountsSrc).toMatch(/fmt\.money\(acc\.equity\)/);
    expect(accountsSrc).toMatch(/pnlClass\(acc\.daily_pnl\)/);
  });

  test("TradesTable keeps sort, filters, and summary testids", () => {
    expect(tradesSrc).toMatch(/data-testid="trades-panel"/);
    expect(tradesSrc).toMatch(/data-testid="trades-symbol-filter"/);
    expect(tradesSrc).toMatch(/data-testid="trades-side-filter"/);
    expect(tradesSrc).toMatch(/data-testid="trades-net-pnl"/);
    expect(tradesSrc).toMatch(/data-testid="trades-win-rate"/);
    expect(tradesSrc).toMatch(/data-testid=\{`trades-sort-\$\{k\}`\}/);
    expect(tradesSrc).toMatch(/data-testid="trades-sample-label"/);
    expect(tradesSrc).toMatch(/filtered\.slice\(0, 80\)/);
  });

  test("Overview still mounts both tables inside overview-layout with no new props", () => {
    expect(dashboardSrc).toMatch(/className="overview-layout"/);
    expect(dashboardSrc).toMatch(/<AccountsTable accounts=\{accounts\} selectedId=\{selectedId\}/);
    expect(dashboardSrc).toMatch(/<TradesTable trades=\{trades\} accountId=\{selectedId\} isSample=\{isSample\} \/>/);
    expect(dashboardSrc).not.toMatch(/AccountsTable[^>]*className/);
    expect(dashboardSrc).not.toMatch(/TradesTable[^>]*className/);
  });
});

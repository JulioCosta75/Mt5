import fs from "fs";
import path from "path";
import { healthFromKpis } from "./components/OverviewHero";
import {
  dashboardReducer,
  globalsFromSettled,
  shouldApplyAccountDetail,
} from "./dashboardFeed";

const dashboardSrc = fs.readFileSync(path.join(__dirname, "Dashboard.jsx"), "utf8");

function sliceBetween(src, startMarker, endMarker) {
  const start = src.indexOf(startMarker);
  const end = src.indexOf(endMarker, start + 1);
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return src.slice(start, end);
}

const previous = {
  kpis: { critical_alerts: 0, active_alerts: 0, total_equity: 1000 },
  accounts: [{ id: "MT5-1", status: "OFFLINE", stale: true }],
  selectedId: "MT5-1",
  equity: [{ t: "t0", equity: 1000 }],
  drawdown: { series: [1], max_drawdown: 2, current_drawdown: 1 },
  trades: [{ id: "t1" }],
  alerts: [{ id: "a1", severity: "WARNING" }],
  refreshing: false,
  loading: false,
};

describe("loadGlobals keeps the previous feed when a poll fails", () => {
  test("a rejected or invalid feed is null and the reducer keeps the previous value", () => {
    const feeds = globalsFromSettled([
      { status: "rejected", reason: new Error("timeout") },
      { status: "fulfilled", value: { accounts: [] } },
      { status: "fulfilled", value: { count: 0 } },
    ]);
    expect(feeds).toEqual({ kpis: null, accounts: null, alerts: null });

    const next = dashboardReducer(previous, { type: "SET_GLOBALS", ...feeds });
    expect(next.kpis).toEqual(previous.kpis);
    expect(next.accounts).toEqual(previous.accounts);
    expect(next.alerts).toEqual(previous.alerts);
    expect(next.selectedId).toBe("MT5-1");
    expect(healthFromKpis(next.kpis, next.accounts).word).toBe("OFFLINE");
  });

  test("a rejected alerts feed keeps the previous alerts while a real accounts list replaces the table", () => {
    const feeds = globalsFromSettled([
      { status: "fulfilled", value: previous.kpis },
      { status: "fulfilled", value: [{ id: "MT5-2", status: "LIVE" }] },
      { status: "rejected", reason: new Error("timeout") },
    ]);
    const next = dashboardReducer(previous, { type: "SET_GLOBALS", ...feeds });
    expect(next.alerts).toEqual(previous.alerts);
    expect(next.accounts).toEqual([{ id: "MT5-2", status: "LIVE" }]);
    expect(next.selectedId).toBe("MT5-1");
    expect(healthFromKpis(next.kpis, next.accounts).word).toBe("OK");
  });

  test("a fulfilled feed replaces only that feed, including an empty list", () => {
    const feeds = globalsFromSettled([
      { status: "fulfilled", value: { critical_alerts: 1, active_alerts: 1 } },
      { status: "rejected", reason: new Error("timeout") },
      { status: "fulfilled", value: { count: 0, alerts: [] } },
    ]);
    const next = dashboardReducer(previous, { type: "SET_GLOBALS", ...feeds });
    expect(next.kpis).toEqual({ critical_alerts: 1, active_alerts: 1 });
    expect(next.accounts).toEqual(previous.accounts);
    expect(next.alerts).toEqual([]);
    expect(healthFromKpis(next.kpis, next.accounts).word).toBe("OFFLINE");
  });

  test("Dashboard sends null feeds through SET_GLOBALS", () => {
    const loadGlobals = sliceBetween(dashboardSrc, "const loadGlobals", "const loadAccountDetail");
    expect(loadGlobals).toMatch(/Promise\.allSettled\(\[api\.kpis\(\), api\.accounts\(\), api\.alerts\(\)\]\)/);
    expect(loadGlobals).toMatch(/globalsFromSettled\(settled\)/);
    expect(loadGlobals).toMatch(/type: "SET_GLOBALS"/);
    expect(loadGlobals).not.toMatch(/: \[\]/);
  });
});

describe("loadAccountDetail drops a response for an account that is no longer selected", () => {
  test("SET_DETAIL applies only when the requested id is still selected", () => {
    expect(shouldApplyAccountDetail("MT5-1", "MT5-1")).toBe(true);
    expect(shouldApplyAccountDetail("MT5-1", "MT5-2")).toBe(false);
    expect(shouldApplyAccountDetail("MT5-1", null)).toBe(false);
  });

  test("the check runs after the detail requests resolve", () => {
    const loadDetail = sliceBetween(dashboardSrc, "const loadAccountDetail", "const pollBusyRef");
    const awaitAt = loadDetail.indexOf("await Promise.all");
    const checkAt = loadDetail.indexOf("shouldApplyAccountDetail(id, selectedIdRef.current)");
    const dispatchAt = loadDetail.indexOf('type: "SET_DETAIL"');
    expect(awaitAt).toBeGreaterThan(-1);
    expect(checkAt).toBeGreaterThan(awaitAt);
    expect(dispatchAt).toBeGreaterThan(checkAt);
    expect(dashboardSrc).toMatch(/selectedIdRef\.current = selectedId;/);
  });
});

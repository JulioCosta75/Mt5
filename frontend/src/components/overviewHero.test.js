import {
  healthFromKpis,
  mt5FromStatus,
} from "./OverviewHero";

describe("Overview hero uses existing KPI / MT5 status fields", () => {
  test("maps critical_alerts to ALERT without inventing a new count", () => {
    const result = healthFromKpis({ critical_alerts: 2, active_alerts: 5 });
    expect(result.word).toBe("ALERT");
    expect(result.detail).toBe("2 critical · 5 active");
  });

  test("maps active_alerts to WARNING using the same fields as the ticker", () => {
    const result = healthFromKpis({ critical_alerts: 0, active_alerts: 3 });
    expect(result.word).toBe("WARNING");
    expect(result.detail).toBe("3 active alerts");
  });

  test("OK when both alert counts are zero", () => {
    expect(healthFromKpis({ critical_alerts: 0, active_alerts: 0 }).word).toBe("OK");
  });

  test("MT5 card follows existing config states", () => {
    expect(mt5FromStatus({ state: "connected" }, false).word).toBe("CONNECTED");
    expect(mt5FromStatus({ state: "bridge_down" }, false).word).toBe("BRIDGE DOWN");
    expect(mt5FromStatus({ state: "bridge_down" }, false).signal).toBe("cell-neg");
    expect(mt5FromStatus({ state: "pending_restart" }, false).word).toBe("PENDING");
    expect(mt5FromStatus({ state: "unconfigured" }, false).word).toBe("OFFLINE");
    expect(mt5FromStatus({ state: "connected" }, true).word).toBe("OFFLINE");
  });

  test("health is OFFLINE while any account is served from cache", () => {
    const accounts = [{ id: "MT5-1", status: "OFFLINE", stale: true }, { id: "MT5-2", status: "LIVE" }];
    const result = healthFromKpis({ critical_alerts: 0, active_alerts: 0 }, accounts);
    expect(result.word).toBe("OFFLINE");
    expect(result.signal).toBe("cell-neg");
    expect(result.detail).toBe("1 account offline · data may be outdated");
  });

  test("health ignores live accounts", () => {
    expect(healthFromKpis({ critical_alerts: 0, active_alerts: 0 }, [{ status: "LIVE" }]).word).toBe("OK");
  });

  test("MT5 card tells a closed terminal from a bridge outage", () => {
    const r = mt5FromStatus({ state: "mt5_offline" }, false);
    expect(r.word).toBe("MT5 OFFLINE");
    expect(r.signal).toBe("cell-neg");
  });
});

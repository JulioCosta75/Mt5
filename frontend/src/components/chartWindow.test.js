import { CHART_WINDOWS, DEFAULT_CHART_WINDOW_DAYS, pointTimeMs, windowByDays } from "./chartWindow";

const NOW = Date.parse("2026-09-25T12:00:00.000Z");

function pt(iso, extra = {}) {
  return { t: iso, ...extra };
}

describe("windowByDays filters existing series and never invents points", () => {
  test("default window is 90D and the allowed set is 7/30/90", () => {
    expect(DEFAULT_CHART_WINDOW_DAYS).toBe(90);
    expect(CHART_WINDOWS).toEqual([7, 30, 90]);
  });

  test("keeps points with t >= now − N days", () => {
    const series = [
      pt("2026-06-01T00:00:00.000Z", { equity: 1 }),
      pt("2026-09-01T00:00:00.000Z", { equity: 2 }),
      pt("2026-09-20T00:00:00.000Z", { equity: 3 }),
      pt("2026-09-25T00:00:00.000Z", { equity: 4 }),
    ];
    const week = windowByDays(series, 7, NOW);
    expect(week.map((p) => p.equity)).toEqual([3, 4]);
    const month = windowByDays(series, 30, NOW);
    expect(month.map((p) => p.equity)).toEqual([2, 3, 4]);
    const quarter = windowByDays(series, 90, NOW);
    expect(quarter.map((p) => p.equity)).toEqual([2, 3, 4]);
  });

  test("empty window returns [] — not synthetic points", () => {
    const series = [pt("2020-01-01T00:00:00.000Z", { equity: 99 })];
    expect(windowByDays(series, 7, NOW)).toEqual([]);
    expect(windowByDays([], 90, NOW)).toEqual([]);
    expect(windowByDays(null, 90, NOW)).toEqual([]);
    expect(windowByDays(series, 0, NOW)).toEqual([]);
    expect(windowByDays(series, "x", NOW)).toEqual([]);
  });

  test("parses ISO strings and unix seconds or milliseconds", () => {
    expect(pointTimeMs({ t: "2026-09-25T12:00:00.000Z" })).toBe(NOW);
    expect(pointTimeMs({ t: NOW })).toBe(NOW);
    expect(pointTimeMs({ t: NOW / 1000 })).toBe(NOW);
    expect(Number.isFinite(pointTimeMs({ t: "nope" }))).toBe(false);
  });
});

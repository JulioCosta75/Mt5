/**
 * Client-side window of an existing equity/drawdown series.
 * Does not invent points: empty windows stay empty.
 * Formula: keep points with t >= now − N days.
 */
export const CHART_WINDOWS = [7, 30, 90];
export const DEFAULT_CHART_WINDOW_DAYS = 90;
const MS_PER_DAY = 86400000;

export function pointTimeMs(point) {
  if (!point || point.t == null) return NaN;
  const t = point.t;
  if (typeof t === "number" && Number.isFinite(t)) {
    return t < 1e12 ? t * 1000 : t;
  }
  const ms = Date.parse(t);
  return Number.isFinite(ms) ? ms : NaN;
}

export function windowByDays(series, days, nowMs = Date.now()) {
  const n = Number(days);
  if (!Array.isArray(series) || !Number.isFinite(n) || n <= 0) return [];
  const now = Number(nowMs);
  if (!Number.isFinite(now)) return [];
  const cutoff = now - n * MS_PER_DAY;
  return series.filter((p) => {
    const t = pointTimeMs(p);
    return Number.isFinite(t) && t >= cutoff;
  });
}

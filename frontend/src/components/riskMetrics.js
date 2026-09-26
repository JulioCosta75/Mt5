/**
 * Display-only helpers for Risk hero bars.
 * Does not invent risk rules: a bar is a ratio of two numbers the UI already has.
 */
export function barPct(current, limit) {
  const c = Number(current);
  const l = Number(limit);
  if (!Number.isFinite(c) || !Number.isFinite(l) || l <= 0) return 0;
  return Math.min(100, Math.max(0, (c / l) * 100));
}

/**
 * Display-only fill for drawdown bars. current_drawdown is signed (negative);
 * the limit is a positive magnitude. barPct itself must stay unsigned so
 * margin/positions bars are unchanged.
 */
export function drawdownBarPct(current, limit) {
  return barPct(Math.abs(Number(current)), limit);
}

export function resolveHeroLayout(heroLayout, showHeroBars) {
  return heroLayout || (showHeroBars ? "overview" : null);
}

/**
 * Display-only: current DD vs max_daily_loss_pct and open positions vs
 * max_open_positions — the same two comparisons already drawn as bars.
 * Returns null when a comparator is missing; never invents a third rule.
 */
export function withinExistingLimits(account, limits) {
  if (!account || !limits) return null;
  const dd = Math.abs(Number(account.current_drawdown));
  const ddLimit = Number(limits.max_daily_loss_pct);
  const open = Number(account.open_positions);
  const openLimit = Number(limits.max_open_positions);
  if (!Number.isFinite(dd) || !Number.isFinite(ddLimit) || ddLimit <= 0) return null;
  if (!Number.isFinite(open) || !Number.isFinite(openLimit) || openLimit <= 0) return null;
  return dd <= ddLimit && open <= openLimit;
}

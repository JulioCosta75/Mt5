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

export function resolveHeroLayout(heroLayout, showHeroBars) {
  return heroLayout || (showHeroBars ? "overview" : null);
}

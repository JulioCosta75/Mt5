/**
 * Sample / mock presentation helpers for Sr. Atlas Phase 2.
 * Live connected mode must not receive simulated labels.
 */

const LIVE_STATES = new Set(["connected", "bridge_down"]);

export function isSamplePresentation(mt5Status, healthMode) {
  if (healthMode === "mock") return true;
  if (!mt5Status) return true;
  if (mt5Status.mode === "mock") return true;
  // A bridge outage in MT5 mode is still live data (served from cache), not sample.
  return !LIVE_STATES.has(mt5Status.state);
}

export function formatSimulatedStatus(status) {
  if (!status) return "SIM · —";
  return `SIM · ${status}`;
}

export const SAMPLE_DATA_LABEL = "SAMPLE DATA";
export const SIMULATED_ALERTS_TITLE = "Alerts · Simulated Sample";

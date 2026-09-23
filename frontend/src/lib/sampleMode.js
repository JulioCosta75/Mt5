/**
 * Sample / mock presentation helpers for Sr. Atlas Phase 2.
 * Live connected mode must not receive simulated labels.
 */

export function isSamplePresentation(mt5Status, healthMode) {
  if (healthMode === "mock") return true;
  if (!mt5Status) return true;
  if (mt5Status.mode === "mock") return true;
  return mt5Status.state !== "connected";
}

export function formatSimulatedStatus(status) {
  if (!status) return "SIM · —";
  return `SIM · ${status}`;
}

export const SAMPLE_DATA_LABEL = "SAMPLE DATA";
export const SIMULATED_ALERTS_TITLE = "Alerts · Simulated Sample";

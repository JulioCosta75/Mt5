// Feed refresh for the dashboard.
// A rejected or invalid feed is null. The reducer keeps that feed's previous
// value, so a transient timeout does not wipe the accounts table or alerts.
// An empty array is a real response and replaces the previous value.

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function fulfilledValue(result) {
  if (!result || result.status !== "fulfilled") return undefined;
  return result.value;
}

export function globalsFromSettled(settled) {
  const kpisRaw = fulfilledValue(settled[0]);
  const accountsRaw = fulfilledValue(settled[1]);
  const alertsRaw = fulfilledValue(settled[2]);
  return {
    kpis: isObject(kpisRaw) ? kpisRaw : null,
    accounts: Array.isArray(accountsRaw) ? accountsRaw : null,
    alerts: isObject(alertsRaw) && Array.isArray(alertsRaw.alerts) ? alertsRaw.alerts : null,
  };
}

function kept(next, prev) {
  return next == null ? prev : next;
}

export function dashboardReducer(state, action) {
  switch (action.type) {
    case "SET_GLOBALS": {
      const accounts = kept(action.accounts, state.accounts);
      const selectedId = state.selectedId || (
        action.accounts == null ? state.selectedId : (action.accounts[0]?.id ?? null)
      );
      return {
        ...state,
        kpis: kept(action.kpis, state.kpis),
        accounts,
        alerts: kept(action.alerts, state.alerts),
        selectedId,
      };
    }
    case "SET_DETAIL":
      return { ...state, equity: action.equity, drawdown: action.drawdown, trades: action.trades };
    case "SELECT":
      return { ...state, selectedId: action.id };
    case "ACK_ALERT":
      return { ...state, alerts: state.alerts.map(a => a.id === action.id ? { ...a, acknowledged: true } : a) };
    case "REFRESHING":
      return { ...state, refreshing: action.value };
    case "LOADING":
      return { ...state, loading: action.value };
    default:
      return state;
  }
}

// True only when the detail response still belongs to the selected account.
export function shouldApplyAccountDetail(requestedId, selectedId) {
  return requestedId != null && requestedId === selectedId;
}

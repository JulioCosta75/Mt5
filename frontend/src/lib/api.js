import axios from "axios";

// Same-origin when unset/empty (Windows installer serves dashboard from backend).
const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

const client = axios.create({ baseURL: API, timeout: 15000 });

export const api = {
  kpis: () => client.get("/kpis").then(r => r.data),
  accounts: () => client.get("/accounts").then(r => r.data),
  account: (id) => client.get(`/accounts/${id}`).then(r => r.data),
  equity: (id, points = 200) => client.get(`/accounts/${id}/equity`, { params: { points } }).then(r => r.data),
  drawdown: (id, points = 200) => client.get(`/accounts/${id}/drawdown`, { params: { points } }).then(r => r.data),
  trades: (id, params = {}) => client.get(`/accounts/${id}/trades`, { params }).then(r => r.data),
  alerts: (params = {}) => client.get("/alerts", { params }).then(r => r.data),
  ackAlert: (id, acknowledged = true) => client.post(`/alerts/${id}/ack`, { acknowledged }).then(r => r.data),
  killSwitch: (id, enabled) => client.post(`/accounts/${id}/kill-switch`, { enabled }).then(r => r.data),
  updateRisk: (id, payload) => client.put(`/accounts/${id}/risk-limits`, payload).then(r => r.data),
  tick: () => client.post("/sim/tick").then(r => r.data),
  systemHealth: () => client.get("/system/health").then(r => r.data),
  systemVersion: () => client.get("/system/version").then(r => r.data),
  getMt5Config: () => client.get("/mt5/config").then(r => r.data),
  saveMt5Config: (payload) => client.put("/mt5/config", payload).then(r => r.data),
  clearMt5Config: () => client.delete("/mt5/config").then(r => r.data),
  // Phase 2 — Sr. Atlas supervision
  supervisionSnapshot: () => client.get("/supervision/snapshot").then(r => r.data),
  atlasReports: (params = {}) => client.get("/atlas/reports", { params }).then(r => r.data),
  postAtlasReport: (payload = {}) => client.post("/atlas/report", payload).then(r => r.data),
};

export const fmt = {
  money: (v, ccy = "USD") => {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    const sign = v < 0 ? "-" : "";
    const abs = Math.abs(v);
    const out = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return `${sign}$${out}`;
  },
  pct: (v, digits = 2) => {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(digits)}%`;
  },
  num: (v, digits = 2) => {
    if (v === null || v === undefined || Number.isNaN(v)) return "—";
    return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  },
  time: (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("en-GB", { hour12: false });
  },
  timeShort: (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleTimeString("en-GB", { hour12: false });
  },
  relative: (iso) => {
    if (!iso) return "—";
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  },
};

export const pnlClass = (v) => (v > 0 ? "cell-pos" : v < 0 ? "cell-neg" : "");

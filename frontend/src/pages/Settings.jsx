import React, { useCallback, useEffect, useState } from "react";
import PageShell from "@/pages/PageShell";
import { api } from "@/lib/api";

/**
 * MT5 Connection settings — managed entirely from the Dashboard.
 * Replaces the old install-time wizard: credentials can be entered and
 * changed here at any time, without reinstalling Atlas.
 */
export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [passwordSet, setPasswordSet] = useState(false);
  const [banner, setBanner] = useState(null); // {type, text}
  const [form, setForm] = useState({
    login: "",
    password: "",
    server: "",
    terminal_path: "",
    bridge_port: 8002,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getMt5Config();
      const c = data.config || {};
      setForm((f) => ({
        ...f,
        login: c.login || "",
        password: "",
        server: c.server || "",
        terminal_path: c.terminal_path || "",
        bridge_port: c.bridge_port || 8002,
      }));
      setPasswordSet(!!c.password_set);
      setStatus(data.status || null);
    } catch (e) {
      setBanner({ type: "error", text: "Could not load configuration from the backend." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setBanner(null);
    try {
      const payload = {
        login: String(form.login).trim(),
        password: form.password, // empty keeps the existing password
        server: String(form.server).trim(),
        terminal_path: String(form.terminal_path).trim(),
        bridge_port: Number(form.bridge_port) || 8002,
      };
      const res = await api.saveMt5Config(payload);
      setStatus(res.status || null);
      setPasswordSet(!!(res.config && res.config.password_set));
      setForm((f) => ({ ...f, password: "" }));
      setBanner({ type: "ok", text: res.message || "MT5 settings saved." });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setBanner({ type: "error", text: detail || "Failed to save settings." });
    } finally {
      setSaving(false);
    }
  };

  const onClear = async () => {
    if (!window.confirm("Clear the saved MT5 connection? Atlas will return to Configuration Mode.")) return;
    setSaving(true);
    setBanner(null);
    try {
      const res = await api.clearMt5Config();
      setStatus(res.status || null);
      setPasswordSet(false);
      setForm({ login: "", password: "", server: "", terminal_path: "", bridge_port: 8002 });
      setBanner({ type: "ok", text: "MT5 connection cleared. Atlas is back in Configuration Mode." });
    } catch (err) {
      setBanner({ type: "error", text: "Failed to clear settings." });
    } finally {
      setSaving(false);
    }
  };

  const state = status?.state || "unconfigured";
  const stateMeta = {
    connected: { label: "Connected", color: "#22C55E", desc: "Atlas is connected to your MetaTrader 5 account." },
    pending_restart: { label: "Applying / Pending restart", color: "#F59E0B", desc: "Settings saved. Atlas is (re)starting its services to connect." },
    unconfigured: { label: "Configuration Mode", color: "#F59E0B", desc: "No MetaTrader 5 account connected yet. Enter your credentials below." },
  }[state] || { label: state, color: "#A1A1AA", desc: "" };

  const inputStyle = {
    width: "100%", padding: "9px 11px", background: "#121212", color: "#F4F4F5",
    border: "1px solid #27272A", borderRadius: 8, fontSize: 13, outline: "none",
  };
  const labelStyle = { display: "block", fontSize: 12, color: "#A1A1AA", marginBottom: 6, marginTop: 14 };

  return (
    <PageShell active="settings" testId="settings-page">
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: "4px 0 2px" }}>MT5 Connection</h1>
        <p style={{ color: "#A1A1AA", fontSize: 13, marginBottom: 18 }}>
          Connect Atlas to your MetaTrader 5 account. You can change these details
          anytime — no reinstall required.
        </p>

        {/* Connection status */}
        <div
          className="panel"
          data-testid="connection-status"
          style={{ padding: 16, marginBottom: 16, border: "1px solid #27272A", borderRadius: 12, background: "#0F0F0F" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: stateMeta.color, display: "inline-block" }} />
            <span data-testid="connection-state" style={{ fontWeight: 600 }}>{stateMeta.label}</span>
            <span className="kbd" style={{ marginLeft: "auto" }}>mode: {status?.mode || "—"}</span>
          </div>
          <p style={{ color: "#A1A1AA", fontSize: 12.5, margin: "10px 0 0" }}>{stateMeta.desc}</p>
          {status?.platform === "preview" && (
            <p style={{ color: "#71717A", fontSize: 11.5, margin: "8px 0 0" }}>
              Note: this is the cloud preview (no local MT5). On the installed Windows app,
              saving connects to MT5 automatically.
            </p>
          )}
        </div>

        {banner && (
          <div
            data-testid="settings-banner"
            style={{
              padding: "10px 14px", borderRadius: 8, marginBottom: 16, fontSize: 13,
              background: banner.type === "error" ? "#3F1D1D" : "#14321F",
              color: banner.type === "error" ? "#FCA5A5" : "#86EFAC",
              border: `1px solid ${banner.type === "error" ? "#7F1D1D" : "#166534"}`,
            }}
          >
            {banner.text}
          </div>
        )}

        {/* Form */}
        <form onSubmit={onSave} className="panel" data-testid="mt5-form" style={{ padding: 18, border: "1px solid #27272A", borderRadius: 12 }}>
          <label style={labelStyle}>MT5 Login (account number)</label>
          <input data-testid="mt5-login" style={inputStyle} value={form.login} onChange={setField("login")} placeholder="e.g. 51234567" inputMode="numeric" />

          <label style={labelStyle}>MT5 Password {passwordSet && <span style={{ color: "#22C55E" }}>· saved (leave blank to keep)</span>}</label>
          <input data-testid="mt5-password" style={inputStyle} type="password" value={form.password} onChange={setField("password")} placeholder={passwordSet ? "••••••••" : "account password"} />

          <label style={labelStyle}>Server / Broker</label>
          <input data-testid="mt5-server" style={inputStyle} value={form.server} onChange={setField("server")} placeholder="e.g. Darwinex-Live" />

          <label style={labelStyle}>Terminal path (optional)</label>
          <input data-testid="mt5-terminal" style={inputStyle} value={form.terminal_path} onChange={setField("terminal_path")} placeholder="C:\\Program Files\\MetaTrader 5\\terminal64.exe" />

          <label style={labelStyle}>Bridge port</label>
          <input data-testid="mt5-port" style={inputStyle} value={form.bridge_port} onChange={setField("bridge_port")} placeholder="8002" inputMode="numeric" />

          <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
            <button type="submit" className="btn success" data-testid="mt5-save" disabled={saving || loading}>
              {saving ? "SAVING…" : "SAVE & CONNECT"}
            </button>
            <button type="button" className="btn" data-testid="mt5-clear" onClick={onClear} disabled={saving || loading}>
              CLEAR
            </button>
          </div>
        </form>
      </div>
    </PageShell>
  );
}

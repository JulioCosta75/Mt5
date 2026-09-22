import React, { useCallback, useEffect, useState } from "react";
import PageShell from "@/pages/PageShell";
import { api } from "@/lib/api";

const LICENSE_STATUS_META = {
  free: { label: "Free", color: "#A1A1AA", desc: "1 MT5 account included." },
  pro_active: { label: "Pro active", color: "#22C55E", desc: "Unlimited MT5 accounts." },
  pro_expired: { label: "Pro expired", color: "#F59E0B", desc: "Back to the free version (1 MT5 account)." },
  checking: { label: "Checking", color: "#60A5FA", desc: "Checking license status…" },
};

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
  const [license, setLicense] = useState(null);
  const [licenseKey, setLicenseKey] = useState("");
  const [activating, setActivating] = useState(false);
  const [licenseBanner, setLicenseBanner] = useState(null); // {type, text}

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [data, lic] = await Promise.all([
        api.getMt5Config(),
        api.getLicense().catch(() => null),
      ]);
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
      if (lic) setLicense(lic);
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
      try {
        const lic = await api.getLicense();
        setLicense(lic);
      } catch {
        /* license panel is independent of MT5 save */
      }
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

  const onActivateLicense = async (e) => {
    e.preventDefault();
    setActivating(true);
    setLicenseBanner(null);
    try {
      const res = await api.activateLicense(licenseKey);
      setLicense(res);
      setLicenseKey("");
      setLicenseBanner({
        type: res.activated ? "ok" : "error",
        text: res.message || (res.activated ? "Pro license active." : "This license key could not be validated."),
      });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setLicenseBanner({
        type: "error",
        text: detail || "Could not reach the license server. Try again in a moment.",
      });
    } finally {
      setActivating(false);
    }
  };

  const state = status?.state || "unconfigured";
  const stateMeta = {
    connected: { label: "Connected", color: "#22C55E", desc: "Atlas is connected to your MetaTrader 5 account." },
    pending_restart: { label: "Applying / Pending restart", color: "#F59E0B", desc: "Settings saved. Atlas is (re)starting its services to connect." },
    unconfigured: { label: "Configuration Mode", color: "#F59E0B", desc: "No MetaTrader 5 account connected yet. Enter your credentials below." },
  }[state] || { label: state, color: "#A1A1AA", desc: "" };

  const licenseStatus = license?.status || "free";
  const licenseMeta = LICENSE_STATUS_META[licenseStatus] || LICENSE_STATUS_META.free;
  const showFreeLimitNotice = Boolean(
    status?.configured && license && !license.pro
  );

  const inputStyle = {
    width: "100%", padding: "9px 11px", background: "#121212", color: "#F4F4F5",
    border: "1px solid #27272A", borderRadius: 8, fontSize: 13, outline: "none",
  };
  const labelStyle = { display: "block", fontSize: 12, color: "#A1A1AA", marginBottom: 6, marginTop: 14 };
  const panelStyle = { padding: 18, marginBottom: 16, border: "1px solid #27272A", borderRadius: 12, background: "#0F0F0F" };

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

        {showFreeLimitNotice && (
          <div
            data-testid="license-limit-notice"
            style={{
              marginTop: 16, padding: "12px 14px", borderRadius: 8, fontSize: 13,
              background: "#1A1A12", color: "#E4E4C8",
              border: "1px solid #3F3F22",
            }}
          >
            The free version includes 1 MT5 account, and this installation is already using it.
            You can keep using this account as usual. To connect more accounts, paste a Pro
            license key in the License section below.
          </div>
        )}

        {/* License */}
        <div
          className="panel"
          data-testid="license-panel"
          style={{ ...panelStyle, marginTop: 24 }}
        >
          <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 6px" }}>License</h2>
          <p style={{ color: "#A1A1AA", fontSize: 13, margin: "0 0 14px" }}>
            Atlas is free for one MetaTrader 5 account. A Pro license unlocks unlimited accounts.
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: licenseMeta.color, display: "inline-block" }} />
            <span data-testid="license-status" style={{ fontWeight: 600 }}>{licenseMeta.label}</span>
            {license?.key_present && (
              <span className="kbd" data-testid="license-key-present" style={{ marginLeft: "auto" }}>key saved</span>
            )}
          </div>
          <p data-testid="license-status-desc" style={{ color: "#A1A1AA", fontSize: 12.5, margin: "0 0 12px" }}>
            {license?.message || licenseMeta.desc}
          </p>

          {licenseBanner && (
            <div
              data-testid="license-banner"
              style={{
                padding: "10px 14px", borderRadius: 8, marginBottom: 14, fontSize: 13,
                background: licenseBanner.type === "error" ? "#3F1D1D" : "#14321F",
                color: licenseBanner.type === "error" ? "#FCA5A5" : "#86EFAC",
                border: `1px solid ${licenseBanner.type === "error" ? "#7F1D1D" : "#166534"}`,
              }}
            >
              {licenseBanner.text}
            </div>
          )}

          <form onSubmit={onActivateLicense}>
            <label style={{ ...labelStyle, marginTop: 0 }}>Pro license key</label>
            <input
              data-testid="license-key-input"
              style={inputStyle}
              type="password"
              autoComplete="off"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder="Paste your Lemon Squeezy license key"
            />
            <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button type="submit" className="btn success" data-testid="license-activate" disabled={activating || loading}>
                {activating ? "ACTIVATING…" : "ACTIVATE"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </PageShell>
  );
}

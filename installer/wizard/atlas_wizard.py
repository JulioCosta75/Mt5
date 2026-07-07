"""Atlas — Setup Wizard.

Runs once after the Inno Setup installer finishes. Walks the user through:

  1. Welcome
  2. Detect MetaTrader 5 installation(s)
  3. MT5 account credentials
  4. Generate bridge token + write .env files
  5. Install / (re)start Windows services
  6. Verify health → open dashboard

Distributed as a single PyInstaller-built Atlas Wizard.exe.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import urllib.error
from pathlib import Path
from tkinter import messagebox, ttk

APP_NAME = "Atlas Setup Wizard"
ATLAS_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent
# When frozen as Atlas\Atlas Wizard.exe, ATLAS_DIR points at C:\Program Files\Atlas
# (one level up from python\ is the install root).
# Heuristic: locate scripts\ relative to the .exe location.
if not (ATLAS_DIR / "scripts").exists():
    # fall back to two levels up (when running from source)
    ATLAS_DIR = Path(sys.executable).resolve().parent

SCRIPTS  = ATLAS_DIR / "scripts"
# Support both layouts:
#   * Production install (Atlas_Setup.exe): ATLAS_DIR\backend, ATLAS_DIR\bridge
#   * Fresh git clone: ATLAS_DIR is the installer\ folder, so the sources live
#     one level up as <repo>\backend and <repo>\mt5-bridge.
if (ATLAS_DIR / "backend").exists():
    ROOT_DIR = ATLAS_DIR
    BACKEND  = ATLAS_DIR / "backend"
    BRIDGE   = ATLAS_DIR / "bridge"
else:
    ROOT_DIR = ATLAS_DIR.parent
    BACKEND  = ROOT_DIR / "backend"
    BRIDGE   = ROOT_DIR / "mt5-bridge"
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

MT5_DEFAULT_PATHS = [
    Path(r"C:\Program Files\MetaTrader 5\terminal64.exe"),
    Path(r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"),
]

# Discover MT5 installations under common locations (broker-branded folders).
def discover_mt5() -> list[Path]:
    found: list[Path] = []
    for base in [Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")]:
        if not base.exists():
            continue
        for child in base.iterdir():
            if not child.is_dir():
                continue
            cand = child / "terminal64.exe"
            if cand.exists():
                found.append(cand)
    # Also scan %APPDATA%\MetaQuotes\Terminal\<hash>\
    mq = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    if mq.exists():
        for child in mq.iterdir():
            cand = child / "terminal64.exe"
            if cand.exists():
                found.append(cand)
    return found


def write_env(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(cmd: list[str] | str, *, shell: bool = False) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=180)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def http_json(url: str, timeout: float = 5.0) -> tuple[int, dict | str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, str(e)
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


# =====================================================================
# UI
# =====================================================================
class WizardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("680x520")
        self.minsize(680, 520)
        self.configure(bg="#0A0A0A")
        self.style = ttk.Style(self)
        self._apply_theme()

        # state
        self.mt5_terminal_path = tk.StringVar()
        self.mt5_login         = tk.StringVar()
        self.mt5_password      = tk.StringVar()
        self.mt5_server        = tk.StringVar()
        self.bridge_port       = tk.StringVar(value="8002")
        self.bridge_token      = tk.StringVar(value=secrets.token_urlsafe(32))
        self.step              = 0

        self.body = tk.Frame(self, bg="#0A0A0A")
        self.body.pack(fill="both", expand=True, padx=24, pady=(20, 8))

        self.nav = tk.Frame(self, bg="#0A0A0A")
        self.nav.pack(fill="x", padx=24, pady=(8, 20))

        self.btn_back = ttk.Button(self.nav, text="← Back",  command=self.back, state="disabled")
        self.btn_next = ttk.Button(self.nav, text="Next →",  command=self.next_, style="Accent.TButton")
        self.btn_back.pack(side="left")
        self.btn_next.pack(side="right")

        self.steps = [self.step_welcome, self.step_detect, self.step_creds,
                      self.step_apply, self.step_verify]
        self.render()

    def _apply_theme(self):
        self.style.theme_use("clam")
        bg, panel, text, dim, accent = "#0A0A0A", "#121212", "#F4F4F5", "#A1A1AA", "#22C55E"
        self.style.configure("TLabel",  background=bg,    foreground=text)
        self.style.configure("Sub.TLabel", background=bg, foreground=dim)
        self.style.configure("TFrame",  background=bg)
        self.style.configure("TEntry",  fieldbackground=panel, foreground=text, bordercolor="#27272A")
        self.style.configure("TCombobox", fieldbackground=panel, foreground=text)
        self.style.configure("TButton", background=panel, foreground=text, padding=(14, 8), borderwidth=1)
        self.style.configure("Accent.TButton", background=accent, foreground="#0A0A0A", padding=(16, 8))
        self.style.map("Accent.TButton", background=[("active", "#16A34A")])

    # ------------------------------------------------------------ render
    def render(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.steps[self.step]()
        self.btn_back.configure(state=("normal" if self.step > 0 else "disabled"))
        last = self.step == len(self.steps) - 1
        self.btn_next.configure(text=("Finish ✓" if last else "Next →"))

    def back(self):
        if self.step > 0:
            self.step -= 1
            self.render()

    def next_(self):
        try:
            ok = self._validate_current()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Error", str(e))
            return
        if not ok:
            return
        if self.step == len(self.steps) - 1:
            self.destroy()
            return
        self.step += 1
        self.render()

    def _validate_current(self) -> bool:
        s = self.step
        if s == 2:  # creds
            if not self.mt5_login.get().strip().isdigit():
                messagebox.showwarning("Invalid login", "MT5 login must be numeric.")
                return False
            if not self.mt5_password.get().strip():
                messagebox.showwarning("Missing password", "Enter your MT5 account password.")
                return False
            if not self.mt5_server.get().strip():
                messagebox.showwarning("Missing server", "Enter your broker server (e.g., Darwinex-Live).")
                return False
        return True

    # ------------------------------------------------------------ pages
    def _title(self, title: str, subtitle: str = ""):
        tk.Label(self.body, text=title, fg="#F4F4F5", bg="#0A0A0A",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(self.body, text=subtitle, fg="#A1A1AA", bg="#0A0A0A",
                     font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 16))
        else:
            tk.Frame(self.body, height=12, bg="#0A0A0A").pack()

    def step_welcome(self):
        self._title("Welcome to Atlas",
                    "MT5 supervision dashboard — installed locally on this Windows host.")
        msg = ("This wizard will:\n\n"
               "  •  Detect your MetaTrader 5 installation\n"
               "  •  Collect your MT5 account credentials (kept locally)\n"
               "  •  Generate a secure bridge token\n"
               "  •  Write the configuration files\n"
               "  •  Start the Atlas services (bridge + backend)\n"
               "  •  Verify the connection and open the dashboard\n\n"
               "Prerequisites:\n"
               "  ✓  MetaTrader 5 installed and logged into your account\n"
               "  ✓  In MT5: Tools → Options → Expert Advisors → \"Allow algorithmic trading\"\n"
               "  ✓  This wizard runs with administrator privileges")
        tk.Label(self.body, text=msg, fg="#F4F4F5", bg="#0A0A0A",
                 font=("Segoe UI", 10), justify="left").pack(anchor="w")

    def step_detect(self):
        self._title("MetaTrader 5 Detection",
                    "Atlas needs the path to your MT5 terminal (terminal64.exe).")
        found = discover_mt5()
        if found:
            tk.Label(self.body, text=f"Detected {len(found)} installation(s):",
                     fg="#22C55E", bg="#0A0A0A", font=("Segoe UI", 10, "bold")).pack(anchor="w")
            cb = ttk.Combobox(self.body, textvariable=self.mt5_terminal_path,
                              values=[str(p) for p in found], width=80)
            cb.current(0)
            cb.pack(anchor="w", pady=(8, 16), fill="x")
        else:
            tk.Label(self.body, text="No MetaTrader 5 installation auto-detected.",
                     fg="#F59E0B", bg="#0A0A0A", font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(self.body, text="Leave empty to let MT5 auto-discover at runtime, or paste the full path.",
                     fg="#A1A1AA", bg="#0A0A0A", font=("Segoe UI", 9)).pack(anchor="w")
            ttk.Entry(self.body, textvariable=self.mt5_terminal_path, width=80).pack(anchor="w", pady=(8, 16), fill="x")

        tk.Label(self.body,
                 text=("Optional. If left blank, the Bridge will try to attach to whichever\n"
                       "MT5 terminal is currently running. Specifying a path forces a specific install."),
                 fg="#A1A1AA", bg="#0A0A0A", font=("Segoe UI", 9), justify="left").pack(anchor="w")

    def step_creds(self):
        self._title("MT5 Account Credentials",
                    "Stored locally in a .env file. Never sent anywhere by Atlas itself.")
        grid = tk.Frame(self.body, bg="#0A0A0A")
        grid.pack(anchor="w", fill="x")
        def row(r, label, var, show=None):
            tk.Label(grid, text=label, fg="#F4F4F5", bg="#0A0A0A",
                     font=("Segoe UI", 10)).grid(row=r, column=0, sticky="w", pady=6, padx=(0, 12))
            e = ttk.Entry(grid, textvariable=var, width=44, show=show)
            e.grid(row=r, column=1, sticky="we", pady=6)
        row(0, "MT5 Login (number)", self.mt5_login)
        row(1, "MT5 Password",       self.mt5_password, show="•")
        row(2, "MT5 Server / Broker", self.mt5_server)
        row(3, "Bridge port",        self.bridge_port)
        tk.Label(grid, text="Bridge token (auto-generated)", fg="#F4F4F5", bg="#0A0A0A",
                 font=("Segoe UI", 10)).grid(row=4, column=0, sticky="w", pady=6, padx=(0, 12))
        tk.Label(grid, textvariable=self.bridge_token, fg="#A1A1AA", bg="#0A0A0A",
                 font=("Consolas", 9), wraplength=420, justify="left").grid(row=4, column=1, sticky="we", pady=6)
        grid.columnconfigure(1, weight=1)

    def step_apply(self):
        self._title("Apply Configuration",
                    "Write .env files and (re)install Windows services.")
        self.log = tk.Text(self.body, bg="#121212", fg="#F4F4F5",
                           insertbackground="#F4F4F5", height=14, borderwidth=1, relief="solid",
                           font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, pady=(0, 8))
        ttk.Button(self.body, text="▶ Apply now", command=self._run_apply).pack(anchor="e")

    def _log(self, msg: str):
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.update_idletasks()

    def _run_apply(self):
        self.log.delete("1.0", "end")
        try:
            self._log("[1/5] Writing bridge .env ...")
            bridge_env = (
                f"MT5_LOGIN={self.mt5_login.get().strip()}\n"
                f"MT5_PASSWORD={self.mt5_password.get()}\n"
                f"MT5_SERVER={self.mt5_server.get().strip()}\n"
                + (f"MT5_TERMINAL_PATH={self.mt5_terminal_path.get().strip()}\n"
                   if self.mt5_terminal_path.get().strip() else "")
                + f"BRIDGE_TOKEN={self.bridge_token.get()}\n"
                f"BRIDGE_HOST=127.0.0.1\n"
                f"BRIDGE_PORT={self.bridge_port.get().strip()}\n"
                f"SNAPSHOT_INTERVAL_SECONDS=10\n"
                f"SQLITE_PATH={DATA_DIR / 'bridge_data.db'}\n"
                f"LOG_LEVEL=INFO\n"
            )
            write_env(BRIDGE / ".env", bridge_env)
            self._log("    OK: " + str(BRIDGE / ".env"))

            self._log("[2/5] Writing backend .env ...")
            backend_env = (
                f"MT5_BRIDGE_URL=http://127.0.0.1:{self.bridge_port.get().strip()}\n"
                f"MT5_BRIDGE_TOKEN={self.bridge_token.get()}\n"
                f"ATLAS_STORE=sqlite\n"
                f"ATLAS_SQLITE_PATH={DATA_DIR / 'atlas.db'}\n"
                f"SERVE_FRONTEND=true\n"
                f"FRONTEND_BUILD={ATLAS_DIR / 'frontend_build'}\n"
                f"CORS_ORIGINS=*\n"
            )
            write_env(BACKEND / ".env", backend_env)
            self._log("    OK: " + str(BACKEND / ".env"))

            DATA_DIR.mkdir(parents=True, exist_ok=True)
            LOGS_DIR.mkdir(parents=True, exist_ok=True)

            self._log("[3/5] (Re)installing services...")
            rc, out = run([str(SCRIPTS / "install_services.bat")], shell=False)
            self._log(out.strip())
            if rc != 0:
                self._log(f"[!] install_services.bat exit code {rc}")
                return

            self._log("[4/5] Starting Atlas Bridge + Backend ...")
            rc, out = run([str(SCRIPTS / "start_atlas.bat")], shell=False)
            self._log(out.strip())

            self._log("[5/5] Waiting up to 20s for services to come up ...")
            for _ in range(20):
                time.sleep(1)
                code, body = http_json("http://127.0.0.1:8001/api/system/health", timeout=2)
                if code == 200 and isinstance(body, dict):
                    self._log("    Backend reachable.")
                    self._log("    " + json.dumps(body, indent=2))
                    break
            else:
                self._log("[!] Backend did not respond in time. Check logs in " + str(LOGS_DIR))
                return

            self._log("\nDone. Click Next → to verify connection.")
        except Exception as e:  # noqa: BLE001
            self._log(f"[ERROR] {e}")

    def step_verify(self):
        self._title("Health Check", "Verifies the Atlas backend and the MT5 bridge connection.")
        self.health = tk.Text(self.body, bg="#121212", fg="#F4F4F5",
                              height=14, borderwidth=1, relief="solid",
                              font=("Consolas", 9))
        self.health.pack(fill="both", expand=True, pady=(0, 8))

        def refresh():
            self.health.delete("1.0", "end")
            self.health.insert("end", "Checking http://127.0.0.1:8001/api/system/health ...\n\n")
            code, body = http_json("http://127.0.0.1:8001/api/system/health", timeout=5)
            if code == 200 and isinstance(body, dict):
                self.health.insert("end", json.dumps(body, indent=2))
                if body.get("mode") == "mt5" and (body.get("bridge") or {}).get("terminal_connected"):
                    self.health.insert("end", "\n\n✓  Atlas is connected to your MT5 terminal.")
                elif body.get("mode") == "mock":
                    self.health.insert("end", "\n\n⚠  Backend running in MOCK mode (MT5_BRIDGE_URL not picked up). Restart services.")
                else:
                    self.health.insert("end", "\n\n⚠  Backend OK, but bridge cannot reach MT5. Check that the terminal is open and 'Allow algorithmic trading' is enabled.")
            else:
                self.health.insert("end", f"Backend unreachable. status={code}\n{body}")

        bar = tk.Frame(self.body, bg="#0A0A0A")
        bar.pack(fill="x")
        ttk.Button(bar, text="↻ Refresh",
                   command=lambda: threading.Thread(target=refresh, daemon=True).start()).pack(side="left")
        ttk.Button(bar, text="Open Dashboard",
                   command=lambda: os.startfile("http://127.0.0.1:8001/")
                   ).pack(side="left", padx=8)
        ttk.Button(bar, text="Open Health Page",
                   command=lambda: os.startfile("http://127.0.0.1:8001/healthcheck")
                   ).pack(side="left")
        threading.Thread(target=refresh, daemon=True).start()


if __name__ == "__main__":
    WizardApp().mainloop()

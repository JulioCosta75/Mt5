# Atlas — Installer build kit

This folder contains everything needed to produce **`Atlas_Setup.exe`**, the
single-file Windows installer for Atlas (MT5 Supervisor).

The installer bundles:
- Embedded **Python 3.11** runtime (no need to install Python on the VPS)
- Atlas **backend** (FastAPI) + pre-built **React frontend**
- **MT5 Bridge** (the `MetaTrader5` Python lib lives here)
- **NSSM** for Windows service management
- A **Tkinter setup wizard** (`Atlas Wizard.exe`) that collects MT5 credentials
  on first run, writes `.env` files and starts the services

---

## 1. One-time prerequisites on your **build** machine (Windows 10/11)

You only need these once, where the installer is **compiled** (not where it is installed):

| Tool | Why | Where |
|------|-----|-------|
| **Inno Setup 6** | Compiles `.iss` → `.exe` | **auto-installed by `build.bat`** if missing (see note) |
| **Node.js LTS + yarn** (or npm) | Builds the React frontend | https://nodejs.org |
| PowerShell 5+ | Downloads payload deps + Inno Setup | already in Windows |

**Inno Setup is now automatic.** `build.bat` detects `ISCC.exe`; if it is not found it
installs Inno Setup 6 for you — first via `winget install -e --id JRSoftware.InnoSetup`
(if winget is present), otherwise by downloading the official installer from
`https://jrsoftware.org/download.php/is.exe` and running it silently
(`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-`). No PATH setup is required.

If you prefer to install it manually (or the machine has no internet), download from
https://jrsoftware.org/isdl.php and install; `build.bat` will find it at the default
path `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`. You can also point the build at a
specific copy with `set ISCC=C:\path\to\ISCC.exe` before running `build.bat`.

> Note: the PyInstaller wizard step was removed — MT5 is now configured from the
> Dashboard, so Python 3.11 is no longer required on the build machine.

---

## 2. Build the installer (one command)

From a Windows shell, inside `installer\`:

```cmd
build.bat
```

The script:
1. Downloads **Python 3.11.9 embeddable** zip → unpacks to `payload\python\`
2. Downloads **NSSM 2.24** → extracts `nssm.exe` to `payload\`
3. Copies `..\backend\` and `..\mt5-bridge\` into `payload\` (excluding `__pycache__`, `tests/`, user `.env`)
4. Runs `yarn build` on the React frontend → copies `build/` into `payload\frontend_build\`
5. Runs **PyInstaller** on `wizard\atlas_wizard.py` → produces `payload\wizard\Atlas Wizard.exe`
6. Invokes **ISCC.exe** with `atlas_setup.iss` → outputs **`dist\Atlas_Setup.exe`**

Total build time (cold): ~3-5 minutes. Subsequent rebuilds reuse cached
downloads (~30 s).

---

## 3. Deploy to a Windows VPS

Once you have `Atlas_Setup.exe`:

1. Copy it to the VPS (RDP file transfer, OneDrive, etc.).
2. Right-click → **Run as administrator**.
3. Click through:
   - Welcome → License → choose install folder (default: `C:\Program Files\Atlas`)
   - Tasks: ☑ desktop icon, ☑ start menu, ☑ install services, ☑ open browser
   - Inno Setup will install all files, then automatically:
     - bootstrap pip into the embedded Python
     - install backend + bridge Python dependencies
     - register `AtlasBridge` and `AtlasBackend` Windows services
     - launch the **Atlas Setup Wizard**
4. In the Wizard:
   - Page 1: Welcome
   - Page 2: confirms detected MT5 path (or leave blank for auto-attach)
   - Page 3: enter **MT5 login, password, server name**
   - Page 4: click **Apply Now** — writes `.env` files, starts services
   - Page 5: shows live health-check → click **Open Dashboard**

5. Dashboard is at `http://localhost:8001/`. Health page at `http://localhost:8001/healthcheck`.

If you want to access the dashboard from outside the VPS, open port 8001 in
the Windows Firewall and bind the backend to `0.0.0.0` instead of `127.0.0.1`
in `scripts\install_services.bat`. (Default is loopback-only for safety.)

---

## 4. Folder layout produced on the target VPS

```
C:\Program Files\Atlas\
├── python\                  ← embedded Python 3.11
├── backend\                 ← FastAPI app (with .env after wizard)
├── bridge\                  ← MT5 bridge (with .env after wizard)
├── frontend_build\          ← pre-built React static files
├── data\
│   ├── atlas.db             ← SQLite cache + overrides
│   └── bridge_data.db       ← SQLite equity snapshots
├── logs\
│   ├── backend.out.log / .err.log
│   └── bridge.out.log  / .err.log
├── scripts\                 ← .bat operations
├── icons\
├── nssm.exe
├── Atlas Wizard.exe
└── unins000.exe             ← Inno Setup uninstaller
```

---

## 5. Services

Both registered with `Start = SERVICE_AUTO_START`:

| Name | Display | Depends on | Listens |
|------|---------|------------|---------|
| `AtlasBridge`  | Atlas MT5 Bridge | — | 127.0.0.1:8002 |
| `AtlasBackend` | Atlas Backend    | AtlasBridge | 127.0.0.1:8001 |

Manage with standard tools:
```cmd
net start  AtlasBackend
net stop   AtlasBridge
sc query   AtlasBackend
```
Or use the bundled scripts:
- `scripts\start_atlas.bat`
- `scripts\stop_atlas.bat`
- `scripts\healthcheck.bat` (opens the browser to the health page)

---

## 6. Rebuilding only the frontend / wizard

Delete the relevant folder and rerun `build.bat`:

```cmd
rmdir /S /Q payload\frontend_build
rmdir /S /Q payload\wizard
build.bat
```

The Python download is cached as long as `payload\python\python.exe` exists.

---

## 7. Uninstall

Add/Remove Programs → **Atlas** → Uninstall.

Removes both services, deletes `data\` and `logs\` (purges all local state).

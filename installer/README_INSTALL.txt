Atlas — MT5 Supervisor
======================

This installer has placed Atlas under the folder you selected
(default: C:\Program Files\Atlas).

Quick start
-----------
1. The Setup Wizard should open automatically. If it didn't, run:
       <install folder>\Atlas Wizard.exe
2. Follow the 5 pages: Welcome → MT5 detection → Credentials → Apply → Verify.
3. When the health check shows "connected", click "Open Dashboard".

What got installed
------------------
• Two Windows services that auto-start with Windows:
    AtlasBridge   — talks to MT5 via the MetaTrader5 Python lib (port 8002)
    AtlasBackend  — API + dashboard server (port 8001)

• Start menu entries under "Atlas":
    Atlas Dashboard           open the dashboard
    Atlas Wizard              re-run the setup wizard
    Atlas Health Check        opens the diagnostics page
    Start Atlas / Stop Atlas  service control

URLs
----
Dashboard:    http://localhost:8001/
Health page:  http://localhost:8001/healthcheck
API root:     http://localhost:8001/api/

Checking which version is running
---------------------------------
The running build is shown in two places, so you can always confirm an
install/upgrade actually took effect:
  • Dashboard header (top-right), e.g.  v0.3.0
  • Health page footer  (http://localhost:8001/healthcheck)
  • API:  http://localhost:8001/api/system/version

Upgrading to a new version
--------------------------
Atlas upgrades are clean and reproducible — no manual commands:
  1. Run the new Atlas_Setup.exe (or first uninstall via Add/Remove Programs).
  2. The installer automatically STOPS both Atlas services, REPLACES all old
     program files and Python packages, re-registers the services and STARTS
     the new build. Your data (\data) and logs (\logs) are preserved.
  3. Open the Dashboard and confirm the version number in the header changed.

Logs
----
<install folder>\logs\backend.out.log
<install folder>\logs\backend.err.log
<install folder>\logs\bridge.out.log
<install folder>\logs\bridge.err.log

Data
----
SQLite databases are kept under <install folder>\data\
You can back up this folder to preserve overrides and equity snapshots.

Troubleshooting
---------------
1. Dashboard not loading?
     - Run "Atlas Health Check" from the Start menu.
     - If Backend = unreachable, run "Start Atlas".

2. Health page says "Mode = mock"?
     - The wizard didn't write the backend .env, or services started before it.
     - Run "Atlas Wizard" again and click "Apply Now".

3. Bridge "unreachable"?
     - Ensure MetaTrader 5 is open and the account is logged in.
     - Ensure "Allow algorithmic trading" is enabled
       (MT5 Tools → Options → Expert Advisors).
     - Check <install folder>\logs\bridge.err.log for the exact error code.

4. Want remote access?
     - By default, both services listen on 127.0.0.1 only.
     - To expose the dashboard on the LAN/internet, edit
       <install folder>\scripts\install_services.bat:
       change "--host 127.0.0.1" to "--host 0.0.0.0", then re-run that script
       as administrator.
     - Open inbound TCP 8001 in the Windows Firewall.

Support
-------
Atlas is provided as-is. See LICENSE.txt.

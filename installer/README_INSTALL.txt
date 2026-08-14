Atlas — MT5 Supervisor
======================

This installer places Atlas under your user profile:

    %LOCALAPPDATA%\Atlas
    (typically C:\Users\<you>\AppData\Local\Atlas)

No Administrator rights are required. Atlas runs as a normal tray
application (system tray icon), not as a Windows service.

Quick start
-----------
1. During setup you were asked for your MetaTrader 5 account
   (Login / Password / Server, and optionally the terminal path).
   Those details were written to the local .env files.
2. Atlas starts as a tray app. Look for the Atlas icon near the clock.
   Right-click: Open Dashboard / Restart Atlas / Quit Atlas.
3. The dashboard is at http://127.0.0.1:8001/
4. To change your MT5 account later, use the dashboard Settings page
   ("Save & Connect") — Atlas restarts itself automatically.
   Or re-run:
       <install folder>\scripts\configure_mt5.bat
       <install folder>\scripts\stop_atlas.bat
       <install folder>\scripts\start_atlas_app.bat

Optional: start when you sign in to Windows
-------------------------------------------
If you ticked "Start Atlas when I sign in to Windows" during setup,
a shortcut was added to your Startup folder. You can remove it any
time from that folder or by reinstalling without the option.

What got installed
------------------
• Tray launcher that starts:
    Bridge  — talks to MT5 (port 8002)
    Backend — API + dashboard (port 8001)

• Start menu / desktop shortcuts (if selected):
    Atlas                 start the tray app
    Atlas Dashboard       open http://127.0.0.1:8001/
    Atlas Health Check    diagnostics page
    Stop Atlas            quit the tray app and children

URLs
----
Dashboard:    http://127.0.0.1:8001/
Health page:  http://127.0.0.1:8001/healthcheck
API root:     http://127.0.0.1:8001/api/

Checking which version is running
---------------------------------
  • Dashboard header (top-right), e.g.  v0.3.0
  • Health page footer
  • API:  http://127.0.0.1:8001/api/system/version

Upgrading
---------
  1. Run the new Atlas_Setup.exe (no Administrator needed).
  2. The installer stops any running Atlas processes, replaces program
     files, and starts the tray app again. Your data (\data) and logs
     (\logs) are preserved.
  3. Confirm the version in the dashboard header.

  If you previously installed under Program Files with Windows services,
  uninstall that old copy (or let the new installer stop those legacy
  services) so only the LocalAppData install remains.

Logs
----
<install folder>\logs\backend.out.log
<install folder>\logs\backend.err.log
<install folder>\logs\bridge.out.log
<install folder>\logs\bridge.err.log
<install folder>\logs\launcher.log

Data
----
SQLite databases are kept under <install folder>\data\

Troubleshooting
---------------
1. Dashboard not loading?
     - Confirm the Atlas tray icon is present.
     - Run "Atlas" / start_atlas_app.bat from the Start menu.
     - Run "Atlas Health Check".

2. Health page says "Mode = mock"?
     - Configure MT5 from Settings → Save & Connect, or run
       scripts\configure_mt5.bat then start_atlas_app.bat again.

3. Upgrading from an old "Windows Services" install?
     - Prefer uninstalling the old Program Files copy first.
     - If the installer detects AtlasBackend / AtlasBridge still registered,
       it will explain and ask before requesting Windows administrator
       permission — only to remove those old services. You can decline;
       the per-user install still completes, but you should then remove
       the old Program Files Atlas from Windows Settings → Apps so ports
       8001/8002 are free.

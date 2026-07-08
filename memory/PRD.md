# PRD — Forge Factory Lab / Sr. Atlas

## Problem statement (Phase 1 Final Integration)
Finalize Phase 1 of the Forge Factory Lab MT5 supervision system: resolve the Git
unrelated‑histories issue, integrate official Sr. Atlas + Forge Factory Lab
branding across the app, preserve the institutional dark trading terminal, keep
all health checks operational, update docs, and prepare for Phase 2.

## Brand hierarchy
- **Forge Factory Lab** — company / laboratory / engineering environment.
- **Sr. Atlas** — AI supervisor / orchestration system / dashboard identity.

## Architecture
- Frontend: React 19 institutional dark terminal (Dashboard, About, Documentation) + welcome/loading boot splash.
- Backend: FastAPI `/api/*`, mock + live (MT5 bridge) modes, MongoDB/SQLite cache & overrides.
- MT5 Bridge: Windows-side MetaTrader5 service. Installer under `installer/`.
- Supervision: n8n `Forge Factory Lab — Sr. Atlas Health Monitor` workflow (14 nodes).

## Implemented (2026-07-05)
- Imported full `main` project into workspace; added Phase 1 n8n workflow files.
- Branding system under `frontend/src/assets/branding/` (swappable, one source module):
  - `sr-atlas/logo-round.png` (official) → favicon, app icon, header badge, boot, About card.
  - `forge-factory/logo.png` (official) → boot/welcome/loading, About hero + card, Docs hero.
- Dashboard header rebranded QUANT.SUPERVISE → **Sr. Atlas** emblem + wordmark; nav + About/Docs links; footer rebranded.
- New: BrandBoot welcome/loading splash, About page, Documentation page, PageShell nav.
- Favicon + tab title + meta updated (`public/index.html`, `public/favicon.png`).
- Standalone `/healthcheck` page rebranded to Sr. Atlas / Forge Factory Lab.
- README rewritten (architecture, install, branding, workflow, Phase 1, Phase 2 roadmap, Git runbook).
- Verified: `/api/system/health` 200, `/` + `/api/` ok, `/healthcheck` 200, n8n JSON valid (14 nodes).

## Health checks (all operational)
- Atlas Backend Health — `GET /api/system/health`
- Atlas Dashboard Health — `GET /` / `GET /api/`
- MT5 Bridge Health — `GET /health` (`:8002`, live only; `n/a` in mock preview)

## Open items / backlog
- P1: Distinct **Sr. Atlas horizontal header logo** file not received as a separate asset;
  header currently uses the official round emblem + "Sr. Atlas" wordmark. Trivial swap when provided
  (`sr-atlas/logo-horizontal.*` + update `assets/branding/index.js`).
- P1: Git remote history consolidation + delete `conflict_050726_1612` — runbook in README;
  push via Emergent "Save to GitHub".
- P2: Phase 2 features (Telegram alerts, MT5 telemetry probes, Sr. Atlas AI analysis, closed-loop control).

## Notes
- No authentication in this project (no credentials to store).
- Backend runs in MOCK data mode in preview (set `MT5_BRIDGE_URL` for live MT5).

## Update (2026-07-07) — Commercial installer + Dashboard-managed MT5
Goal: Atlas must behave like commercial Windows software. Zero-input install; every
install/upgrade is a clean, reproducible deployment; the running build is visible in
the app; MT5 is configured from the Dashboard (no reinstall).

Delivered & verified:
- Running-build visibility: backend GET /api/system/version + version/build in
  /api/system/health (source: env ATLAS_VERSION > backend/build_info.json > backend/VERSION).
  Dashboard header shows live version (v0.3.0); /healthcheck footer too. (backend+frontend tested)
- Windows installer hardening (installer/atlas_setup.iss, build.bat) — files only, built on
  Windows (cannot compile/run in Linux env):
    * PrepareToInstall stops+removes AtlasBackend/AtlasBridge and kills bundled python BEFORE
      files are touched (releases locks) → fixes "old version keeps running".
    * [InstallDelete] wipes backend/bridge/frontend_build/site-packages → clean deploy;
      data/ and logs/ preserved. CloseApplications=yes. Services auto-start post-install.
    * build.bat stamps build_info.json (version+UTC+git sha), always clean-rebuilds the
      frontend, passes version to ISCC. PyInstaller wizard removed (build is simpler/robust).
    * Zero-input: no MT5 prompt at install; dashboard opens automatically in Configuration Mode.
- MT5 configured from Dashboard: backend mt5_config.py + GET/PUT/DELETE /api/mt5/config
  (password never echoed; login numeric; port validated; JSON persisted to data/mt5_config.json;
  on Windows also writes bridge/.env + backend/.env and restarts services via
  scripts/apply_restart.bat). Frontend /settings page (Settings nav) + Dashboard
  "Configuration Mode" banner. (backend 9/9 + frontend 16/16 tested)

Open/notes:
- Windows installer itself must be built+validated by the user on Windows (no ISCC/MT5 in preview).
- Live MT5 connection (mt5 mode, bridge restart) only exercised on the Windows install.

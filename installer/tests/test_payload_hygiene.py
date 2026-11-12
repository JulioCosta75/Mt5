"""Linux-side check of what the Windows installer is allowed to ship.

Mirrors installer/build.bat robocopy exclusions. Does not invoke Inno Setup.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "installer"
BACKEND = ROOT / "backend"
BRIDGE = ROOT / "mt5-bridge"
FRONTEND_SRC = ROOT / "frontend" / "src"

SKIP_DIR_NAMES = {".venv", "__pycache__", ".pytest_cache", "tests", "data", ".git"}
SKIP_FILE_SUFFIXES = {".db", ".pyc"}
SKIP_FILE_NAMES = {".env", ".installed"}
SECRET_NEEDLES = (
    "sk_live_",
    "sk_test_",
    "LEMON_SQUEEZY_API_KEY",
    "LEMONSQUEEZY_API_KEY",
    "TELEGRAM_BOT_TOKEN=",
    "OPENAI_API_KEY=",
)


def _stage_tree(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        if path.is_dir():
            continue
        if path.name in SKIP_FILE_NAMES or path.suffix in SKIP_FILE_SUFFIXES:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def test_staged_backend_includes_license_and_excludes_secrets(tmp_path):
    staged = tmp_path / "payload"
    _stage_tree(BACKEND, staged / "backend")
    _stage_tree(BRIDGE, staged / "bridge")

    assert (staged / "backend" / "license.py").is_file()
    assert (staged / "backend" / "server.py").is_file()
    assert (staged / "backend" / "VERSION").is_file()
    assert (staged / "bridge" / "bridge_server.py").is_file()

    assert not (staged / "backend" / "tests").exists()
    assert not (staged / "backend" / "data").exists()
    assert not list(staged.rglob(".env"))
    assert not list(staged.rglob("*.db"))

    names = {p.name for p in staged.rglob("*") if p.is_file()}
    assert ".env" not in names
    assert "phase3_knowledge_engine" not in {p.name for p in staged.rglob("*")}
    assert not (staged / "notifications").exists()
    assert not (staged / "education").exists()
    assert not (staged / "ai_usage").exists()


def test_payload_trees_do_not_embed_live_secrets(tmp_path):
    staged = tmp_path / "payload"
    _stage_tree(BACKEND, staged / "backend")
    _stage_tree(BRIDGE, staged / "bridge")
    for path in staged.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".json", ".txt", ".md", ".bat", ".iss", ".env"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in SECRET_NEEDLES:
            assert needle not in text, f"{needle} found in staged {path.relative_to(staged)}"


def test_installer_scripts_do_not_embed_live_secrets():
    for path in INSTALLER.rglob("*"):
        if not path.is_file():
            continue
        if "tests" in path.parts:
            continue
        if path.suffix.lower() not in {".py", ".bat", ".iss", ".txt", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in SECRET_NEEDLES:
            assert needle not in text, f"{needle} found in {path.relative_to(ROOT)}"


def test_atlas2_dashboard_sources_are_present_for_frontend_build():
    risk = (FRONTEND_SRC / "components" / "riskMetrics.js").read_text(encoding="utf-8")
    settings = (FRONTEND_SRC / "pages" / "Settings.jsx").read_text(encoding="utf-8")
    assert "export function drawdownBarPct" in risk
    assert 'data-testid="license-panel"' in settings
    assert "activateLicense" in settings

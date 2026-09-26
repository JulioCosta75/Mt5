"""Regression: Inno [Run] must not open a second dashboard tab."""

from __future__ import annotations

from pathlib import Path

ISS = Path(__file__).resolve().parents[1] / "atlas_setup.iss"
ISS_TEXT = ISS.read_text(encoding="utf-8")


def _section(name: str) -> list[str]:
    lines: list[str] = []
    in_section = False
    header = f"[{name}]"
    for raw in ISS_TEXT.splitlines():
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == header
            continue
        if in_section:
            lines.append(raw)
    return lines


def _run_filenames() -> list[str]:
    names: list[str] = []
    for line in _section("Run"):
        stripped = line.strip()
        if stripped.startswith("Filename:"):
            names.append(stripped)
    return names


def _directive_names(section: str, prefix: str) -> list[str]:
    out: list[str] = []
    for line in _section(section):
        stripped = line.strip()
        if stripped.startswith(prefix):
            out.append(stripped)
    return out


def test_run_section_does_not_open_dashboard_bat():
    filenames = _run_filenames()
    assert filenames, "expected [Run] Filename entries"
    assert any("start_atlas_app.bat" in item for item in filenames)
    assert not any("open_dashboard.bat" in item for item in filenames)


def test_open_dashboard_bat_still_ships_for_start_menu():
    files = "\n".join(_section("Files"))
    icons = "\n".join(_section("Icons"))
    assert "scripts\\open_dashboard.bat" in files
    assert "open_dashboard.bat" in icons


def test_single_unsigned_setup_exe():
    assert "OutputBaseFilename=Atlas_Setup" in ISS_TEXT
    assert "OutputBaseFilename=Atlas_Setup_Free" not in ISS_TEXT
    assert "OutputBaseFilename=Atlas_Setup_Pro" not in ISS_TEXT
    assert ISS_TEXT.lower().count("outputbasefilename=") == 1
    assert "SignTool" not in ISS_TEXT


def test_packages_atlas2_frontend_and_backend():
    files = "\n".join(_section("Files"))
    assert "payload\\frontend_build\\*" in files
    assert "payload\\backend\\*" in files
    assert "payload\\bridge\\*" in files


def test_upgrade_cleans_code_but_not_user_data():
    install_delete = "\n".join(_section("InstallDelete"))
    assert "{app}\\backend" in install_delete
    assert "{app}\\frontend_build" in install_delete
    assert "{app}\\data" not in install_delete
    assert "{app}\\logs" not in install_delete


def test_uninstall_preserves_user_data_and_logs():
    names = _directive_names("UninstallDelete", "Name:")
    blob = "\n".join(names)
    assert "{app}\\data" not in blob
    assert "{app}\\logs" not in blob
    assert any("{app}\\python\\Lib\\site-packages" in item for item in names)


def test_install_creates_data_and_logs_dirs():
    dirs = "\n".join(_section("Dirs"))
    assert "{app}\\data" in dirs
    assert "{app}\\logs" in dirs

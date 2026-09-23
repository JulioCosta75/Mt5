"""Regression: Inno [Run] must not open a second dashboard tab."""

from __future__ import annotations

from pathlib import Path

ISS = Path(__file__).resolve().parents[1] / "atlas_setup.iss"


def _section(name: str) -> list[str]:
    text = ISS.read_text(encoding="utf-8")
    lines: list[str] = []
    in_section = False
    header = f"[{name}]"
    for raw in text.splitlines():
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

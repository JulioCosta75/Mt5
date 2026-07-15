"""Installer lock-release script contract tests (static analysis)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_BAT = REPO_ROOT / "installer" / "scripts" / "release_atlas_locks.bat"
APPLY_RESTART = REPO_ROOT / "installer" / "scripts" / "apply_restart.bat"
DIAGNOSE_PS1 = REPO_ROOT / "installer" / "scripts" / "diagnose_atlas_locks.ps1"


class TestReleaseAtlasLocksScript:
    def test_kills_cmd_wrappers_with_atlas_command_line(self):
        text = RELEASE_BAT.read_text(encoding="utf-8")
        assert "apply_restart" in text
        assert "release_atlas_locks" in text
        assert "CommandLine" in text

    def test_kills_port_listeners(self):
        text = RELEASE_BAT.read_text(encoding="utf-8")
        assert "8001" in text
        assert "8002" in text
        assert "Get-NetTCPConnection" in text

    def test_verifies_backend_lock_probe(self):
        text = RELEASE_BAT.read_text(encoding="utf-8")
        assert ".atlas_lock_probe" in text

    def test_apply_restart_changes_working_directory_to_scripts(self):
        text = APPLY_RESTART.read_text(encoding="utf-8")
        assert 'cd /d "%~dp0"' in text

    def test_diagnose_script_exists(self):
        assert DIAGNOSE_PS1.exists()
        text = DIAGNOSE_PS1.read_text(encoding="utf-8")
        assert "Rename probe" in text
        assert "handle.exe" in text


class TestMt5ConfigRestartSpawn:
    def test_restart_services_uses_scripts_cwd_not_backend(self, monkeypatch, tmp_path):
        import backend.mt5_config as mc

        scripts = tmp_path / "scripts"
        scripts.mkdir()
        restart_bat = scripts / "apply_restart.bat"
        restart_bat.write_text("@echo off\n", encoding="utf-8")

        captured = {}

        class FakePopen:
            def __init__(self, args, **kwargs):
                captured["args"] = args
                captured["kwargs"] = kwargs

        monkeypatch.setattr(mc, "INSTALL_ROOT", tmp_path)
        monkeypatch.setattr(mc.subprocess, "Popen", FakePopen)

        mc._restart_services()

        assert captured["kwargs"]["cwd"] == str(scripts)
        assert "start" not in captured["args"]

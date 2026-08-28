"""Unit tests — Phase 2 parts 1+2: per-account report persistence + retention.

Does not require a running server or MT5 bridge. Uses temp SQLite files.
"""
from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from atlas_store import AtlasReportStore, scrub_secrets
from mt5_cache_sqlite import MT5CacheSQLite


def _run(coro):
    return asyncio.run(coro)


def _report(account_id: str, *, created_at: str | None = None, **extra) -> dict:
    doc = {
        "account_id": account_id,
        "login": 12345678,
        "server": "Demo-Server",
        "currency": "USD",
        "status": "OK",
        "source": "auto",
        "message": f"Account snapshot for {account_id}",
        "backend_ok": True,
        "bridge_ok": True,
        "dashboard_ok": True,
        "data_origin": "live",
        "metrics": {"equity": 10000.0, "daily_pnl": 12.5},
    }
    if created_at:
        doc["created_at"] = created_at
    doc.update(extra)
    return doc


class TestScrubSecrets:
    def test_strips_password_and_token_keys(self):
        raw = {
            "login": 1,
            "password": "secret-pass",
            "bridge_token": "abc",
            "nested": {"api_key": "k", "equity": 1.0},
            "list": [{"connection_string": "x", "ok": True}],
        }
        clean = scrub_secrets(raw)
        assert "password" not in clean
        assert "bridge_token" not in clean
        assert clean["nested"] == {"equity": 1.0}
        assert clean["list"] == [{"ok": True}]
        assert clean["login"] == 1


class TestSqliteAtlasReports:
    def test_persists_and_survives_reopen(self, tmp_path: Path):
        db = tmp_path / "atlas.db"
        store = AtlasReportStore(sqlite_path=db)
        assert store.backend == "sqlite"
        saved = _run(store.add(_report("MT5-111")))
        assert saved["account_id"] == "MT5-111"
        assert "id" in saved and "created_at" in saved

        # Re-open on the same file — persistence across "restart".
        store2 = AtlasReportStore(sqlite_path=db)
        rows = _run(store2.list(limit=10))
        assert len(rows) == 1
        assert rows[0]["id"] == saved["id"]
        assert rows[0]["account_id"] == "MT5-111"

    def test_requires_account_id(self, tmp_path: Path):
        store = AtlasReportStore(sqlite_path=tmp_path / "atlas.db")
        with pytest.raises(ValueError, match="account_id"):
            _run(store.add({"status": "OK", "source": "auto"}))

    def test_filter_by_account_id(self, tmp_path: Path):
        store = AtlasReportStore(sqlite_path=tmp_path / "atlas.db")
        _run(store.add(_report("MT5-A")))
        _run(store.add(_report("MT5-B")))
        _run(store.add(_report("MT5-A", source="manual")))
        only_a = _run(store.list(account_id="MT5-A"))
        assert len(only_a) == 2
        assert all(r["account_id"] == "MT5-A" for r in only_a)
        assert _run(store.count(account_id="MT5-B")) == 1

    def test_purge_older_than_retention_days(self, tmp_path: Path):
        store = AtlasReportStore(sqlite_path=tmp_path / "atlas.db")
        old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        recent = datetime.now(timezone.utc).isoformat()
        _run(store.add(_report("MT5-1", created_at=old, message="old")))
        _run(store.add(_report("MT5-1", created_at=recent, message="new")))
        deleted = _run(store.purge_older_than(90))
        assert deleted == 1
        left = _run(store.list())
        assert len(left) == 1
        assert left[0]["message"] == "new"

    def test_migration_does_not_destroy_existing_mt5_cache_tables(self, tmp_path: Path):
        db = tmp_path / "atlas.db"
        # Pre-create the legacy MT5 cache schema (existing install).
        cache = MT5CacheSQLite(str(db))
        _run(cache.put("account:42", {"login": 42, "equity": 1.0}))

        # Opening AtlasReportStore must ADD atlas_reports without dropping cache.
        store = AtlasReportStore(sqlite_path=db)
        _run(store.add(_report("MT5-42")))

        with sqlite3.connect(str(db)) as cx:
            tables = {
                r[0]
                for r in cx.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "mt5_cache" in tables
        assert "mt5_overrides" in tables
        assert "atlas_reports" in tables
        assert "atlas_alerts" in tables

        # Cache row still readable.
        doc = _run(cache.get("account:42"))
        assert doc is not None
        assert doc["payload"]["login"] == 42
        assert _run(store.count()) == 1

    def test_add_scrubs_secrets_from_payload(self, tmp_path: Path):
        store = AtlasReportStore(sqlite_path=tmp_path / "atlas.db")
        saved = _run(
            store.add(
                _report(
                    "MT5-9",
                    password="should-not-persist",
                    metrics={"equity": 1.0, "token": "x"},
                )
            )
        )
        assert "password" not in saved
        assert "token" not in saved.get("metrics", {})
        # And not in the raw SQLite blob either.
        with sqlite3.connect(str(tmp_path / "atlas.db")) as cx:
            blob = cx.execute("SELECT payload FROM atlas_reports").fetchone()[0]
        assert "should-not-persist" not in blob
        assert '"token"' not in blob


class TestMemoryAndLatest:
    def test_memory_backend_and_latest_for_account(self):
        store = AtlasReportStore()
        assert store.backend == "memory"
        _run(store.add(_report("ACC-1", message="first")))
        newer = _run(store.add(_report("ACC-1", message="second")))
        _run(store.add(_report("ACC-2", message="other")))
        latest = _run(store.latest_for_account("ACC-1"))
        assert latest is not None
        assert latest["id"] == newer["id"]
        assert latest["message"] == "second"


class TestInstallerEnvDefaults:
    def test_launcher_sets_snapshot_interval_1800(self, tmp_path: Path, monkeypatch):
        import sys

        scripts = Path(__file__).resolve().parents[2] / "installer" / "scripts"
        sys.path.insert(0, str(scripts))
        import atlas_launcher as al  # noqa: E402

        root = tmp_path / "Atlas"
        (root / "backend").mkdir(parents=True)
        (root / "bridge").mkdir(parents=True)
        (root / "backend" / "server.py").write_text("#\n", encoding="utf-8")
        (root / "bridge" / "bridge_server.py").write_text("#\n", encoding="utf-8")
        (root / "data").mkdir()
        (root / "logs").mkdir()
        monkeypatch.delenv("ATLAS_AUTO_SNAPSHOT_INTERVAL_SEC", raising=False)
        monkeypatch.delenv("ATLAS_REPORT_RETENTION_DAYS", raising=False)
        paths = al.resolve_paths(str(root))
        paths = al.AtlasPaths(
            root=paths.root,
            backend=paths.backend,
            bridge=paths.bridge,
            frontend_build=paths.frontend_build,
            data=paths.data,
            logs=paths.logs,
            python=Path(sys.executable),
            icon=paths.icon,
        )
        launcher = al.Launcher(paths, open_browser=False)
        children = launcher.build_children()
        backend_env = children[1].spec.env
        assert backend_env["ATLAS_STORE"] == "sqlite"
        assert backend_env["ATLAS_AUTO_SNAPSHOT_INTERVAL_SEC"] == "1800"
        assert backend_env["ATLAS_REPORT_RETENTION_DAYS"] == "90"

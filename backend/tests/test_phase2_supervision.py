"""Phase 2 backend tests: Sr. Atlas supervision snapshot + report persistence.

Runs against the running backend (REACT_APP_BACKEND_URL, falling back to the
preview URL). Locally, export REACT_APP_BACKEND_URL=http://localhost:8001.

Covers:
  * GET  /api/supervision/snapshot
  * POST /api/atlas/report
  * GET  /api/atlas/reports
While leaving all Phase 1 behaviour untouched.
"""
import os

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://inno-setup-fix.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

VALID_STATUS = {"OK", "WARNING", "ALERT"}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestSupervisionSnapshot:
    def test_snapshot_shape(self, session):
        r = session.get(f"{API}/supervision/snapshot", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["supervisor"] == "Sr. Atlas"
        assert d["ecosystem"] == "Forge Factory Lab"
        assert d["status"] in VALID_STATUS
        assert d["mode"] in ("mock", "mt5")
        assert "generated_at" in d

    def test_snapshot_sections(self, session):
        d = session.get(f"{API}/supervision/snapshot", timeout=15).json()
        for section in ("kpis", "accounts", "risk", "alerts", "services"):
            assert section in d, f"missing section {section}"
        for k in ("total_equity", "total_balance", "daily_pnl", "open_positions"):
            assert k in d["kpis"]
        for k in ("total", "live", "paused", "error"):
            assert k in d["accounts"]
        for k in ("active", "critical", "warning"):
            assert k in d["alerts"]
        for k in ("backend_ok", "store_ok", "bridge_ok", "dashboard_ok"):
            assert k in d["services"]
        assert d["services"]["backend_ok"] is True


class TestAtlasReports:
    def test_create_report_defaults(self, session):
        r = session.post(f"{API}/atlas/report", json={"source": "pytest"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["supervisor"] == "Sr. Atlas"
        assert d["ecosystem"] == "Forge Factory Lab"
        assert d["status"] in VALID_STATUS
        assert d["source"] == "pytest"
        assert "id" in d and d["id"]
        assert "created_at" in d
        assert "message" in d
        assert "metrics" in d

    def test_create_report_custom_fields(self, session):
        payload = {
            "status": "alert",
            "message": "Manual drill from pytest",
            "backend_ok": True,
            "bridge_ok": False,
            "dashboard_ok": True,
            "source": "pytest",
        }
        r = session.post(f"{API}/atlas/report", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "ALERT"
        assert d["message"] == "Manual drill from pytest"
        assert d["bridge_ok"] is False

    def test_reports_list_contains_created(self, session):
        created = session.post(f"{API}/atlas/report", json={"source": "pytest-list"}, timeout=15).json()
        r = session.get(f"{API}/atlas/reports", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "reports" in d and "count" in d and "total" in d
        assert d["count"] == len(d["reports"])
        ids = {rep["id"] for rep in d["reports"]}
        assert created["id"] in ids, "newly created report should appear in the list"

    def test_reports_list_limit(self, session):
        r = session.get(f"{API}/atlas/reports", params={"limit": 2}, timeout=15)
        assert r.status_code == 200
        assert len(r.json()["reports"]) <= 2

    def test_reports_status_filter(self, session):
        session.post(f"{API}/atlas/report", json={"status": "OK", "source": "pytest"}, timeout=15)
        r = session.get(f"{API}/atlas/reports", params={"status": "OK"}, timeout=15)
        assert r.status_code == 200
        for rep in r.json()["reports"]:
            assert rep["status"] == "OK"


class TestAutoSnapshot:
    def test_supervision_config(self, session):
        r = session.get(f"{API}/supervision/config", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "auto_snapshot_enabled" in d
        assert "interval_sec" in d
        assert d["store_backend"] in ("mongo", "memory")
        assert d["mode"] in ("mock", "mt5")

    def test_trigger_auto_snapshot(self, session):
        r = session.post(f"{API}/supervision/auto-snapshot", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["source"] == "auto"
        assert d["supervisor"] == "Sr. Atlas"
        assert d["status"] in VALID_STATUS
        assert "id" in d and d["id"]
        assert "created_at" in d
        # the auto report should be retrievable from the list
        lst = session.get(f"{API}/atlas/reports", timeout=15).json()
        ids = {rep["id"] for rep in lst["reports"]}
        assert d["id"] in ids


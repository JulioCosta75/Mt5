"""Unit tests for problem report: local SQLite registry + Resend email (no auto-fix)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def atlas_db(tmp_path, monkeypatch):
    db_path = tmp_path / "atlas_test.db"
    monkeypatch.setenv("ATLAS_SQLITE_PATH", str(db_path))
    return db_path


@pytest.fixture
def client(atlas_db):
    from server import app

    with TestClient(app) as c:
        yield c


def _mock_resend_ok(email_id: str = "email_abc"):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": email_id}
    mock_resp.text = json.dumps({"id": email_id})
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _mock_resend_fail(status: int = 401):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.text = "Unauthorized"
    mock_resp.json.return_value = {"message": "Invalid API key"}
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def test_report_problem_persists_before_email_and_succeeds(client, atlas_db, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("REPORT_PROBLEM_TO", "lab@example.com")
    monkeypatch.setenv("REPORT_PROBLEM_FROM", "Sr. Atlas <onboarding@resend.dev>")

    with patch("httpx.AsyncClient", return_value=_mock_resend_ok()):
        r = client.post(
            "/api/system/report-problem",
            json={"note": "feed stuck", "tester": "Julio"},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["saved"] is True
    assert body["email_sent"] is True
    assert body["report_id"] >= 1
    assert "sent" in body["message"].lower()
    assert "thank you" in body["message"].lower()
    assert atlas_db.is_file()

    hist = client.get("/api/system/problem-reports")
    assert hist.status_code == 200
    rows = hist.json()["reports"]
    assert len(rows) >= 1
    assert rows[0]["id"] == body["report_id"]
    assert rows[0]["tester"] == "Julio"
    assert rows[0]["email_status"] == "sent"
    assert rows[0]["email_provider_id"] == "email_abc"

    detail = client.get(f"/api/system/problem-reports/{body['report_id']}")
    assert detail.status_code == 200
    diag = detail.json()["report"]["diagnostic"]
    assert diag["kind"] == "problem_report"
    assert diag.get("no_auto_remediation") is True or "user_note" in diag
    blob = json.dumps(diag)
    assert "RESEND_API_KEY" not in blob
    assert "MT5_LOGIN" not in blob
    assert "password" not in blob.lower()


def test_report_problem_persists_even_when_email_not_configured(client, atlas_db, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("REPORT_PROBLEM_TO", raising=False)

    r = client.post("/api/system/report-problem", json={"note": "offline test"})
    assert r.status_code == 503, r.text
    detail = r.json()["detail"]
    assert "saved locally" in detail.lower()
    assert "#" in detail
    assert "report saved and sent" not in detail.lower()

    hist = client.get("/api/system/problem-reports")
    assert hist.status_code == 200
    rows = hist.json()["reports"]
    assert len(rows) == 1
    assert rows[0]["email_status"] == "not_configured"

    full = client.get(f"/api/system/problem-reports/{rows[0]['id']}").json()["report"]
    assert "offline test" in json.dumps(full["diagnostic"])


def test_report_problem_never_claims_sent_on_provider_error(client, atlas_db, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_bad")
    monkeypatch.setenv("REPORT_PROBLEM_TO", "lab@example.com")

    with patch("httpx.AsyncClient", return_value=_mock_resend_fail()):
        r = client.post("/api/system/report-problem", json={})

    assert r.status_code == 503
    detail = r.json()["detail"].lower()
    assert "saved locally" in detail
    # Must not claim success as if email went through alone
    assert not detail.startswith("report saved and sent")

    rows = client.get("/api/system/problem-reports").json()["reports"]
    assert rows[0]["email_status"] == "failed"


def test_build_diagnostic_payload_has_no_credential_fields():
    from problem_report import build_diagnostic_payload

    health = {
        "mode": "live",
        "version": "0.3.0",
        "build": {"version": "0.3.0", "build": "test"},
        "bridge": {
            "url": "http://127.0.0.1:8001",
            "reachable": True,
            "password": "should-be-stripped",
            "api_key": "should-be-stripped",
        },
        "store": {"backend": "memory"},
    }
    d = build_diagnostic_payload(health, note="x")
    blob = json.dumps(d)
    assert "should-be-stripped" not in blob
    assert "RESEND_API_KEY" not in blob
    assert d["kind"] == "problem_report"
    assert "bridge" in d
    assert "recent_logs" in d


def test_sqlite_store_roundtrip(atlas_db):
    from problem_report_store import ProblemReportStore

    store = ProblemReportStore()
    rid = store.insert(
        tester="Codex",
        atlas_version="0.3.0",
        atlas_build="test",
        diagnostic={"hello": "world", "kind": "problem_report"},
        email_status="pending",
    )
    store.update_email(rid, email_status="sent", email_provider_id="eid1")
    rows = store.list_recent(limit=5)
    assert rows[0]["id"] == rid
    assert rows[0]["tester"] == "Codex"
    assert rows[0]["email_status"] == "sent"
    full = store.get(rid)
    assert full["diagnostic"]["hello"] == "world"

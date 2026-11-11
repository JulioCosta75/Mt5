"""The MT5 config sent to the browser never carries the password or the bridge token.

In-process only: no preview URL, no MT5, no bridge.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import mt5_config  # noqa: E402
import server  # noqa: E402

TOKEN = "tok_9f3b1c7e5a2d4f60b8e1"
PASSWORD = "pw_7c2e9a41"


def _cfg(**extra):
    cfg = dict(mt5_config.DEFAULTS)
    cfg.update(
        configured=True,
        login="12345678",
        password=PASSWORD,
        server="Broker-Demo",
        bridge_token=TOKEN,
    )
    cfg.update(extra)
    return cfg


def test_masked_omits_secrets_and_reports_presence():
    out = mt5_config.masked(_cfg())
    assert "password" not in out
    assert "bridge_token" not in out
    assert out["password_set"] is True
    assert out["bridge_token_set"] is True
    assert TOKEN not in str(out)
    assert PASSWORD not in str(out)


def test_masked_reports_missing_token():
    out = mt5_config.masked(_cfg(bridge_token=""))
    assert out["bridge_token_set"] is False


def test_masked_keeps_non_secret_fields():
    out = mt5_config.masked(_cfg())
    for key in ("configured", "login", "server", "terminal_path", "bridge_host", "bridge_port", "updated_at"):
        assert key in out


def test_get_config_endpoint_never_returns_token(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(server._mt5cfg, "load", lambda: _cfg())
    r = TestClient(server.app).get("/api/mt5/config")
    assert r.status_code == 200, r.text
    assert TOKEN not in r.text
    assert PASSWORD not in r.text
    assert r.json()["config"]["bridge_token_set"] is True

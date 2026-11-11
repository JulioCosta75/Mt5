"""Reloading a React route serves index.html; /api and asset 404s are kept."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from spa_static import SPAStaticFiles, _is_client_route  # noqa: E402


@pytest.fixture
def client(tmp_path):
    (tmp_path / "index.html").write_text("<html>atlas</html>", encoding="utf-8")
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "main.js").write_text("console.log(1)", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/ping")
    async def ping():
        return {"ok": True}

    app.mount("/", SPAStaticFiles(directory=str(tmp_path), html=True), name="frontend")
    return TestClient(app)


def test_root_and_client_routes_serve_index(client):
    for path in ("/", "/settings", "/settings/", "/reports/123"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert "atlas" in r.text


def test_existing_assets_are_served(client):
    r = client.get("/static/main.js")
    assert r.status_code == 200
    assert "console.log" in r.text


def test_api_routes_and_api_404_untouched(client):
    assert client.get("/api/ping").json() == {"ok": True}
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert "atlas" not in r.text


def test_missing_asset_stays_404(client):
    r = client.get("/static/missing.js")
    assert r.status_code == 404


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("settings", True),
        ("a/b", True),
        ("api", False),
        ("api/x", False),
        ("x.js", False),
        ("static/a.css", False),
        # Windows-normalized paths from StaticFiles.get_path()
        ("api\\does-not-exist", False),
        ("reports\\123", True),
        ("static\\a.css", False),
    ],
)
def test_is_client_route(path, expected):
    assert _is_client_route(path) is expected

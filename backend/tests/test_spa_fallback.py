"""SPA static serving: index.html fallback for client-side routes."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server import mount_spa_frontend


def _make_build(tmp: Path) -> Path:
    (tmp / "static" / "js").mkdir(parents=True)
    (tmp / "index.html").write_text(
        "<!doctype html><html><body>SPA_INDEX</body></html>", encoding="utf-8"
    )
    (tmp / "static" / "js" / "main.js").write_text("console.log('ok')", encoding="utf-8")
    (tmp / "favicon.ico").write_bytes(b"\x00\x00ico")
    return tmp


class SpaFallbackTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.build = _make_build(Path(self._tmp.name))
        self.app = FastAPI(docs_url=None, redoc_url=None)

        @self.app.get("/api/kpis")
        async def kpis():
            return {"ok": True}

        @self.app.get("/healthcheck")
        async def healthcheck():
            return {"page": "healthcheck"}

        self.assertTrue(mount_spa_frontend(self.app, self.build))
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp.cleanup()

    def test_root_serves_index(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("SPA_INDEX", r.text)

    def test_settings_direct_url_serves_index(self):
        r = self.client.get("/settings")
        self.assertEqual(r.status_code, 200)
        self.assertIn("SPA_INDEX", r.text)
        self.assertNotIn("Not Found", r.text)

    def test_about_and_docs_serve_index(self):
        for path in ("/about", "/docs", "/strategies", "/risk"):
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 200, path)
                self.assertIn("SPA_INDEX", r.text)

    def test_real_asset_still_served(self):
        r = self.client.get("/static/js/main.js")
        self.assertEqual(r.status_code, 200)
        self.assertIn("console.log", r.text)

    def test_root_file_still_served(self):
        r = self.client.get("/favicon.ico")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"\x00\x00ico")

    def test_api_routes_not_swallowed(self):
        r = self.client.get("/api/kpis")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"ok": True})

    def test_unknown_api_stays_404_json(self):
        r = self.client.get("/api/does-not-exist")
        self.assertEqual(r.status_code, 404)

    def test_healthcheck_not_replaced_by_spa(self):
        r = self.client.get("/healthcheck")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"page": "healthcheck"})

    def test_path_traversal_rejected(self):
        r = self.client.get("/../server.py")
        # Either blocked as 404 or normalized away from escape.
        self.assertIn(r.status_code, (404, 200))
        if r.status_code == 200:
            # Must not leak backend source — only SPA index or safe asset.
            self.assertNotIn("mount_spa_frontend", r.text)


if __name__ == "__main__":
    unittest.main()

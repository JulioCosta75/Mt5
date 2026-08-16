"""Tests for problem-report sanitization and honest failure without Resend key."""
from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from problem_report import (
    NOT_CONFIGURED_FAIL,
    USER_FACING_FAIL,
    ReportSendError,
    build_diagnostic_payload,
    sanitize,
    send_problem_report,
)


class SanitizeTests(unittest.TestCase):
    def test_strips_password_token_login(self):
        raw = {
            "mode": "mt5",
            "password": "secret-pass",
            "bridge": {
                "login": 12345,
                "server": "PepperstoneUK-Demo",
                "last_error": "auth failed",
                "token": "abc",
                "reachable": True,
            },
            "RESEND_API_KEY": "re_xxx",
        }
        clean = sanitize(raw)
        self.assertNotIn("password", clean)
        self.assertNotIn("RESEND_API_KEY", clean)
        self.assertNotIn("login", clean["bridge"])
        self.assertNotIn("token", clean["bridge"])
        self.assertEqual(clean["bridge"]["server"], "PepperstoneUK-Demo")
        self.assertTrue(clean["bridge"]["reachable"])

    def test_build_diagnostic_drops_bridge_login(self):
        health = {
            "mode": "mt5",
            "version": "0.3.0",
            "build": {"version": "0.3.0", "build": "test"},
            "server_time": "2026-01-01T00:00:00Z",
            "store": {"backend": "sqlite", "ok": True},
            "bridge": {
                "url": "http://127.0.0.1:8002",
                "reachable": True,
                "login": 99999,
                "password": "nope",
                "server": "Demo",
                "last_error": None,
            },
        }
        payload = build_diagnostic_payload(health)
        self.assertEqual(payload["kind"], "problem_report")
        self.assertIsNone(payload["bridge"].get("login"))
        self.assertNotIn("password", payload["bridge"])
        blob = str(payload)
        self.assertNotIn("99999", blob)
        self.assertNotIn("nope", blob)


class SendReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_api_key_fails_honestly(self):
        os.environ.pop("RESEND_API_KEY", None)
        with self.assertRaises(ReportSendError) as ctx:
            await send_problem_report({"version": "0.3.0", "generated_at": "t"})
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.user_message, NOT_CONFIGURED_FAIL)
        self.assertNotIn("sucesso", ctx.exception.user_message.lower())

    async def test_provider_error_fails_honestly(self):
        os.environ["RESEND_API_KEY"] = "re_test_key"
        mock_resp = AsyncMock()
        mock_resp.status_code = 401
        mock_resp.text = "unauthorized"
        mock_resp.json = lambda: {"message": "invalid"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("problem_report.httpx.AsyncClient", return_value=mock_client):
            with self.assertRaises(ReportSendError) as ctx:
                await send_problem_report({"version": "0.3.0", "generated_at": "t"})
        self.assertEqual(ctx.exception.user_message, USER_FACING_FAIL)
        os.environ.pop("RESEND_API_KEY", None)

    async def test_success_returns_confirmation(self):
        os.environ["RESEND_API_KEY"] = "re_test_key"
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = "{}"
        mock_resp.json = lambda: {"id": "email_123"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("problem_report.httpx.AsyncClient", return_value=mock_client):
            result = await send_problem_report({"version": "0.3.0", "generated_at": "t"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "Relatório enviado, obrigado")
        os.environ.pop("RESEND_API_KEY", None)


class EndpointIntegrationTests(unittest.TestCase):
    """POST /api/system/report-problem without a key must not fake success."""

    def setUp(self):
        os.environ.pop("RESEND_API_KEY", None)
        # Import the real app route wiring via a thin FastAPI copy of the handler.
        from fastapi import FastAPI, HTTPException
        from problem_report import ReportSendError, build_diagnostic_payload, send_problem_report

        self.app = FastAPI()

        @self.app.get("/api/system/health")
        async def health():
            return {
                "mode": "mock",
                "version": "0.3.0",
                "build": {"version": "0.3.0"},
                "server_time": "t",
                "store": {"ok": True},
                "bridge": None,
            }

        @self.app.post("/api/system/report-problem")
        async def report():
            payload = build_diagnostic_payload(await health())
            try:
                return await send_problem_report(payload)
            except ReportSendError as e:
                raise HTTPException(status_code=e.status_code, detail=e.user_message) from e

        self.client = TestClient(self.app)

    def test_endpoint_without_key_returns_clear_error(self):
        r = self.client.post("/api/system/report-problem")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"], NOT_CONFIGURED_FAIL)
        self.assertNotEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()

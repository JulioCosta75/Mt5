"""Deterministic tests for the Telegram DEMO outbound bridge.

No real network. Telegram HTTP is replaced by MockHttpClient.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telegram_demo_outbound.bridge import OutboundBridge, build_bridge_from_env
from telegram_demo_outbound.constants import REQUIRED_PREFIX
from telegram_demo_outbound.demo_payloads import (
    daily_summary_text,
    order_created_text,
    startup_text,
)
from telegram_demo_outbound.errors import (
    ChatNotAllowlistedError,
    FailClosedError,
    MissingTokenError,
)
from telegram_demo_outbound.events import (
    DAILY_SUMMARY_FIELDS,
    ORDER_CREATED_FIELDS,
    missing_order_fields,
    missing_summary_fields,
)
from telegram_demo_outbound.queue import DurableOutbox
from telegram_demo_outbound.rate_limit import RateLimiter
from telegram_demo_outbound.redact import redact_text
from telegram_demo_outbound.transport import MockHttpClient, MockTransport, TelegramHttpTransport

JULIO_CHAT = "10001"
OTHER_CHAT = "99999"
DUMMY_TOKEN = "123456789:AADummyTokenValueForTestsOnly012345678"


def _outbox(directory: str) -> DurableOutbox:
    return DurableOutbox(str(Path(directory) / "outbox.sqlite"), secrets=(DUMMY_TOKEN, JULIO_CHAT))


def _rate() -> RateLimiter:
    return RateLimiter(per_chat_interval=0.0, global_max_per_sec=10_000)


def _http_bridge(directory: str, http: MockHttpClient, app_mode: str | None) -> OutboundBridge:
    transport = TelegramHttpTransport(
        token=DUMMY_TOKEN,
        allowlist=frozenset({JULIO_CHAT}),
        app_mode=app_mode,
        http=http,
    )
    return OutboundBridge(
        transport=transport,
        outbox=_outbox(directory),
        allowlist=frozenset({JULIO_CHAT}),
        rate_limiter=_rate(),
    )


def _mock_bridge(directory: str) -> OutboundBridge:
    return OutboundBridge(
        transport=MockTransport(),
        outbox=_outbox(directory),
        allowlist=frozenset({JULIO_CHAT}),
        rate_limiter=_rate(),
    )


class TestFailClosed(unittest.TestCase):
    def _assert_fail_closed(self, app_mode: str | None) -> None:
        http = MockHttpClient()
        with tempfile.TemporaryDirectory() as tmp:
            bridge = _http_bridge(tmp, http, app_mode)
            with self.assertRaises(FailClosedError) as ctx:
                bridge.enqueue("evt-start", JULIO_CHAT, startup_text())
                bridge.flush()
            self.assertIn("refusing to send", str(ctx.exception))
            self.assertNotIn(DUMMY_TOKEN, str(ctx.exception))
        self.assertEqual(http.calls, [])

    def test_fail_closed_when_app_mode_absent(self) -> None:
        self._assert_fail_closed(None)

    def test_fail_closed_when_app_mode_empty(self) -> None:
        self._assert_fail_closed("")

    def test_fail_closed_when_app_mode_real(self) -> None:
        self._assert_fail_closed("real")

    def test_fail_closed_when_app_mode_unknown(self) -> None:
        self._assert_fail_closed("unknown")

    def test_factory_fail_closed_http_without_demo(self) -> None:
        env = {
            "APP_MODE": "real",
            "TELEGRAM_TRANSPORT": "http",
            "TELEGRAM_BOT_TOKEN": DUMMY_TOKEN,
            "TELEGRAM_CHAT_ID": JULIO_CHAT,
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FailClosedError):
                build_bridge_from_env(env, outbox_path=str(Path(tmp) / "o.sqlite"))


class TestAllowlist(unittest.TestCase):
    def test_reject_chat_id_outside_allowlist(self) -> None:
        http = MockHttpClient()
        with tempfile.TemporaryDirectory() as tmp:
            bridge = _http_bridge(tmp, http, "demo")
            with self.assertRaises(ChatNotAllowlistedError) as ctx:
                bridge.enqueue("evt-other", OTHER_CHAT, startup_text())
            self.assertIn("allowlist", str(ctx.exception))
            self.assertNotIn(DUMMY_TOKEN, str(ctx.exception))
            flush = bridge.flush()
            self.assertEqual(flush.sent, 0)
        self.assertEqual(http.calls, [])


class TestMissingToken(unittest.TestCase):
    def test_missing_token_refuses_to_operate(self) -> None:
        env = {
            "APP_MODE": "demo",
            "TELEGRAM_TRANSPORT": "http",
            "TELEGRAM_CHAT_ID": JULIO_CHAT,
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MissingTokenError) as ctx:
                build_bridge_from_env(env, outbox_path=str(Path(tmp) / "o.sqlite"))
            self.assertIn("absent", str(ctx.exception))
            self.assertIn("refusing to operate", str(ctx.exception))

    def test_missing_token_never_exposes_value(self) -> None:
        env = {
            "APP_MODE": "demo",
            "TELEGRAM_TRANSPORT": "http",
            "TELEGRAM_CHAT_ID": JULIO_CHAT,
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MissingTokenError) as ctx:
                build_bridge_from_env(env, outbox_path=str(Path(tmp) / "o.sqlite"))
            message = str(ctx.exception)
        self.assertNotRegex(message, r"\d{6,}:[A-Za-z0-9_-]{20,}")
        self.assertNotIn("TELEGRAM_BOT_TOKEN=", message)
        leaked = redact_text(message)
        self.assertEqual(leaked, message)

    def test_http_error_redacts_token(self) -> None:
        http = MockHttpClient()
        http.raise_with_token_in_error = DUMMY_TOKEN
        with tempfile.TemporaryDirectory() as tmp:
            bridge = _http_bridge(tmp, http, "demo")
            bridge.enqueue("evt-redact", JULIO_CHAT, startup_text())
            result = bridge.flush()
            self.assertEqual(result.retried, 1)
            stored = bridge.outbox.get("evt-redact")
            self.assertIsNotNone(stored)
            self.assertNotIn(DUMMY_TOKEN, stored.last_error or "")
            self.assertNotRegex(stored.last_error or "", r"\d{6,}:[A-Za-z0-9_-]{20,}")


class TestPrefix(unittest.TestCase):
    def test_prefix_present_on_every_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bridge = _mock_bridge(tmp)
            payloads = {
                "evt-startup": startup_text(),
                "evt-order": order_created_text(),
                "evt-summary": daily_summary_text(),
                "evt-plain": "plain synthetic line",
            }
            for event_id, text in payloads.items():
                bridge.enqueue(event_id, JULIO_CHAT, text)
            result = bridge.flush()
            self.assertEqual(result.sent, 4)
            sent_texts = [item["text"] for item in bridge.transport.sent]
            self.assertEqual(len(sent_texts), 4)
            for text in sent_texts:
                self.assertTrue(
                    text.startswith(REQUIRED_PREFIX),
                    f"message did not start with required prefix: {text[:40]!r}",
                )


class TestDedup(unittest.TestCase):
    def test_retry_does_not_duplicate_send(self) -> None:
        http = MockHttpClient()
        http.fail_remaining = 1
        with tempfile.TemporaryDirectory() as tmp:
            bridge = _http_bridge(tmp, http, "demo")
            bridge.enqueue("evt-unique", JULIO_CHAT, startup_text())
            first = bridge.flush()
            self.assertEqual(first.retried, 1)
            self.assertEqual(first.sent, 0)
            send_calls = [c for c in http.calls if c["method"] == "sendMessage"]
            self.assertEqual(len(send_calls), 1)
            second = bridge.flush()
            self.assertEqual(second.sent, 1)
            send_calls = [c for c in http.calls if c["method"] == "sendMessage"]
            self.assertEqual(len(send_calls), 2)
            third = bridge.flush()
            self.assertEqual(third.sent, 0)
            self.assertEqual(third.skipped_duplicate, 0)
            send_calls = [c for c in http.calls if c["method"] == "sendMessage"]
            self.assertEqual(len(send_calls), 2)
            stored = bridge.outbox.get("evt-unique")
            self.assertEqual(stored.status, "sent")
            self.assertIsNotNone(stored.provider_message_id)
            again = bridge.enqueue("evt-unique", JULIO_CHAT, startup_text())
            self.assertEqual(again, "duplicate")
            fourth = bridge.flush()
            send_calls = [c for c in http.calls if c["method"] == "sendMessage"]
            self.assertEqual(len(send_calls), 2)
            self.assertEqual(fourth.sent, 0)


class TestSyntheticEvents(unittest.TestCase):
    def test_order_created_has_all_required_fields(self) -> None:
        text = order_created_text()
        self.assertTrue(text.startswith(REQUIRED_PREFIX))
        self.assertIn("SYNTHETIC DATA", text)
        self.assertEqual(missing_order_fields(text), [])
        for name in ORDER_CREATED_FIELDS:
            self.assertIn(f"{name}:", text)

    def test_daily_summary_has_all_required_fields(self) -> None:
        text = daily_summary_text()
        self.assertTrue(text.startswith(REQUIRED_PREFIX))
        self.assertIn("SYNTHETIC DATA", text)
        self.assertEqual(missing_summary_fields(text), [])
        for name in DAILY_SUMMARY_FIELDS:
            self.assertIn(f"{name}:", text)

    def test_startup_event_is_synthetic(self) -> None:
        text = startup_text()
        self.assertTrue(text.startswith(REQUIRED_PREFIX))
        self.assertIn("event: startup", text)
        self.assertIn("SYNTHETIC DATA", text)


class TestDefaultMockTransport(unittest.TestCase):
    def test_factory_defaults_to_mock(self) -> None:
        env = {"TELEGRAM_CHAT_ID": JULIO_CHAT}
        with tempfile.TemporaryDirectory() as tmp:
            bridge = build_bridge_from_env(env, outbox_path=str(Path(tmp) / "o.sqlite"))
            self.assertIsInstance(bridge.transport, MockTransport)
            bridge.enqueue("evt-mock", JULIO_CHAT, startup_text())
            result = bridge.flush()
            self.assertEqual(result.sent, 1)


class TestPhase2Isolation(unittest.TestCase):
    def test_not_imported_by_phase2_backend(self) -> None:
        server = Path(__file__).resolve().parents[2] / "backend" / "server.py"
        text = server.read_text(encoding="utf-8")
        self.assertNotIn("telegram_demo_outbound", text)

    def test_not_imported_by_mt5_bridge(self) -> None:
        root = Path(__file__).resolve().parents[2] / "mt5-bridge"
        for path in root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("telegram_demo_outbound", text, path.name)

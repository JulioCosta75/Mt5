"""Transports: mock by default; real HTTP only when APP_MODE is exactly 'demo'."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from telegram_demo_outbound.constants import (
    DEFAULT_HTTP_TIMEOUT_SEC,
    DEMO_APP_MODE,
    TELEGRAM_API_BASE,
)
from telegram_demo_outbound.errors import (
    ChatNotAllowlistedError,
    FailClosedError,
    PermanentTransportError,
    RetryableTransportError,
)
from telegram_demo_outbound.redact import exception_text, redact_text, sanitize_telegram_json


@dataclass(frozen=True)
class RawHttpResponse:
    status: int
    body: str


@dataclass(frozen=True)
class SendResult:
    ok: bool
    status: int
    provider_message_id: str | None
    retryable: bool = False
    sanitized_body: object | None = None


class HttpClient(Protocol):
    def get(self, url: str, timeout: float) -> RawHttpResponse: ...

    def post(
        self, url: str, form: dict[str, str], timeout: float
    ) -> RawHttpResponse: ...


class UrlLibHttpClient:
    """stdlib HTTP client. Callers must never log the URL (it contains the token)."""

    def get(self, url: str, timeout: float) -> RawHttpResponse:
        return self._request(url, data=None, timeout=timeout)

    def post(
        self, url: str, form: dict[str, str], timeout: float
    ) -> RawHttpResponse:
        encoded = urllib.parse.urlencode(form).encode("utf-8")
        return self._request(url, data=encoded, timeout=timeout)

    def _request(
        self, url: str, data: bytes | None, timeout: float
    ) -> RawHttpResponse:
        request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        if data is not None:
            request.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return RawHttpResponse(status=int(response.status), body=raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            return RawHttpResponse(status=int(exc.code), body=raw)
        except urllib.error.URLError as exc:
            secrets = _secrets_from_url(url)
            raise RetryableTransportError(
                exception_text(exc, secrets)
            ) from None


def _secrets_from_url(url: str) -> tuple[str, ...]:
    # Extract token from /bot<token>/<method> without ever returning it to logs.
    marker = "/bot"
    if marker not in url:
        return ()
    after = url.split(marker, 1)[1]
    token = after.split("/", 1)[0]
    return (token,) if token else ()


def _method_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


class MockHttpClient:
    """In-memory Telegram endpoint. Stores method names, never URLs."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.status_by_method: dict[str, int] = {}
        self.body_by_method: dict[str, str] = {}
        self.fail_remaining: int = 0
        self.next_message_id: int = 1
        self.raise_with_token_in_error: str | None = None

    def get(self, url: str, timeout: float) -> RawHttpResponse:
        return self._handle("GET", url, {})

    def post(
        self, url: str, form: dict[str, str], timeout: float
    ) -> RawHttpResponse:
        return self._handle("POST", url, form)

    def _handle(
        self, http_method: str, url: str, form: dict[str, str]
    ) -> RawHttpResponse:
        method = _method_from_url(url)
        if self.raise_with_token_in_error:
            leaked = f"upstream failed contacting {url}"
            self.raise_with_token_in_error = None
            raise RetryableTransportError(leaked)
        self.calls.append({"http": http_method, "method": method, "form": dict(form)})
        if self.fail_remaining > 0:
            self.fail_remaining -= 1
            return RawHttpResponse(500, '{"ok":false,"description":"synthetic-fail"}')
        status = self.status_by_method.get(method, 200)
        if method in self.body_by_method:
            return RawHttpResponse(status, self.body_by_method[method])
        if method == "getMe":
            body = json.dumps(
                {
                    "ok": True,
                    "result": {
                        "id": 1,
                        "is_bot": True,
                        "first_name": "synthetic-bot",
                        "username": "synthetic_bot",
                    },
                }
            )
            return RawHttpResponse(status, body)
        if method == "getUpdates":
            body = json.dumps({"ok": True, "result": []})
            return RawHttpResponse(status, body)
        if method == "sendMessage":
            mid = self.next_message_id
            self.next_message_id += 1
            body = json.dumps(
                {
                    "ok": True,
                    "result": {
                        "message_id": mid,
                        "date": 0,
                        "text": form.get("text", ""),
                        "chat": {"id": 0, "type": "private"},
                    },
                }
            )
            return RawHttpResponse(status, body)
        return RawHttpResponse(status, '{"ok":true,"result":{}}')


@dataclass
class MockTransport:
    """Default transport: records messages, never opens a network socket."""

    sent: list[dict[str, str]] = field(default_factory=list)
    _next_id: int = 1

    def send_message(self, chat_id: str, text: str) -> SendResult:
        message_id = str(self._next_id)
        self._next_id += 1
        self.sent.append({"chat_id": chat_id, "text": text, "message_id": message_id})
        return SendResult(
            ok=True,
            status=0,
            provider_message_id=message_id,
            sanitized_body={"ok": True, "transport": "mock", "message_id": message_id},
        )


class TelegramHttpTransport:
    """Real Telegram Bot API transport. Fail-closed unless APP_MODE == 'demo'."""

    def __init__(
        self,
        *,
        token: str,
        allowlist: frozenset[str],
        app_mode: str | None,
        http: HttpClient | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT_SEC,
    ) -> None:
        self._token = token
        self._allowlist = allowlist
        self._app_mode = app_mode
        self._http = http or UrlLibHttpClient()
        self._timeout = timeout
        self._secrets = (token, *allowlist)

    def _assert_demo(self) -> None:
        if self._app_mode != DEMO_APP_MODE:
            raise FailClosedError(
                "APP_MODE is not exactly 'demo'; refusing to send via real transport"
            )

    def _url(self, method: str) -> str:
        return f"{TELEGRAM_API_BASE}/bot{self._token}/{method}"

    def _parse(self, response: RawHttpResponse) -> dict:
        try:
            payload = json.loads(response.body) if response.body else {}
        except json.JSONDecodeError:
            payload = {"ok": False, "description": "non-json-body"}
        if not isinstance(payload, dict):
            payload = {"ok": False, "description": "unexpected-body"}
        return sanitize_telegram_json(payload, secrets=self._secrets)

    def call(self, method: str, *, form: dict[str, str] | None = None) -> tuple[int, dict]:
        self._assert_demo()
        url = self._url(method)
        try:
            if form is None:
                raw = self._http.get(url, self._timeout)
            else:
                raw = self._http.post(url, form, self._timeout)
        except RetryableTransportError as exc:
            raise RetryableTransportError(
                redact_text(str(exc), self._secrets)
            ) from None
        except FailClosedError:
            raise
        except Exception as exc:
            raise RetryableTransportError(
                exception_text(exc, self._secrets)
            ) from None
        return raw.status, self._parse(raw)

    def get_me(self) -> tuple[int, dict]:
        return self.call("getMe")

    def get_updates(self) -> tuple[int, dict]:
        return self.call("getUpdates", form={"timeout": "0", "limit": "100"})

    def send_message(self, chat_id: str, text: str) -> SendResult:
        self._assert_demo()
        if str(chat_id) not in self._allowlist:
            raise ChatNotAllowlistedError(
                "chat_id is not on the allowlist; refusing to send"
            )
        status, payload = self.call(
            "sendMessage",
            form={"chat_id": str(chat_id), "text": text},
        )
        ok = bool(payload.get("ok")) and 200 <= status < 300
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        provider_id = None
        if isinstance(result, dict) and result.get("message_id") is not None:
            provider_id = str(result.get("message_id"))
        retryable = (not ok) and (status == 429 or status >= 500 or status == 0)
        if ok and provider_id:
            return SendResult(
                ok=True,
                status=status,
                provider_message_id=provider_id,
                sanitized_body=payload,
            )
        if retryable:
            raise RetryableTransportError(
                f"telegram send retryable status={status} ok={payload.get('ok')}"
            )
        raise PermanentTransportError(
            f"telegram send rejected status={status} ok={payload.get('ok')}"
        )

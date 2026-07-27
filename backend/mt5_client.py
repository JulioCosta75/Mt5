"""HTTP client(s) for the MT5 bridge(s).

Supports one OR many bridges (one per MT5 account). Each bridge is identified
by its base URL + bearer token. The client exposes async helpers that the
backend routes consume.

Environment variables (in /app/backend/.env):

    MT5_BRIDGE_URL        – single bridge URL (e.g. https://tunnel.example.com)
    MT5_BRIDGE_TOKEN      – bearer token for that bridge

  OR for multi-bridge:

    MT5_BRIDGE_URLS       – comma-separated list of URLs
    MT5_BRIDGE_TOKENS     – comma-separated list of tokens (same order)

If none of the above are set, callers should fall back to mock data (existing
behaviour). This keeps the preview functional while the bridge isn't online.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("mt5-client")


@dataclass(frozen=True)
class BridgeEndpoint:
    url: str
    token: str
    label: str  # short id for logs/cache (we'll fill in once we know the login)


def _list_env(name: str) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def configured_bridges() -> list[BridgeEndpoint]:
    urls = _list_env("MT5_BRIDGE_URLS")
    tokens = _list_env("MT5_BRIDGE_TOKENS")
    if not urls:
        single_url = os.environ.get("MT5_BRIDGE_URL", "").strip()
        single_token = os.environ.get("MT5_BRIDGE_TOKEN", "").strip()
        if single_url:
            urls = [single_url]
            tokens = [single_token]
    if not urls:
        return []
    if len(tokens) < len(urls):
        # pad with empty so misconfiguration fails clearly downstream
        tokens = tokens + [""] * (len(urls) - len(tokens))
    return [BridgeEndpoint(url=u.rstrip("/"), token=t, label=f"bridge#{i}")
            for i, (u, t) in enumerate(zip(urls, tokens))]


class BridgeClient:
    def __init__(self, endpoint: BridgeEndpoint, timeout: float = 8.0):
        self.endpoint = endpoint
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.endpoint.token}"} if self.endpoint.token else {}

    async def _get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(f"{self.endpoint.url}{path}", params=params, headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def health(self) -> dict:
        return await self._get("/health")

    async def account(self) -> dict:
        return await self._get("/account")

    async def positions(self) -> list[dict]:
        return await self._get("/positions")

    async def orders(self) -> list[dict]:
        return await self._get("/orders")

    async def deals(self, days: int = 90) -> list[dict]:
        return await self._get("/deals", params={"days": days})

    async def equity_history(self, days: int = 90) -> dict:
        return await self._get("/equity-history", params={"days": days})


def clients() -> list[BridgeClient]:
    return [BridgeClient(ep) for ep in configured_bridges()]

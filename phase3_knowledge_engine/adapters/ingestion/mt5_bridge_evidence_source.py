"""Read-only MT5 bridge evidence source (Phase 3 Gate 1).

Fetches closed deals from the Phase 2 bridge GET /deals via the existing
``backend.mt5_client.BridgeClient`` pattern — never places trades, never
writes back to Phase 2 backend or bridge.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from phase3_knowledge_engine.domain.entities import (
    AccountType,
    EAKnowledgeProfile,
    EvidenceItem,
)

logger = logging.getLogger("phase3.mt5_bridge_evidence")

SOURCE_SYSTEM = "mt5_bridge"
INCOMPLETE_MARKER = "incomplete_auto_from_magic"
INCOMPLETE_NOTE = (
    "Auto-created from MT5 magic number; needs manual completion by founder."
)


class _SupportsBridgeReads(Protocol):
    """Minimal async surface of backend.mt5_client.BridgeClient (read-only)."""

    async def deals(self, days: int = 90) -> list[dict]: ...

    async def account(self) -> dict: ...


class _KnowledgeStore(Protocol):
    def get_ea_profile_by_ea_key(self, ea_key: str) -> EAKnowledgeProfile | None: ...

    def save_ea_profile(self, profile: EAKnowledgeProfile) -> EAKnowledgeProfile: ...

    def has_evidence_by_external_id(
        self, source_system: str, external_id: str
    ) -> bool: ...


def magic_ea_key(magic: int | str) -> str:
    return f"magic-{magic}"


def is_incomplete_ea_profile(profile: EAKnowledgeProfile) -> bool:
    mc = profile.market_conditions or {}
    return bool(mc.get("incomplete") or mc.get("needs_manual_completion")) or (
        INCOMPLETE_MARKER in (profile.known_weaknesses or [])
    )


def resolve_account_type(account: dict[str, Any] | None) -> AccountType:
    """Map bridge /account payload to demo|live (best-effort; no write APIs)."""
    if not account:
        return "live"
    explicit = account.get("trade_mode") or account.get("account_type")
    if isinstance(explicit, str):
        low = explicit.strip().lower()
        if "demo" in low:
            return "demo"
        if low in ("live", "real"):
            return "live"
    blob = " ".join(
        str(account.get(k) or "") for k in ("server", "broker", "name", "company")
    ).lower()
    if "demo" in blob:
        return "demo"
    return "live"


def deal_net_pnl(deal: dict[str, Any]) -> float:
    """Net real result: profit + swap + commission."""
    profit = float(deal.get("profit") or 0.0)
    swap = float(deal.get("swap") or 0.0)
    commission = float(deal.get("commission") or 0.0)
    return profit + swap + commission


def parse_deal_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value is None or value == "":
        return datetime.now(timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def build_incomplete_ea_profile(magic: int) -> EAKnowledgeProfile:
    """Minimal EA dossier flagged incomplete for founder follow-up."""
    return EAKnowledgeProfile(
        id=uuid4(),
        ea_key=magic_ea_key(magic),
        name=f"EA magic {magic} (incomplete)",
        version="unknown",
        purpose=INCOMPLETE_NOTE,
        entry_rules="(incomplete — needs manual completion)",
        exit_rules="(incomplete — needs manual completion)",
        risk_rules={"incomplete": True, "magic": magic},
        permitted_symbols=[],
        permitted_sessions=[],
        market_conditions={
            "incomplete": True,
            "needs_manual_completion": True,
            "auto_created_from_magic": magic,
            INCOMPLETE_MARKER: True,
        },
        status="testing",
        known_weaknesses=[INCOMPLETE_MARKER, INCOMPLETE_NOTE],
        open_hypotheses=[INCOMPLETE_NOTE],
    )


def ensure_ea_profile_for_magic(
    store: _KnowledgeStore, magic: int
) -> EAKnowledgeProfile:
    """Return existing profile for magic, or auto-create an incomplete one."""
    key = magic_ea_key(magic)
    existing = store.get_ea_profile_by_ea_key(key)
    if existing is not None:
        return existing
    profile = build_incomplete_ea_profile(magic)
    return store.save_ea_profile(profile)


def map_deal_to_evidence(
    deal: dict[str, Any],
    *,
    ea_profile_id: UUID,
    account_type: AccountType,
    ingestion_batch_id: str | None = None,
) -> EvidenceItem:
    """Map one bridge deal dict to EvidenceItem (pnl = profit+swap+commission)."""
    ticket = deal.get("ticket")
    if ticket is None:
        raise ValueError("deal missing ticket")
    return EvidenceItem(
        id=uuid4(),
        ea_profile_id=ea_profile_id,
        evidence_type="trade",
        occurred_at=parse_deal_time(deal.get("time")),
        symbol=str(deal.get("symbol") or ""),
        pnl=deal_net_pnl(deal),
        account_type=account_type,
        test_type="forward",
        raw_payload=dict(deal),
        source_system=SOURCE_SYSTEM,
        external_id=str(ticket),
        ingestion_batch_id=ingestion_batch_id,
        entry_reason=str(deal.get("comment") or "") or None,
    )


class Mt5BridgeEvidenceSource:
    """EvidenceSourcePort: Phase 2 MT5 bridge → EvidenceItem (batch, read-only)."""

    def __init__(
        self,
        store: _KnowledgeStore,
        *,
        bridge_client: _SupportsBridgeReads | None = None,
        days: int = 90,
        account_type: AccountType | None = None,
        fetch_deals: Callable[[], list[dict[str, Any]]] | None = None,
        fetch_account: Callable[[], dict[str, Any]] | None = None,
        ingestion_batch_id: str | None = None,
    ):
        if bridge_client is None and fetch_deals is None:
            raise ValueError("Provide bridge_client or fetch_deals")
        self._store = store
        self._client = bridge_client
        self._days = max(1, min(int(days), 365))
        self._account_type_override = account_type
        self._fetch_deals = fetch_deals
        self._fetch_account = fetch_account
        self._ingestion_batch_id = ingestion_batch_id
        self._resolved_account_type: AccountType | None = account_type

    @property
    def source_system(self) -> str:
        return SOURCE_SYSTEM

    def _run(self, coro):
        return asyncio.run(coro)

    def _load_deals(self) -> list[dict[str, Any]]:
        if self._fetch_deals is not None:
            return list(self._fetch_deals())
        assert self._client is not None
        return list(self._run(self._client.deals(days=self._days)))

    def _load_account(self) -> dict[str, Any]:
        if self._fetch_account is not None:
            return dict(self._fetch_account())
        if self._client is None:
            return {}
        try:
            return dict(self._run(self._client.account()))
        except Exception as e:  # noqa: BLE001 — account type is best-effort
            logger.warning("Bridge /account unavailable; defaulting account_type: %s", e)
            return {}

    def _account_type(self) -> AccountType:
        if self._resolved_account_type is not None:
            return self._resolved_account_type
        self._resolved_account_type = resolve_account_type(self._load_account())
        return self._resolved_account_type

    def fetch_pending(
        self,
        *,
        ea_profile_id: UUID | None = None,
        limit: int = 100,
    ) -> list[EvidenceItem]:
        """Return bridge deals not yet stored (by ticket / external_id)."""
        limit = max(1, int(limit))
        account_type = self._account_type()
        out: list[EvidenceItem] = []
        for deal in self._load_deals():
            if len(out) >= limit:
                break
            ticket = deal.get("ticket")
            if ticket is None:
                continue
            external_id = str(ticket)
            if self._store.has_evidence_by_external_id(SOURCE_SYSTEM, external_id):
                continue
            magic_raw = deal.get("magic")
            try:
                magic = int(magic_raw if magic_raw is not None else 0)
            except (TypeError, ValueError):
                magic = 0
            profile = ensure_ea_profile_for_magic(self._store, magic)
            if ea_profile_id is not None and profile.id != ea_profile_id:
                continue
            out.append(
                map_deal_to_evidence(
                    deal,
                    ea_profile_id=profile.id,
                    account_type=account_type,
                    ingestion_batch_id=self._ingestion_batch_id,
                )
            )
        return out

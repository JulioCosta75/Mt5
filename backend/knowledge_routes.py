"""Gate 5 Stage 2 — flag-gated read-only Knowledge HTTP surface.

Mounted on backend/server.py under ``/api/knowledge/v1``. When
``PHASE3_KNOWLEDGE_ENGINE_ENABLED`` is false, every route returns 404 —
the feature is not discoverable. No writes. SQLite work runs in
``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

REPO_ROOT = Path(__file__).resolve().parents[1]
_repo_s = str(REPO_ROOT)
if _repo_s not in sys.path:
    sys.path.insert(0, _repo_s)

API_PREFIX = "/api/knowledge/v1"

router = APIRouter(prefix=API_PREFIX, tags=["knowledge"])


def _phase3_enabled() -> bool:
    return os.environ.get("PHASE3_KNOWLEDGE_ENGINE_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )


def _require_enabled() -> None:
    if not _phase3_enabled():
        raise HTTPException(status_code=404, detail="Not found")


def _db_path() -> str:
    return os.environ.get("PHASE3_KNOWLEDGE_DB_PATH", "knowledge.db")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _load_insights_sync(
    account_id: str,
    session: str | None,
    symbol: str | None,
) -> dict[str, Any]:
    from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
    from phase3_knowledge_engine.insights import CurrentContext, list_insights, resolve_account

    repo = KnowledgeRepository(_db_path())
    profile = resolve_account(repo, account_id)
    if profile is None:
        return {
            "account_id": account_id,
            "ea_key": None,
            "insights": [],
            "counts": {"validated": 0, "active_now": 0},
        }
    current = None
    if session or symbol:
        current = CurrentContext(session=session, symbol=symbol)
    rows = list_insights(
        repository=repo,
        ea_profile_id=profile.id,
        current_context=current,
    )
    payload = []
    active = 0
    for row in rows:
        if row.is_context_active_now:
            active += 1
        payload.append(
            {
                "knowledge_record_id": str(row.knowledge_record_id),
                "statement": row.statement,
                "sample_size": row.sample_size,
                "confidence_score": row.confidence_score,
                "last_reviewed_at": _iso(row.last_reviewed_at),
                "context_signature": row.context_signature,
                "is_context_active_now": row.is_context_active_now,
                "is_stale": row.is_stale,
                "formatted": row.formatted,
            }
        )
    return {
        "account_id": account_id,
        "ea_key": profile.ea_key,
        "insights": payload,
        "counts": {"validated": len(payload), "active_now": active},
    }


def _load_graveyard_sync(account_id: str) -> dict[str, Any]:
    from phase3_knowledge_engine.graveyard import list_graveyard
    from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
    from phase3_knowledge_engine.insights import resolve_account

    repo = KnowledgeRepository(_db_path())
    profile = resolve_account(repo, account_id)
    if profile is None:
        return {
            "account_id": account_id,
            "ea_key": None,
            "entries": [],
            "count": 0,
        }
    rows = list_graveyard(repository=repo, ea_profile_id=profile.id)
    payload = [
        {
            "knowledge_record_id": str(row.knowledge_record_id),
            "statement": row.statement,
            "invalidated_at": _iso(row.invalidated_at),
            "decided_by": row.decided_by,
            "justification": row.justification,
            "formatted": row.formatted,
        }
        for row in rows
    ]
    return {
        "account_id": account_id,
        "ea_key": profile.ea_key,
        "entries": payload,
        "count": len(payload),
    }


def _load_correlation_sync(account_id: str, ea_a: str, ea_b: str) -> dict[str, Any]:
    from phase3_knowledge_engine.correlation import STATUS_INSUFFICIENT, correlate_ea_pair
    from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository

    repo = KnowledgeRepository(_db_path())
    result = correlate_ea_pair(
        repository=repo,
        account=account_id,
        ea_a=ea_a,
        ea_b=ea_b,
    )
    return {
        "account_id": account_id,
        "ea_a_key": result.ea_a_key,
        "ea_b_key": result.ea_b_key,
        "status": result.status,
        "coincidence": result.coincidence,
        "is_paired": result.is_paired,
        "negative_days_a": result.negative_days_a,
        "negative_days_b": result.negative_days_b,
        "coinciding_days": result.coinciding_days,
        "union_days": result.union_days,
        "threshold": result.threshold,
        "reason": result.reason,
        "insufficient": result.status == STATUS_INSUFFICIENT,
    }


@router.get("/status")
async def knowledge_status() -> dict[str, bool]:
    _require_enabled()
    return {"enabled": True}


@router.get("/insights")
async def knowledge_insights(
    account_id: str = Query(..., min_length=1),
    session: str | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    _require_enabled()
    return await asyncio.to_thread(_load_insights_sync, account_id, session, symbol)


@router.get("/graveyard")
async def knowledge_graveyard(
    account_id: str = Query(..., min_length=1),
) -> dict[str, Any]:
    _require_enabled()
    return await asyncio.to_thread(_load_graveyard_sync, account_id)


@router.get("/correlation")
async def knowledge_correlation(
    account_id: str = Query(..., min_length=1),
    ea_a: str = Query(..., min_length=1),
    ea_b: str = Query(..., min_length=1),
) -> dict[str, Any]:
    _require_enabled()
    return await asyncio.to_thread(_load_correlation_sync, account_id, ea_a, ea_b)

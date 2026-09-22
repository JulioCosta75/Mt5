"""Gate 5 Stage 2b — flag-gated read-only Knowledge HTTP surface.

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


def _empty_counts() -> dict[str, int]:
    return {
        "under_review": 0,
        "candidates": 0,
        "validated": 0,
        "graveyard": 0,
    }


def _serialize_record(record: Any, grave_by_id: dict[str, Any]) -> dict[str, Any]:
    from phase3_knowledge_engine.domain.validation_states import ValidationState
    from phase3_knowledge_engine.insights import is_knowledge_stale

    rid = str(record.id)
    grave = grave_by_id.get(rid)
    state = record.validation_state
    is_knowledge = state == ValidationState.KNOWLEDGE.value
    return {
        "knowledge_record_id": rid,
        "validation_state": state,
        "statement": record.statement,
        "evidence_count": record.evidence_count,
        "sample_size": record.sample_size,
        "confidence_score": record.confidence_score,
        "context_signature": record.context_signature,
        "last_reviewed_at": _iso(record.last_reviewed_at),
        "is_stale": is_knowledge_stale(record.last_reviewed_at) if is_knowledge else False,
        "decided_by": grave.decided_by if grave is not None else None,
        "justification": grave.justification if grave is not None else None,
        "invalidated_at": _iso(grave.invalidated_at) if grave is not None else None,
    }


def _load_ea_profiles_sync(account_id: str) -> dict[str, Any]:
    """Return EA dossiers when ``account_id`` resolves; otherwise an empty list.

    Phase 3 has no MT5 login on profiles. A resolved account is the admission
    ticket to this knowledge.db, so every stored EA profile is returned — that
    is what lets the Revolution screen group multiple dossiers. Unknown
    account → profiles:[]. Records are included so the pipeline can highlight
    current validation states without a write path.
    """
    from phase3_knowledge_engine.domain.validation_states import ValidationState
    from phase3_knowledge_engine.graveyard import list_graveyard
    from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository
    from phase3_knowledge_engine.insights import resolve_account

    repo = KnowledgeRepository(_db_path())
    matched = resolve_account(repo, account_id)
    if matched is None:
        return {
            "account_id": account_id,
            "ea_key": None,
            "profiles": [],
            "counts": _empty_counts(),
        }

    graves = list_graveyard(repository=repo, ea_profile_id=None)
    grave_by_id = {str(entry.knowledge_record_id): entry for entry in graves}

    records_by_ea: dict[str, list[Any]] = {}
    for state in ValidationState:
        for record in repo.list_knowledge_records_by_state(state, limit=1000):
            records_by_ea.setdefault(str(record.ea_profile_id), []).append(record)

    counts = _empty_counts()
    profiles = []
    for profile in repo.list_ea_profiles():
        rows = records_by_ea.get(str(profile.id), [])
        serialized = [_serialize_record(row, grave_by_id) for row in rows]
        for row in serialized:
            state = row["validation_state"]
            if state == ValidationState.EVIDENCE_UNDER_REVIEW.value:
                counts["under_review"] += 1
            elif state == ValidationState.KNOWLEDGE_CANDIDATE.value:
                counts["candidates"] += 1
            elif state == ValidationState.KNOWLEDGE.value:
                counts["validated"] += 1
            elif state == ValidationState.INVALIDATED_CONCLUSION.value:
                counts["graveyard"] += 1
        profiles.append(
            {
                "id": str(profile.id),
                "ea_key": profile.ea_key,
                "name": profile.name,
                "version": profile.version,
                "purpose": profile.purpose,
                "entry_rules": profile.entry_rules,
                "exit_rules": profile.exit_rules,
                "risk_rules": profile.risk_rules,
                "permitted_symbols": list(profile.permitted_symbols or []),
                "permitted_sessions": list(profile.permitted_sessions or []),
                "status": profile.status,
                "records": serialized,
            }
        )
    return {
        "account_id": account_id,
        "ea_key": matched.ea_key,
        "profiles": profiles,
        "counts": counts,
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


@router.get("/ea-profiles")
async def knowledge_ea_profiles(
    account_id: str = Query(..., min_length=1),
) -> dict[str, Any]:
    _require_enabled()
    return await asyncio.to_thread(_load_ea_profiles_sync, account_id)

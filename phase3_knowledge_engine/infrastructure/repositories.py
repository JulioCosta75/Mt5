"""SQLite persistence for Phase 3 — separate knowledge.db only."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from phase3_knowledge_engine.domain.entities import (
    AuditTrailEntry,
    EAKnowledgeProfile,
    EvidenceItem,
    EvidenceImpactRecord,
    KnowledgeRecord,
    MarketContext,
)
from phase3_knowledge_engine.domain.validation_states import ValidationState
from phase3_knowledge_engine.domain.rules import DomainRuleViolation
from phase3_knowledge_engine.domain.validation_states import can_transition


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _uuid() -> UUID:
    return uuid4()


class KnowledgeRepository:
    """SQLite repository — isolated from atlas.db."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        cx = sqlite3.connect(self.db_path)
        cx.row_factory = sqlite3.Row
        cx.execute("PRAGMA foreign_keys = ON")
        return cx

    def _init_schema(self) -> None:
        schema_file = Path(__file__).with_name("schema.sql")
        ddl = schema_file.read_text(encoding="utf-8")
        with self._connect() as cx:
            cx.executescript(ddl)

    # ---- EA profiles ---------------------------------------------------------
    def save_ea_profile(self, profile: EAKnowledgeProfile) -> EAKnowledgeProfile:
        now = _utcnow()
        if profile.created_at is None:
            profile.created_at = now
        profile.updated_at = now
        with self._connect() as cx:
            cx.execute(
                """
                INSERT INTO ea_profiles (
                    id, ea_key, name, version, purpose, entry_rules, exit_rules,
                    risk_rules_json, permitted_symbols, permitted_sessions,
                    market_conditions, status, known_strengths, known_weaknesses,
                    created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, version=excluded.version,
                    purpose=excluded.purpose, entry_rules=excluded.entry_rules,
                    exit_rules=excluded.exit_rules, risk_rules_json=excluded.risk_rules_json,
                    permitted_symbols=excluded.permitted_symbols,
                    permitted_sessions=excluded.permitted_sessions,
                    market_conditions=excluded.market_conditions,
                    status=excluded.status, known_strengths=excluded.known_strengths,
                    known_weaknesses=excluded.known_weaknesses, updated_at=excluded.updated_at
                """,
                (
                    str(profile.id), profile.ea_key, profile.name, profile.version,
                    profile.purpose, profile.entry_rules, profile.exit_rules,
                    json.dumps(profile.risk_rules),
                    json.dumps(profile.permitted_symbols),
                    json.dumps(profile.permitted_sessions),
                    json.dumps(profile.market_conditions),
                    profile.status,
                    json.dumps(profile.known_strengths),
                    json.dumps(profile.known_weaknesses),
                    _iso(profile.created_at), _iso(profile.updated_at),
                ),
            )
        return profile

    def get_ea_profile(self, profile_id: UUID) -> EAKnowledgeProfile | None:
        with self._connect() as cx:
            row = cx.execute(
                "SELECT * FROM ea_profiles WHERE id = ?", (str(profile_id),)
            ).fetchone()
        if not row:
            return None
        return EAKnowledgeProfile(
            id=UUID(row["id"]),
            ea_key=row["ea_key"],
            name=row["name"],
            version=row["version"],
            purpose=row["purpose"],
            entry_rules=row["entry_rules"],
            exit_rules=row["exit_rules"],
            risk_rules=json.loads(row["risk_rules_json"]),
            permitted_symbols=json.loads(row["permitted_symbols"]),
            permitted_sessions=json.loads(row["permitted_sessions"]),
            market_conditions=json.loads(row["market_conditions"]),
            status=row["status"],
            known_strengths=json.loads(row["known_strengths"]),
            known_weaknesses=json.loads(row["known_weaknesses"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # ---- Evidence ------------------------------------------------------------
    def save_evidence(self, item: EvidenceItem) -> EvidenceItem:
        context_id = None
        if item.context:
            context_id = str(self._save_context(item.context))
        with self._connect() as cx:
            cx.execute(
                """
                INSERT INTO evidence_items (
                    id, ea_profile_id, evidence_type, occurred_at, symbol,
                    session, market_regime, volatility, spread, pnl, drawdown,
                    entry_reason, exit_reason, ea_version, account_type, test_type,
                    raw_payload_json, context_id, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(item.id), str(item.ea_profile_id), item.evidence_type,
                    _iso(item.occurred_at), item.symbol, item.session,
                    item.market_regime, item.volatility, item.spread,
                    item.pnl, item.drawdown, item.entry_reason, item.exit_reason,
                    item.ea_version, item.account_type, item.test_type,
                    json.dumps(item.raw_payload), context_id, _iso(_utcnow()),
                ),
            )
        return item

    def _save_context(self, ctx: MarketContext) -> UUID:
        cid = _uuid()
        with self._connect() as cx:
            cx.execute(
                """
                INSERT INTO market_contexts (
                    id, session, market_regime, volatility, spread,
                    symbol, occurred_at, weekday, notes
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(cid), ctx.session, ctx.market_regime, ctx.volatility,
                    ctx.spread, ctx.symbol,
                    _iso(ctx.occurred_at) if ctx.occurred_at else None,
                    ctx.weekday, ctx.notes,
                ),
            )
        return cid

    def count_observations_for_ea(self, ea_profile_id: UUID) -> int:
        with self._connect() as cx:
            row = cx.execute(
                "SELECT COUNT(*) AS c FROM evidence_items WHERE ea_profile_id = ?",
                (str(ea_profile_id),),
            ).fetchone()
        return int(row["c"])

    # ---- Knowledge records ---------------------------------------------------
    def save_knowledge_record(self, record: KnowledgeRecord) -> KnowledgeRecord:
        now = _utcnow()
        if record.created_at is None:
            record.created_at = now
        record.updated_at = now
        with self._connect() as cx:
            cx.execute(
                """
                INSERT INTO knowledge_records (
                    id, ea_profile_id, validation_state, statement,
                    evidence_count, sample_size, date_range_start, date_range_end,
                    confidence_score, supporting_evidence_ids_json,
                    contradictory_evidence_ids_json, last_reviewed_at, reviewed_by,
                    relevance_for_decisions, context_documented,
                    material_contradictions_resolved, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    validation_state=excluded.validation_state,
                    statement=excluded.statement,
                    evidence_count=excluded.evidence_count,
                    sample_size=excluded.sample_size,
                    date_range_start=excluded.date_range_start,
                    date_range_end=excluded.date_range_end,
                    confidence_score=excluded.confidence_score,
                    supporting_evidence_ids_json=excluded.supporting_evidence_ids_json,
                    contradictory_evidence_ids_json=excluded.contradictory_evidence_ids_json,
                    last_reviewed_at=excluded.last_reviewed_at,
                    reviewed_by=excluded.reviewed_by,
                    relevance_for_decisions=excluded.relevance_for_decisions,
                    context_documented=excluded.context_documented,
                    material_contradictions_resolved=excluded.material_contradictions_resolved,
                    updated_at=excluded.updated_at
                """,
                (
                    str(record.id), str(record.ea_profile_id), record.validation_state,
                    record.statement, record.evidence_count, record.sample_size,
                    record.date_range_start.isoformat() if record.date_range_start else None,
                    record.date_range_end.isoformat() if record.date_range_end else None,
                    record.confidence_score,
                    json.dumps([str(x) for x in record.supporting_evidence_ids]),
                    json.dumps([str(x) for x in record.contradictory_evidence_ids]),
                    _iso(record.last_reviewed_at) if record.last_reviewed_at else None,
                    record.reviewed_by, record.relevance_for_decisions,
                    1 if record.context_documented else 0,
                    1 if record.material_contradictions_resolved else 0,
                    _iso(record.created_at), _iso(record.updated_at),
                ),
            )
        return record

    def get_knowledge_record(self, record_id: UUID) -> KnowledgeRecord | None:
        with self._connect() as cx:
            row = cx.execute(
                "SELECT * FROM knowledge_records WHERE id = ?", (str(record_id),)
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def _row_to_record(self, row: sqlite3.Row) -> KnowledgeRecord:
        return KnowledgeRecord(
            id=UUID(row["id"]),
            ea_profile_id=UUID(row["ea_profile_id"]),
            validation_state=row["validation_state"],
            statement=row["statement"],
            evidence_count=row["evidence_count"],
            sample_size=row["sample_size"],
            date_range_start=(
                datetime.fromisoformat(row["date_range_start"]).date()
                if row["date_range_start"] else None
            ),
            date_range_end=(
                datetime.fromisoformat(row["date_range_end"]).date()
                if row["date_range_end"] else None
            ),
            confidence_score=row["confidence_score"],
            supporting_evidence_ids=[UUID(x) for x in json.loads(row["supporting_evidence_ids_json"])],
            contradictory_evidence_ids=[UUID(x) for x in json.loads(row["contradictory_evidence_ids_json"])],
            last_reviewed_at=(
                datetime.fromisoformat(row["last_reviewed_at"])
                if row["last_reviewed_at"] else None
            ),
            reviewed_by=row["reviewed_by"],
            relevance_for_decisions=row["relevance_for_decisions"],
            context_documented=bool(row["context_documented"]),
            material_contradictions_resolved=bool(row["material_contradictions_resolved"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # ---- Audit trail ---------------------------------------------------------
    def append_audit(self, entry: AuditTrailEntry) -> AuditTrailEntry:
        with self._connect() as cx:
            cx.execute(
                """
                INSERT INTO audit_trail (
                    id, knowledge_record_id, from_state, to_state,
                    transitioned_at, actor, justification, evidence_ids_json
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    str(entry.id), str(entry.knowledge_record_id),
                    entry.from_state, entry.to_state, _iso(entry.transitioned_at),
                    entry.actor, entry.justification,
                    json.dumps([str(x) for x in entry.evidence_ids]),
                ),
            )
        return entry

    def list_audit_trail(self, knowledge_record_id: UUID) -> list[AuditTrailEntry]:
        with self._connect() as cx:
            rows = cx.execute(
                "SELECT * FROM audit_trail WHERE knowledge_record_id = ? ORDER BY transitioned_at",
                (str(knowledge_record_id),),
            ).fetchall()
        return [
            AuditTrailEntry(
                id=UUID(r["id"]),
                knowledge_record_id=UUID(r["knowledge_record_id"]),
                from_state=r["from_state"],
                to_state=r["to_state"],
                transitioned_at=datetime.fromisoformat(r["transitioned_at"]),
                actor=r["actor"],
                justification=r["justification"],
                evidence_ids=[UUID(x) for x in json.loads(r["evidence_ids_json"])],
            )
            for r in rows
        ]

    def append_evidence_impact(self, impact: EvidenceImpactRecord) -> EvidenceImpactRecord:
        with self._connect() as cx:
            cx.execute(
                """
                INSERT INTO evidence_impacts (
                    id, knowledge_record_id, evidence_id, impact,
                    recorded_at, actor, notes
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    str(impact.id), str(impact.knowledge_record_id),
                    str(impact.evidence_id), impact.impact,
                    _iso(impact.recorded_at), impact.actor, impact.notes,
                ),
            )
        return impact

    def transition_state(
        self,
        record_id: UUID,
        to_state: ValidationState,
        *,
        actor: str,
        justification: str,
        evidence_ids: list[UUID] | None = None,
        human_review_recorded: bool = False,
    ) -> KnowledgeRecord:
        record = self.get_knowledge_record(record_id)
        if not record:
            raise DomainRuleViolation(f"Knowledge record {record_id} not found.")
        from_state = ValidationState(record.validation_state)
        if not can_transition(from_state, to_state, human_review_recorded=human_review_recorded):
            raise DomainRuleViolation(
                f"Illegal transition {from_state.value} -> {to_state.value} "
                f"(human_review_recorded={human_review_recorded})."
            )
        record.validation_state = to_state.value
        if human_review_recorded:
            record.last_reviewed_at = _utcnow()
            record.reviewed_by = actor
        self.save_knowledge_record(record)
        self.append_audit(AuditTrailEntry(
            id=_uuid(),
            knowledge_record_id=record_id,
            from_state=from_state.value,
            to_state=to_state.value,
            transitioned_at=_utcnow(),
            actor=actor,
            justification=justification,
            evidence_ids=evidence_ids or [],
        ))
        return record

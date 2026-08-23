"""SQLite persistence for Phase 3 — separate knowledge.db only."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager, nullcontext
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

    @contextmanager
    def _connection(self):
        cx = self._connect()
        try:
            with cx:
                yield cx
        finally:
            cx.close()

    def _init_schema(self) -> None:
        schema_file = Path(__file__).with_name("schema.sql")
        ddl = schema_file.read_text(encoding="utf-8")
        with self._connection() as cx:
            cx.executescript(ddl)
        self._run_migrations()

    def _schema_version(self) -> int:
        with self._connection() as cx:
            row = cx.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'",
            ).fetchone()
        return int(row["value"]) if row else 1

    def _run_migrations(self) -> None:
        version = self._schema_version()
        if version < 2:
            with self._connection() as cx:
                columns = {
                    r[1] for r in cx.execute("PRAGMA table_info(evidence_items)").fetchall()
                }
                if "source_system" not in columns:
                    cx.execute(
                        "ALTER TABLE evidence_items ADD COLUMN "
                        "source_system TEXT NOT NULL DEFAULT 'manual'"
                    )
                if "external_id" not in columns:
                    cx.execute(
                        "ALTER TABLE evidence_items ADD COLUMN external_id TEXT"
                    )
                if "ingestion_batch_id" not in columns:
                    cx.execute(
                        "ALTER TABLE evidence_items ADD COLUMN ingestion_batch_id TEXT"
                    )
                cx.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_source_external
                    ON evidence_items(source_system, external_id)
                    WHERE external_id IS NOT NULL
                    """
                )
                cx.execute(
                    "UPDATE schema_meta SET value = '2' WHERE key = 'schema_version'"
                )
            version = 2
        if version < 3:
            with self._connection() as cx:
                columns = {
                    r[1]
                    for r in cx.execute("PRAGMA table_info(knowledge_records)").fetchall()
                }
                if "context_signature" not in columns:
                    cx.execute(
                        "ALTER TABLE knowledge_records ADD COLUMN context_signature TEXT"
                    )
                cx.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_knowledge_context_signature
                    ON knowledge_records(context_signature)
                    WHERE context_signature IS NOT NULL
                    """
                )
                cx.execute(
                    "UPDATE schema_meta SET value = '3' WHERE key = 'schema_version'"
                )

    # ---- EA profiles ---------------------------------------------------------
    def save_ea_profile(self, profile: EAKnowledgeProfile) -> EAKnowledgeProfile:
        now = _utcnow()
        if profile.created_at is None:
            profile.created_at = now
        profile.updated_at = now
        with self._connection() as cx:
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
        with self._connection() as cx:
            row = cx.execute(
                "SELECT * FROM ea_profiles WHERE id = ?", (str(profile_id),)
            ).fetchone()
        if not row:
            return None
        return self._row_to_ea_profile(row)

    def get_ea_profile_by_ea_key(self, ea_key: str) -> EAKnowledgeProfile | None:
        with self._connection() as cx:
            row = cx.execute(
                "SELECT * FROM ea_profiles WHERE ea_key = ?", (ea_key,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_ea_profile(row)

    @staticmethod
    def _row_to_ea_profile(row: sqlite3.Row) -> EAKnowledgeProfile:
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
        """Persist evidence. Idempotent on (source_system, external_id) when set."""
        if item.external_id:
            existing = self.get_evidence_by_external_id(
                item.source_system, item.external_id
            )
            if existing is not None:
                return existing
        context_id = None
        if item.context:
            context_id = str(self._save_context(item.context))
        with self._connection() as cx:
            try:
                cx.execute(
                    """
                    INSERT INTO evidence_items (
                        id, ea_profile_id, evidence_type, occurred_at, symbol,
                        session, market_regime, volatility, spread, pnl, drawdown,
                        entry_reason, exit_reason, ea_version, account_type, test_type,
                        raw_payload_json, context_id, source_system, external_id,
                        ingestion_batch_id, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        str(item.id), str(item.ea_profile_id), item.evidence_type,
                        _iso(item.occurred_at), item.symbol, item.session,
                        item.market_regime, item.volatility, item.spread,
                        item.pnl, item.drawdown, item.entry_reason, item.exit_reason,
                        item.ea_version, item.account_type, item.test_type,
                        json.dumps(item.raw_payload), context_id, item.source_system,
                        item.external_id, item.ingestion_batch_id, _iso(_utcnow()),
                    ),
                )
            except sqlite3.IntegrityError:
                if item.external_id:
                    existing = self.get_evidence_by_external_id(
                        item.source_system, item.external_id
                    )
                    if existing is not None:
                        return existing
                raise
        return item

    def has_evidence_by_external_id(
        self, source_system: str, external_id: str
    ) -> bool:
        return self.get_evidence_by_external_id(source_system, external_id) is not None

    def get_evidence_by_external_id(
        self, source_system: str, external_id: str
    ) -> EvidenceItem | None:
        with self._connection() as cx:
            row = cx.execute(
                """
                SELECT * FROM evidence_items
                 WHERE source_system = ? AND external_id = ?
                """,
                (source_system, external_id),
            ).fetchone()
        if not row:
            return None
        return self._row_to_evidence(row)

    def get_evidence(self, evidence_id: UUID) -> EvidenceItem | None:
        with self._connection() as cx:
            row = cx.execute(
                "SELECT * FROM evidence_items WHERE id = ?", (str(evidence_id),),
            ).fetchone()
        if not row:
            return None
        return self._row_to_evidence(row)

    def _row_to_evidence(self, row: sqlite3.Row) -> EvidenceItem:
        return EvidenceItem(
            id=UUID(row["id"]),
            ea_profile_id=UUID(row["ea_profile_id"]),
            evidence_type=row["evidence_type"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
            symbol=row["symbol"],
            session=row["session"],
            market_regime=row["market_regime"],
            volatility=row["volatility"],
            spread=row["spread"],
            pnl=row["pnl"],
            drawdown=row["drawdown"],
            entry_reason=row["entry_reason"],
            exit_reason=row["exit_reason"],
            ea_version=row["ea_version"],
            account_type=row["account_type"],
            test_type=row["test_type"],
            raw_payload=json.loads(row["raw_payload_json"]),
            source_system=row["source_system"],
            external_id=row["external_id"],
            ingestion_batch_id=row["ingestion_batch_id"],
        )

    def _save_context(self, ctx: MarketContext) -> UUID:
        cid = _uuid()
        with self._connection() as cx:
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
        with self._connection() as cx:
            row = cx.execute(
                "SELECT COUNT(*) AS c FROM evidence_items WHERE ea_profile_id = ?",
                (str(ea_profile_id),),
            ).fetchone()
        return int(row["c"])

    # ---- Knowledge records ---------------------------------------------------
    def save_knowledge_record(
        self,
        record: KnowledgeRecord,
        *,
        _connection: sqlite3.Connection | None = None,
    ) -> KnowledgeRecord:
        now = _utcnow()
        if record.created_at is None:
            record.created_at = now
        record.updated_at = now
        with (
            nullcontext(_connection) if _connection is not None else self._connection()
        ) as cx:
            cx.execute(
                """
                INSERT INTO knowledge_records (
                    id, ea_profile_id, validation_state, statement,
                    evidence_count, sample_size, date_range_start, date_range_end,
                    confidence_score, supporting_evidence_ids_json,
                    contradictory_evidence_ids_json, last_reviewed_at, reviewed_by,
                    relevance_for_decisions, context_documented,
                    material_contradictions_resolved, context_signature,
                    created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                    context_signature=excluded.context_signature,
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
                    record.context_signature,
                    _iso(record.created_at), _iso(record.updated_at),
                ),
            )
        return record

    def get_knowledge_record(self, record_id: UUID) -> KnowledgeRecord | None:
        with self._connection() as cx:
            row = cx.execute(
                "SELECT * FROM knowledge_records WHERE id = ?", (str(record_id),)
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def find_knowledge_record_by_signature(
        self, context_signature: str
    ) -> KnowledgeRecord | None:
        """Match RAW_OBSERVATION / REPEATED_PATTERN only (pre-hypothesis grouping)."""
        if not context_signature:
            return None
        with self._connection() as cx:
            row = cx.execute(
                """
                SELECT * FROM knowledge_records
                 WHERE context_signature = ?
                   AND validation_state IN (?, ?)
                 ORDER BY created_at ASC
                 LIMIT 1
                """,
                (
                    context_signature,
                    ValidationState.RAW_OBSERVATION.value,
                    ValidationState.REPEATED_PATTERN.value,
                ),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def find_post_hypothesis_record_by_signature(
        self, context_signature: str
    ) -> KnowledgeRecord | None:
        """Match HYPOTHESIS or later for evidence-impact routing (not grouping)."""
        if not context_signature:
            return None
        with self._connection() as cx:
            row = cx.execute(
                """
                SELECT * FROM knowledge_records
                 WHERE context_signature = ?
                   AND validation_state NOT IN (?, ?)
                 ORDER BY updated_at DESC
                 LIMIT 1
                """,
                (
                    context_signature,
                    ValidationState.RAW_OBSERVATION.value,
                    ValidationState.REPEATED_PATTERN.value,
                ),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def _row_to_record(self, row: sqlite3.Row) -> KnowledgeRecord:
        # context_signature may be absent on pre-migration rows loaded mid-flight
        keys = row.keys()
        signature = row["context_signature"] if "context_signature" in keys else None
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
            context_signature=signature,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # ---- Audit trail ---------------------------------------------------------
    def save_transition_with_audit(
        self,
        record: KnowledgeRecord,
        entry: AuditTrailEntry,
    ) -> KnowledgeRecord:
        with self._connection() as cx:
            self.save_knowledge_record(record, _connection=cx)
            self.append_audit(entry, _connection=cx)
        return record

    def append_audit(
        self,
        entry: AuditTrailEntry,
        *,
        _connection: sqlite3.Connection | None = None,
    ) -> AuditTrailEntry:
        with (
            nullcontext(_connection) if _connection is not None else self._connection()
        ) as cx:
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
        with self._connection() as cx:
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
        with self._connection() as cx:
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

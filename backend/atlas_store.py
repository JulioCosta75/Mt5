"""Persistence layer for Sr. Atlas supervision reports and alerts (Phase 2).

Backends (selected by caller):
  * MongoDB collections ``atlas_reports`` / ``atlas_alerts`` when ``mongo_db``
    is provided.
  * SQLite tables in the same ``atlas.db`` as the MT5 cache when
    ``sqlite_path`` is provided (Windows installer / ATLAS_STORE=sqlite).
  * In-memory lists otherwise (preview / offline without a store).

Every report and every alert belongs to exactly one account (``account_id``).
Aggregate cross-account snapshots are not stored here.

Migration: ``CREATE TABLE IF NOT EXISTS`` — existing ``atlas.db`` files keep
all prior tables untouched.

Secrets: reports are scrubbed before persist — password / token / connection
strings and similar keys are stripped from nested dicts/lists.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional

_SECRET_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "connection_string",
    "conn_str",
    "private_key",
    "credential",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS atlas_reports (
    id          TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    status      TEXT,
    source      TEXT,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_atlas_reports_account_created
    ON atlas_reports (account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_atlas_reports_created
    ON atlas_reports (created_at);

CREATE TABLE IF NOT EXISTS atlas_alerts (
    id               TEXT PRIMARY KEY,
    account_id       TEXT NOT NULL,
    rule_key         TEXT NOT NULL,
    state            TEXT NOT NULL,
    severity         TEXT NOT NULL,
    message          TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    acknowledged_at  TEXT,
    resolved_at      TEXT,
    payload          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_atlas_alerts_account_rule_state
    ON atlas_alerts (account_id, rule_key, state);
CREATE INDEX IF NOT EXISTS idx_atlas_alerts_state_created
    ON atlas_alerts (state, created_at DESC);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scrub_secrets(value: Any) -> Any:
    """Recursively drop keys whose names look like secrets. Never invent data."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key_l = str(k).lower()
            if any(frag in key_l for frag in _SECRET_KEY_FRAGMENTS):
                continue
            out[k] = scrub_secrets(v)
        return out
    if isinstance(value, list):
        return [scrub_secrets(v) for v in value]
    return value


class AtlasReportStore:
    def __init__(
        self,
        mongo_db=None,
        *,
        sqlite_path: str | Path | None = None,
    ):
        self._collection = None
        self._sqlite_path: Path | None = None
        self._mem: List[dict] = []

        if mongo_db is not None:
            self._collection = mongo_db["atlas_reports"]
        elif sqlite_path:
            self._sqlite_path = Path(sqlite_path)
            self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with self._cx() as cx:
                cx.executescript(_SCHEMA)

    @property
    def backend(self) -> str:
        if self._collection is not None:
            return "mongo"
        if self._sqlite_path is not None:
            return "sqlite"
        return "memory"

    @contextmanager
    def _cx(self):
        assert self._sqlite_path is not None
        cx = sqlite3.connect(str(self._sqlite_path), isolation_level=None)
        cx.row_factory = sqlite3.Row
        try:
            yield cx
        finally:
            cx.close()

    async def add(self, report: dict) -> dict:
        clean = scrub_secrets(dict(report))
        clean.setdefault("id", str(uuid.uuid4()))
        clean.setdefault("created_at", _now_iso())
        account_id = clean.get("account_id")
        if not account_id:
            raise ValueError("account_id is required — each report belongs to one account")

        if self._collection is not None:
            await self._collection.insert_one(dict(clean))
            return clean

        if self._sqlite_path is not None:
            with self._cx() as cx:
                cx.execute(
                    """
                    INSERT INTO atlas_reports
                        (id, account_id, created_at, status, source, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clean["id"],
                        str(account_id),
                        clean["created_at"],
                        clean.get("status"),
                        clean.get("source"),
                        json.dumps(clean, ensure_ascii=False),
                    ),
                )
            return clean

        self._mem.insert(0, clean)
        return clean

    async def list(
        self,
        limit: int = 50,
        status: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> List[dict]:
        limit = max(1, min(int(limit or 50), 500))

        if self._collection is not None:
            query: dict[str, Any] = {}
            if status:
                query["status"] = status.upper()
            if account_id:
                query["account_id"] = account_id
            cursor = (
                self._collection.find(query, {"_id": 0})
                .sort("created_at", -1)
                .limit(limit)
            )
            return await cursor.to_list(length=limit)

        if self._sqlite_path is not None:
            clauses: list[str] = []
            params: list[Any] = []
            if status:
                clauses.append("status = ?")
                params.append(status.upper())
            if account_id:
                clauses.append("account_id = ?")
                params.append(account_id)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            with self._cx() as cx:
                rows = cx.execute(
                    f"""
                    SELECT payload FROM atlas_reports
                    {where}
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    params,
                ).fetchall()
            return [json.loads(r["payload"]) for r in rows]

        items = self._mem
        if status:
            items = [r for r in items if r.get("status") == status.upper()]
        if account_id:
            items = [r for r in items if r.get("account_id") == account_id]
        return items[:limit]

    async def count(
        self,
        status: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> int:
        if self._collection is not None:
            query: dict[str, Any] = {}
            if status:
                query["status"] = status.upper()
            if account_id:
                query["account_id"] = account_id
            return await self._collection.count_documents(query)

        if self._sqlite_path is not None:
            clauses: list[str] = []
            params: list[Any] = []
            if status:
                clauses.append("status = ?")
                params.append(status.upper())
            if account_id:
                clauses.append("account_id = ?")
                params.append(account_id)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            with self._cx() as cx:
                row = cx.execute(
                    f"SELECT COUNT(*) AS n FROM atlas_reports {where}", params
                ).fetchone()
            return int(row["n"]) if row else 0

        items = self._mem
        if status:
            items = [r for r in items if r.get("status") == status.upper()]
        if account_id:
            items = [r for r in items if r.get("account_id") == account_id]
        return len(items)

    async def latest_for_account(self, account_id: str) -> dict | None:
        rows = await self.list(limit=1, account_id=account_id)
        return rows[0] if rows else None

    async def purge_older_than(self, retention_days: int) -> int:
        """Delete reports older than ``retention_days``. Returns deleted count."""
        days = max(1, int(retention_days))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        if self._collection is not None:
            result = await self._collection.delete_many(
                {"created_at": {"$lt": cutoff_iso}}
            )
            return int(getattr(result, "deleted_count", 0) or 0)

        if self._sqlite_path is not None:
            with self._cx() as cx:
                cur = cx.execute(
                    "DELETE FROM atlas_reports WHERE created_at < ?",
                    (cutoff_iso,),
                )
                return int(cur.rowcount or 0)

        before = len(self._mem)
        self._mem = [
            r for r in self._mem
            if str(r.get("created_at") or "") >= cutoff_iso
        ]
        return before - len(self._mem)


class AtlasAlertStore:
    """Persist fixed-rule alerts with active → acknowledged → resolved states."""

    _OPEN_STATES = ("active", "acknowledged")

    def __init__(
        self,
        mongo_db=None,
        *,
        sqlite_path: str | Path | None = None,
    ):
        self._collection = None
        self._sqlite_path: Path | None = None
        self._mem: List[dict] = []

        if mongo_db is not None:
            self._collection = mongo_db["atlas_alerts"]
        elif sqlite_path:
            self._sqlite_path = Path(sqlite_path)
            self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with self._cx() as cx:
                cx.executescript(_SCHEMA)

    @property
    def backend(self) -> str:
        if self._collection is not None:
            return "mongo"
        if self._sqlite_path is not None:
            return "sqlite"
        return "memory"

    @contextmanager
    def _cx(self):
        assert self._sqlite_path is not None
        cx = sqlite3.connect(str(self._sqlite_path), isolation_level=None)
        cx.row_factory = sqlite3.Row
        try:
            yield cx
        finally:
            cx.close()

    def _row_from_payload(self, payload: str | dict) -> dict:
        if isinstance(payload, dict):
            return dict(payload)
        return json.loads(payload)

    async def create(self, candidate: dict) -> dict:
        account_id = candidate.get("account_id")
        rule_key = candidate.get("rule_key")
        if not account_id or not rule_key:
            raise ValueError("account_id and rule_key are required")

        now = _now_iso()
        doc = {
            "id": str(uuid.uuid4()),
            "account_id": str(account_id),
            "rule_key": str(rule_key),
            "state": "active",
            "severity": str(candidate.get("severity") or "WARNING"),
            "message": str(candidate.get("message") or ""),
            "created_at": now,
            "updated_at": now,
            "acknowledged_at": None,
            "resolved_at": None,
        }
        clean = scrub_secrets(doc)

        if self._collection is not None:
            await self._collection.insert_one(dict(clean))
            return clean

        if self._sqlite_path is not None:
            with self._cx() as cx:
                cx.execute(
                    """
                    INSERT INTO atlas_alerts (
                        id, account_id, rule_key, state, severity, message,
                        created_at, updated_at, acknowledged_at, resolved_at, payload
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        clean["id"],
                        clean["account_id"],
                        clean["rule_key"],
                        clean["state"],
                        clean["severity"],
                        clean["message"],
                        clean["created_at"],
                        clean["updated_at"],
                        clean["acknowledged_at"],
                        clean["resolved_at"],
                        json.dumps(clean, ensure_ascii=False),
                    ),
                )
            return clean

        self._mem.insert(0, clean)
        return clean

    async def get(self, alert_id: str) -> dict | None:
        if self._collection is not None:
            doc = await self._collection.find_one({"id": alert_id}, {"_id": 0})
            return dict(doc) if doc else None

        if self._sqlite_path is not None:
            with self._cx() as cx:
                row = cx.execute(
                    "SELECT payload FROM atlas_alerts WHERE id = ?",
                    (alert_id,),
                ).fetchone()
            return self._row_from_payload(row["payload"]) if row else None

        for a in self._mem:
            if a.get("id") == alert_id:
                return dict(a)
        return None

    async def list_open(self, account_id: Optional[str] = None) -> List[dict]:
        return await self.list(
            account_id=account_id,
            states=list(self._OPEN_STATES),
            limit=500,
        )

    async def list(
        self,
        *,
        account_id: Optional[str] = None,
        severity: Optional[str] = None,
        states: Optional[list[str]] = None,
        limit: int = 100,
    ) -> List[dict]:
        limit = max(1, min(int(limit or 100), 500))
        state_filter = list(states) if states is not None else None

        if self._collection is not None:
            query: dict[str, Any] = {}
            if account_id:
                query["account_id"] = account_id
            if severity:
                query["severity"] = severity.upper()
            if state_filter is not None:
                query["state"] = {"$in": state_filter}
            cursor = (
                self._collection.find(query, {"_id": 0})
                .sort("created_at", -1)
                .limit(limit)
            )
            return await cursor.to_list(length=limit)

        if self._sqlite_path is not None:
            clauses: list[str] = []
            params: list[Any] = []
            if account_id:
                clauses.append("account_id = ?")
                params.append(account_id)
            if severity:
                clauses.append("severity = ?")
                params.append(severity.upper())
            if state_filter is not None:
                placeholders = ", ".join("?" for _ in state_filter)
                clauses.append(f"state IN ({placeholders})")
                params.extend(state_filter)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            params.append(limit)
            with self._cx() as cx:
                rows = cx.execute(
                    f"""
                    SELECT payload FROM atlas_alerts
                    {where}
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    params,
                ).fetchall()
            return [self._row_from_payload(r["payload"]) for r in rows]

        items = list(self._mem)
        if account_id:
            items = [a for a in items if a.get("account_id") == account_id]
        if severity:
            sev = severity.upper()
            items = [a for a in items if a.get("severity") == sev]
        if state_filter is not None:
            allowed = set(state_filter)
            items = [a for a in items if a.get("state") in allowed]
        return items[:limit]

    async def _persist(self, doc: dict) -> dict:
        clean = scrub_secrets(dict(doc))
        clean["updated_at"] = _now_iso()

        if self._collection is not None:
            await self._collection.replace_one({"id": clean["id"]}, dict(clean), upsert=True)
            return clean

        if self._sqlite_path is not None:
            with self._cx() as cx:
                cx.execute(
                    """
                    UPDATE atlas_alerts SET
                        account_id = ?, rule_key = ?, state = ?, severity = ?,
                        message = ?, created_at = ?, updated_at = ?,
                        acknowledged_at = ?, resolved_at = ?, payload = ?
                    WHERE id = ?
                    """,
                    (
                        clean["account_id"],
                        clean["rule_key"],
                        clean["state"],
                        clean["severity"],
                        clean["message"],
                        clean["created_at"],
                        clean["updated_at"],
                        clean.get("acknowledged_at"),
                        clean.get("resolved_at"),
                        json.dumps(clean, ensure_ascii=False),
                        clean["id"],
                    ),
                )
            return clean

        for i, a in enumerate(self._mem):
            if a.get("id") == clean["id"]:
                self._mem[i] = clean
                return clean
        self._mem.insert(0, clean)
        return clean

    async def acknowledge(self, alert_id: str, acknowledged: bool = True) -> dict | None:
        doc = await self.get(alert_id)
        if doc is None:
            return None
        if doc.get("state") == "resolved":
            return doc

        if acknowledged:
            if doc.get("state") == "active":
                doc["state"] = "acknowledged"
                doc["acknowledged_at"] = _now_iso()
        else:
            if doc.get("state") == "acknowledged":
                doc["state"] = "active"
                doc["acknowledged_at"] = None
        return await self._persist(doc)

    async def resolve(self, alert_id: str) -> dict | None:
        doc = await self.get(alert_id)
        if doc is None:
            return None
        if doc.get("state") == "resolved":
            return doc
        now = _now_iso()
        doc["state"] = "resolved"
        doc["resolved_at"] = now
        return await self._persist(doc)

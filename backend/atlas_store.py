"""Persistence layer for Sr. Atlas supervision reports (Phase 2).

Works in two modes, mirroring the rest of the backend:
  * ATLAS_STORE=mongo  -> reports stored in the `atlas_reports` collection.
  * anything else / no Mongo -> in-memory fallback (installer / offline mode).

All documents use UUID string ids (never Mongo ObjectId) so they are always
JSON serialisable.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional


class AtlasReportStore:
    def __init__(self, mongo_db=None):
        self._collection = None
        self._mem: List[dict] = []
        if mongo_db is not None:
            self._collection = mongo_db["atlas_reports"]

    @property
    def backend(self) -> str:
        return "mongo" if self._collection is not None else "memory"

    async def add(self, report: dict) -> dict:
        report.setdefault("id", str(uuid.uuid4()))
        report.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        if self._collection is not None:
            # Insert a copy so the pymongo-injected _id never leaks into the
            # object we return to the caller (keeps the response JSON-safe).
            await self._collection.insert_one(dict(report))
        else:
            self._mem.insert(0, report)
        return report

    async def list(self, limit: int = 50, status: Optional[str] = None) -> List[dict]:
        limit = max(1, min(int(limit or 50), 500))
        if self._collection is not None:
            query = {}
            if status:
                query["status"] = status.upper()
            cursor = (
                self._collection.find(query, {"_id": 0})
                .sort("created_at", -1)
                .limit(limit)
            )
            return await cursor.to_list(length=limit)
        items = self._mem
        if status:
            items = [r for r in items if r.get("status") == status.upper()]
        return items[:limit]

    async def count(self, status: Optional[str] = None) -> int:
        if self._collection is not None:
            query = {}
            if status:
                query["status"] = status.upper()
            return await self._collection.count_documents(query)
        if status:
            return sum(1 for r in self._mem if r.get("status") == status.upper())
        return len(self._mem)

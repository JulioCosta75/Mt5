"""Standalone Phase 3 Gate 1 ingestion CLI (not wired into Phase 2).

Examples::

    python -m phase3_knowledge_engine.ingest --file deals.json
    python -m phase3_knowledge_engine.ingest --bridge-url http://127.0.0.1:8002 \\
        --bridge-token "$MT5_BRIDGE_TOKEN" --days 90

Read-only against the MT5 bridge. Does not enable PHASE3_KNOWLEDGE_ENGINE_ENABLED.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from uuid import uuid4

from phase3_knowledge_engine.adapters.ingestion.mt5_bridge_evidence_source import (
    SOURCE_SYSTEM,
    Mt5BridgeEvidenceSource,
    map_deal_to_evidence,
    resolve_account_type,
    ensure_ea_profile_for_magic,
)
from phase3_knowledge_engine.config import DEFAULT_KNOWLEDGE_DB_PATH
from phase3_knowledge_engine.infrastructure.repositories import KnowledgeRepository

log = logging.getLogger("phase3.ingest")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _make_bridge_client(url: str, token: str):
    """Reuse Phase 2 BridgeClient — do not invent a second HTTP client."""
    backend = _repo_root() / "backend"
    backend_s = str(backend)
    if backend_s not in sys.path:
        sys.path.insert(0, backend_s)
    from mt5_client import BridgeClient, BridgeEndpoint  # noqa: WPS433

    return BridgeClient(
        BridgeEndpoint(url=url.rstrip("/"), token=token or "", label="phase3-ingest")
    )


def _load_deals_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict) and "deals" in data:
            data = data["deals"]
        if not isinstance(data, list):
            raise ValueError("JSON deal file must be a list or {\"deals\": [...]}")
        return data
    # CSV — expect bridge-like column names
    reader = csv.DictReader(text.splitlines())
    rows = []
    for row in reader:
        cleaned = dict(row)
        for key in ("ticket", "magic", "profit", "swap", "commission", "volume", "price"):
            if key in cleaned and cleaned[key] not in (None, ""):
                try:
                    if key in ("ticket", "magic"):
                        cleaned[key] = int(float(cleaned[key]))
                    else:
                        cleaned[key] = float(cleaned[key])
                except ValueError:
                    pass
        rows.append(cleaned)
    return rows


def _persist_batch(repo: KnowledgeRepository, items) -> tuple[int, int]:
    """Save items; count new vs already-present by external_id."""
    saved = 0
    skipped = 0
    for item in items:
        if item.external_id and repo.has_evidence_by_external_id(
            item.source_system, item.external_id
        ):
            skipped += 1
            continue
        repo.save_evidence(item)
        saved += 1
    return saved, skipped


def run_bridge_ingest(
    *,
    bridge_url: str,
    bridge_token: str,
    days: int,
    db_path: str,
    limit: int,
) -> dict:
    repo = KnowledgeRepository(db_path)
    batch_id = f"bridge-{uuid4().hex[:12]}"
    client = _make_bridge_client(bridge_url, bridge_token)
    source = Mt5BridgeEvidenceSource(
        repo,
        bridge_client=client,
        days=days,
        ingestion_batch_id=batch_id,
    )
    pending = source.fetch_pending(limit=limit)
    saved, skipped = _persist_batch(repo, pending)
    return {
        "source": SOURCE_SYSTEM,
        "batch_id": batch_id,
        "fetched_pending": len(pending),
        "saved": saved,
        "skipped_duplicate": skipped,
        "db": db_path,
    }


def run_file_ingest(
    *,
    file_path: Path,
    db_path: str,
    limit: int,
    account_type: str | None,
) -> dict:
    repo = KnowledgeRepository(db_path)
    batch_id = f"file-{uuid4().hex[:12]}"
    deals = _load_deals_file(file_path)[: max(1, limit)]
    if account_type in ("demo", "live"):
        acct = account_type
    else:
        acct = resolve_account_type({})
    items = []
    for deal in deals:
        magic_raw = deal.get("magic")
        try:
            magic = int(magic_raw if magic_raw is not None else 0)
        except (TypeError, ValueError):
            magic = 0
        profile = ensure_ea_profile_for_magic(repo, magic)
        items.append(
            map_deal_to_evidence(
                deal,
                ea_profile_id=profile.id,
                account_type=acct,  # type: ignore[arg-type]
                ingestion_batch_id=batch_id,
            )
        )
    pending = [
        i
        for i in items
        if not (
            i.external_id
            and repo.has_evidence_by_external_id(SOURCE_SYSTEM, i.external_id)
        )
    ]
    saved, skipped = _persist_batch(repo, pending)
    return {
        "source": "file",
        "batch_id": batch_id,
        "file": str(file_path),
        "rows": len(deals),
        "fetched_pending": len(pending),
        "saved": saved,
        "skipped_duplicate": skipped + (len(items) - len(pending)),
        "db": db_path,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m phase3_knowledge_engine.ingest",
        description=(
            "Phase 3 Gate 1 — read-only evidence ingestion into knowledge.db. "
            "Does not enable PHASE3_KNOWLEDGE_ENGINE_ENABLED or touch Phase 2 runtime."
        ),
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--file",
        type=Path,
        help="JSON list (or CSV) of bridge-shaped deals",
    )
    src.add_argument(
        "--bridge-url",
        help="Live MT5 bridge base URL (uses backend BridgeClient, GET /deals only)",
    )
    p.add_argument(
        "--bridge-token",
        default="",
        help="Bearer token for the bridge (or set MT5_BRIDGE_TOKEN)",
    )
    p.add_argument("--days", type=int, default=90, help="Bridge /deals lookback days")
    p.add_argument(
        "--db",
        default=DEFAULT_KNOWLEDGE_DB_PATH,
        help=f"knowledge.db path (default: {DEFAULT_KNOWLEDGE_DB_PATH})",
    )
    p.add_argument("--limit", type=int, default=500, help="Max deals to ingest")
    p.add_argument(
        "--account-type",
        choices=("demo", "live"),
        default=None,
        help="Override account_type for --file ingestion",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    if args.file:
        result = run_file_ingest(
            file_path=args.file,
            db_path=args.db,
            limit=args.limit,
            account_type=args.account_type,
        )
    else:
        import os

        token = args.bridge_token or os.environ.get("MT5_BRIDGE_TOKEN", "")
        result = run_bridge_ingest(
            bridge_url=args.bridge_url,
            bridge_token=token,
            days=args.days,
            db_path=args.db,
            limit=args.limit,
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

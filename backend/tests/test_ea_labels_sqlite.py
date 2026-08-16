"""SQLite persistence for EA label overrides."""
from __future__ import annotations

import asyncio
from pathlib import Path

from mt5_cache_sqlite import MT5CacheSQLite


def test_ea_label_roundtrip(tmp_path):
    db = MT5CacheSQLite(str(tmp_path / "atlas.db"))

    async def _run():
        assert await db.get_ea_labels(62127915) == {}
        labels = await db.set_ea_label(62127915, 100, "Dark Mimas")
        assert labels[100] == "Dark Mimas"
        labels = await db.set_ea_label(62127915, 100, "  Novo Nome  ")
        assert labels[100] == "Novo Nome"
        labels = await db.set_ea_label(62127915, 100, None)
        assert 100 not in labels
        assert (tmp_path / "atlas.db").is_file()

    asyncio.run(_run())

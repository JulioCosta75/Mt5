"""Periodic equity snapshot recorder.

Runs inside the bridge process. Every N seconds, queries the MT5 account and
stores a row in SQLite. Provides the high-resolution intra-day equity series
that closed-deal reconstruction cannot give us.
"""
from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


class SnapshotRecorder:
    def __init__(self, mt5_service, storage, interval_seconds: int = 10):
        self.mt5_service = mt5_service
        self.storage = storage
        self.interval_seconds = interval_seconds
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self._job = None

    def _tick(self):
        try:
            info = self.mt5_service.account_info()
            self.storage.insert_snapshot(self.mt5_service.login, info)
        except Exception as e:  # noqa: BLE001
            logger.warning("snapshot tick failed: %s", e)

    def start(self):
        if self._job:
            return
        self._job = self.scheduler.add_job(
            self._tick,
            "interval",
            seconds=self.interval_seconds,
            next_run_time=None,
        )
        self.scheduler.start()
        logger.info("SnapshotRecorder started (every %ss)", self.interval_seconds)

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._job = None

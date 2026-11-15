"""Isolated Telegram DEMO outbound bridge (SUS-010).

This package is intentionally not imported by Production Phase 2, the MT5
bridge, the installer, or the Phase 3 Knowledge Engine.

It sends outbound DEMO notifications only. It never places orders, never
talks to MT5, and never reads trading credentials.
"""

from telegram_demo_outbound.constants import REQUIRED_PREFIX

__all__ = ["REQUIRED_PREFIX"]

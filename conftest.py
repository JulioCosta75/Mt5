"""Repo-root pytest hooks. Same external-test gate as backend/conftest.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from pytest_external import (  # noqa: E402
    add_external_option,
    register_external_marker,
    skip_external_items,
)


def pytest_addoption(parser):
    add_external_option(parser)


def pytest_configure(config):
    register_external_marker(config)


def pytest_collection_modifyitems(config, items):
    skip_external_items(config, items)

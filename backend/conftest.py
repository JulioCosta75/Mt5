"""Backend pytest hooks. External URL tests stay off unless requested."""

from __future__ import annotations

from pytest_external import (
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

"""Skip tests that call a remote backend unless the run asks for them.

Default pytest does not use the baked-in preview URL. An external test runs
only with ``--external`` and a ``REACT_APP_BACKEND_URL`` set for that run.
"""

from __future__ import annotations

import os

import pytest

_OPTION = "--external"


def add_external_option(parser: pytest.Parser) -> None:
    try:
        parser.addoption(
            _OPTION,
            action="store_true",
            default=False,
            help=(
                "Run tests marked external. Also set REACT_APP_BACKEND_URL "
                "to the backend those tests should call."
            ),
        )
    except ValueError:
        return


def register_external_marker(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "external: calls REACT_APP_BACKEND_URL; skipped unless --external "
        "and that variable is set",
    )


def skip_external_items(config: pytest.Config, items: list[pytest.Item]) -> None:
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if config.getoption(_OPTION) and url:
        return
    skip = pytest.mark.skip(
        reason=(
            "external test skipped: pass --external and set "
            "REACT_APP_BACKEND_URL (the preview URL is not used by default)"
        )
    )
    for item in items:
        if item.get_closest_marker("external") is not None:
            item.add_marker(skip)

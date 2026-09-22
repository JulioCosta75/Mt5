"""CLI inspection: known id prints JSON; unknown id exits 1 with empty stdout."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout

from education.glossary import main


def test_cli_concept_spread_prints_definition_and_example():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["--concept", "spread"])
    assert code == 0
    payload = json.loads(stdout.getvalue())
    assert payload["id"] == "spread"
    assert payload["definition"].strip()
    assert payload["example"].strip()
    assert stderr.getvalue() == ""


def test_cli_unknown_concept_exits_without_fabricated_body():
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["--concept", "rsi"])
    assert code == 1
    assert stdout.getvalue() == ""
    assert "unknown concept id" in stderr.getvalue()


def test_cli_list_returns_all_nine_ids():
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = main(["--list"])
    assert code == 0
    payload = json.loads(stdout.getvalue())
    ids = [row["id"] for row in payload["concepts"]]
    assert len(ids) == 9
    assert "spread" in ids
    assert "metatrader5" in ids

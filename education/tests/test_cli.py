"""CLI inspection: known id prints JSON; unknown id exits 1 with empty stdout."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout

from education.catalog import get_explanation
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


def test_cli_redirected_stdout_emits_utf8_not_cp1252(monkeypatch):
    """Windows redirected stdout defaults to cp1252; CLI must reconfigure UTF-8."""
    out_buf = io.BytesIO()
    err_buf = io.BytesIO()
    stdout = io.TextIOWrapper(out_buf, encoding="cp1252", newline="\n")
    stderr = io.TextIOWrapper(err_buf, encoding="cp1252", newline="\n")
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    code = main(["--concept", "spread"])
    stdout.flush()
    raw = out_buf.getvalue()

    assert code == 0
    assert stdout.encoding.lower() == "utf-8"
    assert stderr.encoding.lower() == "utf-8"
    expected = get_explanation("spread")
    assert expected is not None
    assert "é" in expected.definition
    assert "é".encode("utf-8") in raw
    payload = json.loads(raw.decode("utf-8"))
    assert payload["definition"] == expected.definition
    assert payload["example"] == expected.example


def test_cli_unknown_id_reconfigures_stderr_to_utf8(monkeypatch):
    out_buf = io.BytesIO()
    err_buf = io.BytesIO()
    stdout = io.TextIOWrapper(out_buf, encoding="cp1252", newline="\n")
    stderr = io.TextIOWrapper(err_buf, encoding="cp1252", newline="\n")
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    code = main(["--concept", "rsi"])
    stdout.flush()
    stderr.flush()

    assert code == 1
    assert stdout.encoding.lower() == "utf-8"
    assert stderr.encoding.lower() == "utf-8"
    assert out_buf.getvalue() == b""
    assert b"unknown concept id" in err_buf.getvalue()


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

"""CLI inspection with synthetic tokens."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from ai_usage.usage import main


def test_cli_record_and_list_are_per_user(tmp_path: Path):
    db = str(tmp_path / "ai_usage.db")
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = main(
            [
                "record",
                "--user",
                "alice",
                "--mode",
                "educador",
                "--model",
                "haiku",
                "--input-tokens",
                "1000",
                "--output-tokens",
                "200",
                "--db",
                db,
            ]
        )
    assert code == 0
    recorded = json.loads(stdout.getvalue())
    assert recorded["user_id"] == "alice"
    assert recorded["estimated_cost_usd"]

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = main(["list", "--user", "bob", "--db", db])
    assert code == 0
    payload = json.loads(stdout.getvalue())
    assert payload["usage"] == []

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = main(["list", "--user", "alice", "--db", db])
    assert code == 0
    payload = json.loads(stdout.getvalue())
    assert len(payload["usage"]) == 1


def test_cli_route_defaults_to_haiku():
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        code = main(["route"])
    assert code == 0
    assert json.loads(stdout.getvalue())["model"] == "haiku"


def test_cli_unknown_mode_is_rejected_before_any_row(tmp_path: Path):
    db = str(tmp_path / "ai_usage.db")
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = main(
                [
                    "record",
                    "--user",
                    "alice",
                    "--mode",
                    "unknown",
                    "--model",
                    "haiku",
                    "--input-tokens",
                    "1",
                    "--output-tokens",
                    "0",
                    "--db",
                    db,
                ]
            )
        except SystemExit as exc:
            code = int(exc.code or 1)
    assert code == 2
    assert stdout.getvalue() == ""
    assert not Path(db).exists()

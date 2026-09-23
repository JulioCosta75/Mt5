"""CLI without a key fails clearly and does not fabricate an answer."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from education.ai.ask import main
from education.ai.clients import AnthropicLLMClient, MissingAPIKeyError


def test_cli_without_api_key_does_not_fabricate(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(
            [
                "--concept",
                "spread",
                "--question",
                "O que é o spread?",
                "--user",
                "alice",
                "--tier",
                "free",
                "--db",
                str(tmp_path / "ai_usage.db"),
            ]
        )
    assert code == 2
    assert stdout.getvalue() == ""
    err = stderr.getvalue()
    assert "ANTHROPIC_API_KEY" in err
    assert "will not fabricate" in err
    assert "spread é" not in err.casefold()


def test_anthropic_client_generate_without_key_raises_before_sdk(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = AnthropicLLMClient(model="haiku")
    try:
        client.generate("pergunta")
        raised = None
    except MissingAPIKeyError as exc:
        raised = exc
    assert raised is not None
    assert "ANTHROPIC_API_KEY" in str(raised)
    assert "sk-" not in str(raised)

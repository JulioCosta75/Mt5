"""Educador Stage 2 — real LLM adapter, budget-guarded.

> **ISOLATION WARNING**
>
> Not wired to `backend/server.py` or the frontend. No account or
> financial data in prompts. Automated tests use `FakeLLMClient` only.
>
> The Anthropic SDK is imported inside `AnthropicLLMClient.generate`,
> never at module import time. `ANTHROPIC_API_KEY` is read from the
> environment only, never hardcoded, never logged.

## CLI

```bash
python -m education.ai.ask --concept spread --question "O que é o spread?" \\
    --user alice --tier free
```

Without `ANTHROPIC_API_KEY`, the CLI exits with a clear error and does
not fabricate an answer.

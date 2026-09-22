"""Educador Stage 1 — isolated static glossary.

> **ISOLATION WARNING**
>
> This module is **not integrated** with Phase 2 production runtime.
> Do **not** import it from `backend/server.py`, the dashboard, MT5 Bridge,
> installer scripts, n8n workflows, `phase3_knowledge_engine`, or
> `notifications`.
>
> No LLM, no external API, no API key, no HTTP in this stage.
> Content is 100% generic — identical for every user and account.

## Purpose

Hand-written explanations for the Educador mode: each concept has a
stable id, a short definition, and one concrete example. Lookup never
fabricates content for an unknown id.

## Closed concept set

| id | title |
| --- | --- |
| `metatrader5` | Como funciona o MetaTrader 5 |
| `candles` | Velas (candles) e como são formadas |
| `spread` | Spread, pip, lote, margem e alavancagem |
| `orders` | Ordens, posições, stop-loss e take-profit |
| `market_sessions` | Volatilidade, liquidez e sessões de mercado |
| `trends` | Tendências e alterações de regime |
| `drawdown` | Drawdown e gestão de risco |
| `expert_advisors` | Funcionamento dos EAs |
| `backtest_demo_live` | Diferenças entre backtest, conta demo e conta real |

## Layout

```
education/
├── catalog.py                # get_explanation / list_concept_ids
├── content/glossary.json     # structured static content
├── domain/entities.py        # Explanation
├── glossary.py               # CLI
└── tests/
```

## CLI

```bash
python -m education.glossary --concept spread
python -m education.glossary --list
```

## Tests

```bash
python3 -m pytest education/tests/ -q
```

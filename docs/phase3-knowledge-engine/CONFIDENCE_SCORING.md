# Phase 3 Confidence Scoring (Advisory Only)

> Confidence **never** replaces human validation. It supports reviewers only.

Implementation: `phase3_knowledge_engine/domain/confidence.py`

## Formula

```
confidence = min(1.0,
    w_sample  × sample_score(n)
  + w_consist × supporting / (supporting + contradictory)
  + w_recency × 0.5^(days / 90)
  + w_context × filled_fields / total_fields
)
```

Default weights: sample 0.35, consistency 0.30, recency 0.15, context 0.20.

## Advisory thresholds

| Milestone | Suggested minimum confidence | Also requires |
|-----------|------------------------------|---------------|
| Provisional validation | 0.55 | Human review |
| Full validation | 0.75 | Human review |
| Knowledge promotion | 0.75+ | Human review + Rule 6 criteria |

Thresholds do **not** auto-promote. `KnowledgeEngineService.apply_human_review_transition()` computes confidence for display but gates remain human.

## Knowledge promotion criteria (Rule 6)

Independent of confidence:

- Documented relevance for future decisions
- `evidence_count >= 10`
- `sample_size >= 30`
- Context documented
- Material contradictions resolved
- Recorded human reviewer

## What confidence must not do

- Auto-promote any validation state
- Override a human rejection
- Replace audit trail requirements
- Start/stop EAs or change capital

# Phase 3 Validation State Model

## States

| State | Code | Description |
|-------|------|-------------|
| Raw Observation | `raw_observation` | Single recorded fact |
| Repeated Pattern | `repeated_pattern` | ≥N similar observations (configurable) |
| Hypothesis | `hypothesis` | Explicit human-formulated claim |
| Evidence Under Review | `evidence_under_review` | Evidence package submitted |
| Provisionally Validated | `provisionally_validated_conclusion` | Early human approval |
| Fully Validated | `fully_validated_conclusion` | Strong human approval |
| Knowledge Candidate | `knowledge_candidate` | Ready for corpus promotion |
| Knowledge | `knowledge` | Permanent validated knowledge |
| Invalidated | `invalidated_conclusion` | Refuted — preserved forever |

## Transition matrix (summary)

| From | Allowed to |
|------|------------|
| RawObservation | RepeatedPattern, RawObservation |
| RepeatedPattern | Hypothesis, RawObservation |
| Hypothesis | EvidenceUnderReview, InvalidatedConclusion |
| EvidenceUnderReview | ProvisionallyValidated, Invalidated, Hypothesis |
| ProvisionallyValidated | FullyValidated, EvidenceUnderReview, Invalidated |
| FullyValidated | **KnowledgeCandidate only**, EvidenceUnderReview, Invalidated |
| KnowledgeCandidate | **Knowledge only**, EvidenceUnderReview, Invalidated |
| Knowledge | EvidenceUnderReview (reopened by new evidence) |
| Invalidated | *(terminal)* |

## Human review requirements

Required for transitions into:

- `provisionally_validated_conclusion`
- `fully_validated_conclusion`
- `knowledge_candidate`
- `knowledge`
- `invalidated_conclusion`

Enforced in `domain/validation_states.py` → `can_transition()` and `application/services.py`.

## Mandatory path to Knowledge

```
FullyValidatedConclusion → KnowledgeCandidate → Knowledge
```

Skipping `KnowledgeCandidate` is **blocked**.

## Audit trail (Rule 9)

Every transition writes:

| Field | Description |
|-------|-------------|
| `from_state` | Previous validation state |
| `to_state` | New validation state |
| `transitioned_at` | UTC timestamp |
| `actor` | Responsible human or system actor |
| `justification` | Free-text reason |
| `evidence_ids` | Evidence used in the decision |

## Evidence impact on existing knowledge (Rule 7)

| Impact | Effect |
|--------|--------|
| `confirm` | Logged; knowledge unchanged |
| `weaken` | Knowledge reopened to `evidence_under_review` |
| `review` | Knowledge reopened to `evidence_under_review` |
| `invalidate` | Knowledge reopened to `evidence_under_review` |

Silent overwrite is forbidden.

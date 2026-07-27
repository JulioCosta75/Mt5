# Sr. Atlas Technical Governance

## 1. Authority and purpose

- These rules apply to every human or AI agent working in this repository.
- The founder defines architecture, priorities, authorization, and production acceptance.
- Cursor implements authorized work.
- Claude Code performs independent architectural and code analysis.
- Installation and functional acceptance occur only after review.
- No agent may treat an implementation as approved merely because it builds or passes tests.

**Architectural principles**

- Knowledge before money.
- We are architects, not mechanics.
- Workflow: We define the architecture → Cursor builds → Claude Code analyzes → we install and test.
- Production Phase 2 must remain protected.
- Phase 3 must remain isolated and disabled unless separately authorized.
- Evidence must be distinguished from assumptions.
- Do not go in circles.

## 2. Protected Production Phase 2 baseline

Record:

- Repository: JulioCosta75/Mt5
- Protected safety tag:
  `sr-atlas-v0.3.0-phase2-baseline-20260727`
- Protected baseline commit:
  `33b3424e31b6bc12534e70b79911d69d95bb4033`
- Protected baseline tree:
  `fda716dbb76e2725643697d91d88af0afb58790d`
- Restored main merge commit:
  `cd43d7935ef59991315b9dae938401e38ffd250e`

Phase 2 includes the production dashboard, backend/FastAPI, supervision functionality, MT5 bridge, installer, frontend, and n8n health-monitor package.

The tag is an immutable recovery reference. It must never be moved, recreated, overwritten, or deleted.

## 3. Main and branch protection

- Never commit directly to main.
- Never force-push or delete main.
- Every change must use a dedicated branch and Pull Request.
- A branch must have one clearly defined purpose.
- Do not mix recovery, governance, Phase 2 fixes, Phase 3 development, dependencies, or formatting in one branch.
- Do not merge without explicit founder authorization.
- Preserve recovery branches until the founder authorizes deletion.
- Prohibit destructive Git operations unless the founder explicitly authorizes an exact target and purpose.

## 4. Mandatory workflow

For every change:

1. Verify repository, branch, HEAD, and clean/dirty state.
2. Read these governance rules.
3. Inspect the relevant architecture and existing tests.
4. State verified facts, inferences, and unverified assumptions separately.
5. Produce a bounded implementation plan.
6. Obtain authorization when a protected decision is involved.
7. Implement only the authorized scope.
8. Run relevant validation without weakening existing checks.
9. Report files changed, tests run, failures, risks, and unverified items.
10. Submit through a Pull Request.
11. Require independent review before merge.
12. Install or deploy only after explicit authorization.

## 5. Protected decisions requiring founder authorization

Require explicit founder authorization before:

- changing architecture or product boundaries;
- modifying Phase 2 behavior;
- changing API contracts, database schemas, validation states, or confidence rules;
- adding, removing, or upgrading dependencies;
- changing security, authentication, secrets handling, ports, services, installer behavior, or deployment;
- enabling feature flags;
- integrating Phase 3 with Phase 2;
- altering tests solely to make a failure disappear;
- deleting compatibility paths, branches, tags, data, reports, or recovery assets;
- merging or deploying.

If authorization is absent or ambiguous, stop and ask.

## 6. Phase 3 isolation

- Phase 3 Knowledge Engine work must live on a dedicated Phase 3 branch.
- Its default feature flag must remain OFF:
  `PHASE3_KNOWLEDGE_ENGINE_ENABLED=false`
- Phase 3 must not be imported, registered, started, scheduled, routed, migrated, or exposed by Production Phase 2 while disabled.
- Phase 3 must not change Phase 2 behavior, dependencies, API responses, database state, startup, installer, services, or frontend unless separately authorized.
- Phase 3 tests must prove both isolation and disabled-by-default behavior.
- No Phase 3 merge into main without architectural review, test evidence, independent analysis, and explicit founder authorization.

## 7. Testing and validation

- Never claim a test passed unless it was actually executed and its result observed.
- Clearly label tests that were not run.
- Do not use historical test reports as proof of the current checkout.
- Do not change production code merely to satisfy an obsolete or external preview test.
- Do not weaken, skip, delete, or rewrite tests without explaining why and obtaining authorization when protection is reduced.
- Prefer the smallest relevant validation first.
- Windows installer and live MT5 validation must be reported separately from mock or non-Windows tests.
- Mock success is not proof of live MT5 success.
- A successful build is not production acceptance.
- Record commands, exit codes, failures, and environmental limitations.

## 8. Secrets and data safety

- Never commit passwords, tokens, private keys, MT5 credentials, bridge tokens, API keys, Mongo credentials, or populated `.env` files.
- Never print secrets in reports, logs, commits, or Pull Requests.
- Use environment variables and sanitized examples.
- Do not copy credentials between systems without explicit authorization.
- Treat local MT5 configuration and operator data as sensitive.
- Stop if a requested action risks exposing or overwriting sensitive data.

## 9. Change discipline

- Make the smallest coherent change.
- Do not perform unrelated cleanup, formatting, renaming, modernization, or dependency updates.
- Preserve user changes and dirty worktrees.
- Do not invent missing requirements.
- Do not silently repair unrelated problems.
- Do not repeatedly retry the same failed approach without new evidence.
- If blocked, report the blocker, evidence, and safest next decision.
- Do not reconstruct missing project history from memory.

## 10. Evidence and reporting

Every completion report must distinguish:

- **VERIFIED:** directly observed in files, Git state, command output, or executed tests.
- **INFERENCE:** reasoned conclusion supported by evidence.
- **NOT VERIFIED:** not inspected or not executable in the current environment.

The final report must include:

- branch and commit;
- files changed;
- tests and validations performed;
- observed results;
- unresolved risks;
- confirmation that no unauthorized files or protected references changed.

## 11. Definition of done

Work is not complete until:

- scope matches the authorization;
- relevant checks pass or failures are disclosed;
- no secrets are exposed;
- Phase 2 protections remain intact;
- Phase 3 remains isolated and disabled where applicable;
- independent review is possible from the recorded evidence;
- founder authorization is obtained for merge or deployment.

FORJA-SE CONHECIMENTO.
KNOWLEDGE IS FORGED.

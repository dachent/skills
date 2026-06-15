# Artifact Contracts

Use concise Markdown. Prefer facts, decisions, evidence, and unresolved questions over narrative.

## state.md

```markdown
# Deep Planning State

Project mode: software-git | software-no-git | business-artifact | mixed-business-coding
Current phase: ...
Status: READY_FOR_PROCEED | BLOCKED_NEEDS_USER_DECISION | BLOCKED_BY_MISSING_EVIDENCE | FAILED_VALIDATION

## Updated Artifacts
- ...

## Decisions
- ...

## Open Assumptions
- ...

## Next Action
...
```

## Deep Planning Delta

Companion skills invoked by `deep-planning-codex` must return or write a concise delta that can be merged into `state.md`:

```markdown
## Deep Planning Delta
Phase: ...
Status: READY_FOR_PROCEED | BLOCKED_NEEDS_USER_DECISION | BLOCKED_BY_MISSING_EVIDENCE | FAILED_VALIDATION
Updated artifacts:
- ...
Blockers:
- ...
Open assumptions:
- ...
Next action:
...
```

## assumption-ledger.md

```markdown
# Assumption Ledger

| ID | Claim | Evidence | Confidence | Owner | Verification method | Status |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | ... | ... | low/medium/high | user/Codex/stakeholder | ... | unverified/probe-passed/probe-failed/accepted-risk |
```

## dead-ends-registry.md

```markdown
# Dead Ends Registry

| ID | Rejected approach | Evidence | Failure mechanism | Reconsider if |
| --- | --- | --- | --- | --- |
| D1 | ... | ... | ... | ... |
```

## evidence-catalog.md

```markdown
# Evidence Catalog

| Item | What it is | Attempt/context | Outcome | Relevance | Failure mechanism |
| --- | --- | --- | --- | --- | --- |
| ... | ... | succeeded/failed/partial/unreached | high/medium/low | ... |
```

## verification-plan.md

```markdown
# Verification Plan

| Criterion | Proof method | Command/check | Expected result | Evidence artifact | Owner/Reviewer | Failure signal | Recovery trigger |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... | ... | ... |
```

## adversarial-review.md

```markdown
# Adversarial Plan Review

## Verdict
PASS | FAIL | PARTIAL

## Findings
- **Severity**: BLOCKING | IMPORTANT | NOTE
- **Issue**: ...
- **Evidence**: ...
- **Required fix**: ...
```

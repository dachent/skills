---
name: adversarial-plan-review-codex
description: "Use when a plan needs hostile review before execution, especially high-risk coding, business deliverables, migrations, no-git changes, weak validation, stale assumptions, rollback gaps, or plans that must be safe for another agent to execute."
---

# Codex Adversarial Plan Review

## Overview

Red-team a plan before execution. The goal is to find blocking flaws while changes are still cheap: stale paths, unsupported assumptions, missing validation, rollback gaps, stakeholder gaps, and contradictions with prior evidence.

## Workflow

1. Read the plan, success criteria, failure criteria, out-of-scope boundaries, repo map, evidence catalog, assumption ledger, dead ends, probes, and verification plan.
2. Select review lenses: software, business, or mixed.
3. Check whether every plan step is evidence-backed, ordered safely, and verifiable.
4. Classify findings as `BLOCKING`, `IMPORTANT`, or `NOTE`.
5. If blockers exist, revise the source plan or tell the user exactly what decision/evidence is missing.
6. Write `.deep-planning/adversarial-review.md` unless the user specifies another planning workfolder.

## When Invoked By deep-planning-codex

- Treat `.deep-planning/implementation-plan.md` and `.deep-planning/verification-plan.md` as required inputs before a final execution gate.
- Return `PASS` only when there are no `BLOCKING` findings. Use `FAIL` when inspected evidence proves a blocking flaw. Use `PARTIAL` when required evidence cannot be inspected well enough to determine whether the plan is safe.
- A `FAIL` or `PARTIAL` verdict must block `READY_FOR_PROCEED`; the Deep Planning Delta status should be `FAILED_VALIDATION`, `BLOCKED_BY_MISSING_EVIDENCE`, or `BLOCKED_NEEDS_USER_DECISION` based on the fix required.
- End with a Deep Planning Delta for the orchestrator to merge into `.deep-planning/state.md`, including the exact artifact or decision needed for re-review.

## References

Read as needed:

- `references/software-review.md` for code, tests, migrations, dependencies, and rollback.
- `references/business-review.md` for stakeholders, source data, approval, privacy, and deliverable risks.
- `references/mixed-review.md` for combined business and coding work.

## PASS Criteria

Return `PASS` only when:

- critical paths and source materials exist;
- assumptions are either verified or explicitly accepted risks;
- validation proves the stated success criteria;
- rollback or recovery is defined;
- sequencing does not depend on impossible or circular steps;
- no blocked stakeholder, data, security, or permission issue remains.

## Output Format

Use this structure:

```markdown
# Adversarial Plan Review

## Verdict
PASS | FAIL | PARTIAL

## Findings
- **Severity**: BLOCKING | IMPORTANT | NOTE
- **Issue**: ...
- **Evidence**: ...
- **Required fix**: ...

## Re-review
[What changed, or why no re-review was needed]
```

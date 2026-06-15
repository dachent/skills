---
name: deep-planning-codex
description: "Use when a project needs deep, gated planning before execution, especially high-stakes coding, failed prior attempts, business deliverables, mixed business-coding work, no-git workflows, or plans that need evidence, probes, verification, and adversarial review."
---

# Codex Deep Planning Orchestrator

## Overview

Run a Codex-native deep planning protocol that adapts to software with Git, software without Git, business artifact work, and mixed business-coding projects. Produce durable planning artifacts, proof criteria, and a reviewed execution strategy before implementation.

## Core Contract

- Treat the user's invocation text as the planning objective.
- Create or reuse the target project's `.deep-planning/` workfolder.
- During planning, do not edit implementation files. Allowed planning writes are `.deep-planning/`, `.ultraplan/plan.md`, approved design/plan docs, `CONTEXT.md`, and accepted ADRs.
- Every phase updates `.deep-planning/state.md`.
- Every phase ends with exactly one status: `READY_FOR_PROCEED`, `BLOCKED_NEEDS_USER_DECISION`, `BLOCKED_BY_MISSING_EVIDENCE`, or `FAILED_VALIDATION`.
- Stop at explicit proceed gates. Continue only after the user says `PROCEED` or gives equivalent explicit approval.
- Use companion skills when available: `$repo-map-codex`, `$verification-plan-codex`, `$adversarial-plan-review-codex`, `$grill-with-docs-codex`, `$grill-me-codex`, `$handoff-codex`, `$ultraplan-codex`, `superpowers:brainstorming`, `superpowers:systematic-debugging`, `superpowers:writing-plans`, and `superpowers:verification-before-completion`. If unavailable, perform the same behavior locally.
- Use Codex subagents only when explicitly allowed by the user or current session instructions. Otherwise perform bounded local exploration and review.

## Companion Skill Contract

When a companion skill is invoked inside this workflow, require a Deep Planning Delta and merge it into `.deep-planning/state.md` before any proceed gate:

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

If the companion skill writes a native artifact outside `.deep-planning/`, such as `.ultraplan/plan.md`, keep that native artifact and also update or link the corresponding `.deep-planning/` artifact so the validator can reason over the full planning packet.

## References

Read references only when needed:

- `references/project-modes.md` when selecting or revising project mode.
- `references/artifact-contracts.md` before writing or validating `.deep-planning/` artifacts.
- `references/phase-contracts.md` before running the full workflow or resuming a workflow.
- `references/proceed-gates.md` before stopping for approval.
- `references/subagent-strategy.md` before delegating planning or execution work.

## Phase Flow

1. **Harness preflight**: record workspace, writable roots, Git state if present, available skills, subagent authorization, allowed artifact paths, and selected project mode.
2. **Intake and criteria**: sharpen success criteria, failure criteria, out-of-scope boundaries, owner decisions, risk tolerance, and documentation permissions.
3. **Project map and evidence catalog**: invoke `$repo-map-codex` if available or produce equivalent `repo-map.md` and `evidence-catalog.md`.
4. **Failure autopsy**: if prior failures exist, use systematic debugging or diagnosis to build `failure-autopsy.md` and `dead-ends-registry.md`.
5. **Assumption attack**: challenge criteria, evidence, dead ends, and unresolved claims; update `assumption-ledger.md`.
6. **Targeted probes**: run low-cost probes mapped to assumptions. Do not implement features.
7. **Design synthesis**: use brainstorming only if real design ambiguity remains; otherwise write the selected design directly.
8. **Grounded implementation plan**: use `$ultraplan-codex` for software-heavy work; for artifact-heavy work write `.deep-planning/implementation-plan.md`. When `$ultraplan-codex` writes `.ultraplan/plan.md`, also write or update `.deep-planning/implementation-plan.md` with the execution sequence, verification command, and a pointer to the native plan.
9. **Verification plan**: invoke `$verification-plan-codex` if available or produce equivalent proof criteria.
10. **Adversarial review**: invoke `$adversarial-plan-review-codex` if available or locally red-team the plan and fix blockers.
11. **Final execution plan**: use `superpowers:writing-plans` for code-heavy work; otherwise write a decision-complete artifact execution plan.
12. **Execution strategy**: choose subagent-driven, parallel, or inline execution only after explicit approval.
13. **Final verification and archive**: use verification-before-completion behavior, then write final validation and handoff records.

## Project Modes

Classify the project in preflight:

| Mode | Use when | Delivery primitive |
| --- | --- | --- |
| `software-git` | Git repository and commits/PRs are allowed | branch, commit, PR, CI |
| `software-no-git` | Code exists but no commit workflow is allowed | file snapshots, milestone state, validation log |
| `business-artifact` | Work is mostly docs, reports, spreadsheets, decisions, or analysis | approval packet, evidence log, deliverable folder |
| `mixed-business-coding` | Business deliverables include code, scripts, data, or automation | artifact snapshots plus code and business validation |

Default to `mixed-business-coding` when uncertain.

## Required Artifacts

Maintain these in the target project's `.deep-planning/` folder as applicable:

- `state.md`
- `harness-preflight.md`
- `project-mode.md`
- `success-criteria.md`
- `failure-criteria.md`
- `out-of-scope.md`
- `stakeholder-map.md`
- `repo-map.md`
- `evidence-catalog.md`
- `assumption-ledger.md`
- `decision-log.md`
- `failure-autopsy.md`
- `dead-ends-registry.md`
- `probe-results.md`
- `design.md`
- `implementation-plan.md`
- `verification-plan.md`
- `adversarial-review.md`
- `execution-strategy.md`
- `final-validation.md`
- `handoffs/`

Use `.ultraplan/plan.md` when `$ultraplan-codex` is part of the selected software-heavy workflow, but do not treat it as a replacement for `.deep-planning/implementation-plan.md`.

## Handoff Policy

Do not run full handoff after every small phase by default. Always update `.deep-planning/state.md`. Run `$handoff-codex` at major context gates: after Phase 0, after failure autopsy, after final plan approval, before execution handoff, and at final archive. In this workflow, store handoffs under `.deep-planning/handoffs/<gate>.md` or record a state pointer to the handoff path.

## Validation

Before presenting a final execution plan, run `scripts/validate_deep_planning_artifacts.py` against the target project when possible. Treat missing required artifacts, incomplete state fields, unresolved proceed gates, failed adversarial verdicts, blocking review findings, or unreviewed verification criteria as blockers.

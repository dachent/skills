---
name: verification-plan
description: "Use when a plan needs proof criteria before execution, especially coding changes, business deliverables, mixed business-coding projects, acceptance criteria, rollback triggers, manual checks, or final validation design."
---

# Verification Plan

## Overview

Define how the work will be proven correct before execution starts. A verification plan maps each success criterion to commands, checks, expected results, evidence, and recovery triggers.

## Workflow

1. Read success criteria, failure criteria, out-of-scope boundaries, repo map, evidence catalog, assumption ledger, and the current implementation plan.
2. Classify validation as software, business, or mixed.
3. For every success criterion, define at least one proof method.
4. For every failure criterion, define the signal that would show it happened.
5. Define rollback or recovery triggers before execution.
6. Write the result to `.deep-planning/verification-plan.md` unless the user specifies another planning workfolder.

## References

Read as needed:

- `references/software-validation.md` for tests, builds, static checks, smoke checks, and command output.
- `references/business-validation.md` for stakeholder acceptance, source reconciliation, document checks, and calculation checks.
- `references/rollback-and-recovery.md` for Git and no-Git recovery strategies.

## Minimum Output

Include:

- criterion identifier;
- proof method;
- command or manual check;
- expected result;
- evidence artifact;
- owner if human review is required;
- failure signal;
- rollback or recovery trigger.

## Red Flags

Do not accept vague checks such as "test it manually", "review output", "run the app", or "stakeholder approves" without defining the specific evidence that makes the check pass.

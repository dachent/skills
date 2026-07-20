---
name: ultraplan-codex
description: "Deprecated for GPT-5.6 Sol. Use native Codex Plan Mode for grounded, decision-complete implementation plans."
---

# Codex UltraPlan

> **Deprecated for GPT-5.6 Sol.** Use native Codex Plan Mode for grounded, decision-complete implementation plans. Do not use this package for new work.

## Overview

Run a read-only, multi-phase implementation planning session before coding. Produce a concise, file-path-grounded `.ultraplan/plan.md` that can be executed without guessing.

## Activation

Treat the user's invocation text as the planning task.

Enter deep planning mode. This is not quick planning: investigate the codebase, interview the user only for non-discoverable decisions, synthesize one recommended approach, and validate the plan before presenting it.

**Read-only rule:** Do not create, modify, or delete files except `.ultraplan/plan.md` while planning. When invoked by `deep-planning-codex`, `.deep-planning/implementation-plan.md` and `.deep-planning/state.md` are also allowed planning artifacts. Do not install dependencies, run migrations, commit, push, format, or edit implementation files. Read commands, searches, tests, and build checks are allowed when they improve the plan and do not intentionally modify tracked source.

## Quick Reference

| Need | Use |
| --- | --- |
| Find files | `rg --files` |
| Search code | `rg` |
| Read files | normal file reads or shell read commands |
| Parallel local reads | `multi_tool_use.parallel` when available |
| Ask user | direct concise questions; use structured question tooling only when available |
| Delegate exploration | Codex subagents only when the user explicitly asked for subagents or parallel agent work |
| Save state | `.ultraplan/plan.md` |

## When Invoked By deep-planning-codex

- Keep `.ultraplan/plan.md` as UltraPlan's native planning state.
- Also create or update `.deep-planning/implementation-plan.md` with the selected execution sequence, key file references, verification command, and a pointer to `.ultraplan/plan.md`.
- Treat `deep-planning-codex` as the owner of proceed gates. Do not ask "Ready to execute this plan, or do you want changes?" Instead, end with "Plan ready for verification phase" when the plan is complete.
- End with a Deep Planning Delta for the orchestrator to merge into `.deep-planning/state.md`. Use `READY_FOR_PROCEED` only after referenced paths, functions, and verification commands have been checked.

## Setup

1. Check whether `.ultraplan/plan.md` exists.
2. If it exists, read it and ask: "I found an existing plan at `.ultraplan/plan.md`. Continue refining it, or start fresh?"
3. If starting fresh, create `.ultraplan/plan.md` with skeleton headings and rough notes only.
4. Gather read-only git context:

```bash
git status --short
git log --oneline -5
git branch --show-current
```

If the current directory is not a Git repository, record `Git context: not a git repository` in the plan and continue. Do not treat missing git metadata as a blocker for planning small fixtures, archives, or copied code directories.

Write discoveries to `.ultraplan/plan.md` incrementally. Do not keep planning state only in conversation memory.

## Planning Loop

Repeat until the plan is complete:

1. Explore the repo with read-only searches and file reads. Prefer reuse of existing utilities, patterns, tests, and APIs before proposing new code.
2. Update `.ultraplan/plan.md` immediately with verified findings, paths, and open decisions.
3. Ask the user only for requirements, preferences, tradeoffs, or scope choices that cannot be derived from the code.

## Phase 1: Requirements Interview

Goal: build a shared understanding of what needs to happen and why.

Start by scanning 3-5 likely key files. Then write the initial skeleton plan and ask the first round of questions if user intent remains ambiguous.

Rules:
- Never ask what can be found by reading the repo.
- Batch related questions.
- Focus on user-owned decisions: requirements, priorities, tradeoffs, edge cases, and scope.
- Scale depth to task complexity.

## Phase 2: Deep Codebase Exploration

Goal: understand every file and pattern that affects the plan.

Use local exploration for all tasks. When the user explicitly asked for subagents or parallel agent work, use bounded Codex explorer subagents for independent read-heavy questions:
- Breadth-first discovery: data layer, business logic, presentation/API layer.
- Feature trace: UI to API to service to storage, plus related tests.
- Impact analysis: direct changes and indirect callers/importers.

For each exploration pass, capture:
- Existing functions or utilities to reuse, with `file:line`.
- Architecture patterns and conventions.
- Dependencies and coupling.
- Test infrastructure and relevant commands.
- Similar features to use as references.

## Phase 3: Architecture Design

Goal: design one implementation approach grounded in verified repo facts.

For complex tasks with genuine architectural ambiguity, compare lenses internally: simplicity, performance, maintainability, risk, and incremental migration. Present only the recommended approach unless the user explicitly asks for alternatives.

If parallel design review is explicitly authorized, use Codex default subagents with specific design lenses and require each to return 3-5 critical implementation files. Otherwise, perform the same design comparison locally.

## Phase 4: Plan Synthesis

Write the final `.ultraplan/plan.md` in this structure:

```markdown
# Implementation Plan: [Title]

## Context
[One line: what is changing and why]

## Changes

### [Component or Module]
- **File**: `path/to/file.ext:line`
- **Change**: [specific change]
- **Reuses**: `existingFunction()` from `path/to/utility.ext:line`

## Implementation Sequence
1. [First dependency-safe step]
2. [Second step]
3. [Final integration step]

## Edge Cases & Risks
- [Risk]: [mitigation]

## Verification
[single command or short command sequence]
```

Rules:
- Keep context to one line.
- Do not restate the user's request.
- Do not include multiple approaches.
- Keep the plan under 40 lines when possible.
- Include exact paths and line references for code reuse.
- End with the verification command.

Read `references/planning-patterns.md` only when the task needs a more detailed plan shape or multi-agent exploration pattern.

## Phase 5: Validation and Approval

Before presenting the plan:

1. Read every critical file referenced in the plan.
2. Verify referenced paths, functions, and signatures exist.
3. Confirm the implementation sequence has no circular dependency.
4. Confirm the verification command actually exercises the proposed changes.
5. If multiple design perspectives were used, synthesize them and pick one recommendation.

Then present the plan and ask directly: "Ready to execute this plan, or do you want changes?" If the user explicitly requested a report-only planning run, no-implementation output, a forward-test report, or orchestration by `deep-planning-codex`, do not ask for execution approval; report the plan location, validation status, and any unclear instruction instead.

Do not ask for approval through structured question tooling; presenting the plan is the approval request.

## Phase 6: Adversarial Verification

Use for complex or high-risk plans, including 3+ file edits, backend/API changes, infrastructure changes, data migrations, or security-sensitive behavior.

If parallel review is explicitly authorized, ask a Codex default subagent to read `.ultraplan/plan.md` and every critical referenced file, then report:
- `PASS` if the plan is sound.
- `FAIL` with specific issues if the plan is unsafe or wrong.
- `PARTIAL` if some items cannot be verified.

If subagents are not authorized or unavailable, perform this review locally. Fix the plan and re-review until no blocking issue remains.

## Execution Handoff

When the user later approves execution:

1. Read `.ultraplan/plan.md` one final time.
2. Follow the implementation sequence exactly.
3. Run the verification command from the plan.
4. Report results faithfully, including failures and unrun checks.

The plan file remains as the record of the agreed approach.

## Complexity Scaling

| Task size | Exploration | Design review | Interview depth | Expected time |
| --- | --- | --- | --- | --- |
| Simple: 1-2 files | Local, optional one focused pass | Local | 0-2 questions | 5-10 min |
| Medium: 3-5 files | Local plus 1-2 explorer agents if authorized | Local or one reviewer | 3-5 questions | 15-20 min |
| Complex: many files | 2-3 focused explorer agents if authorized | 1-2 design lenses | Multiple rounds | 25-35 min |
| Major refactor | 3 focused explorer agents if authorized | 2-3 design/review lenses | Extensive | 35-45 min |

Skip delegation for trivial typo fixes, single-line changes, and simple renames.

## Common Mistakes

Read `references/anti-patterns.md` when the plan starts to drift into one of these:
- False completion claims.
- Plan bloat.
- Phantom file references.
- Premature convergence.
- Asking findable questions.
- Alternative paralysis.
- Scope creep.

## Portability Notes

For details on how this Codex port maps Claude Code-specific companion behavior, read `references/codex-port-notes.md`. Do not treat Claude-specific global autonomy, hidden environment variables, or slash-command behavior as Codex-native features.

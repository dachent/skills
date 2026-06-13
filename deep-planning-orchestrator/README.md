# Deep Planning Orchestrator Codex Skill

`deep-planning-orchestrator` is the master Codex skill for gated, evidence-backed planning before execution. It adapts a Claude-native deep planning prompt into a Codex workflow that can handle software with Git, software without Git, business artifacts, and mixed business-coding projects.

Use it when a task needs more than a quick implementation plan: unfamiliar systems, failed prior attempts, high-risk changes, stakeholder-sensitive deliverables, or work that should stop at explicit proceed gates.

## What This Skill Does

- Creates or resumes a `.deep-planning/` workfolder.
- Classifies the project as `software-git`, `software-no-git`, `business-artifact`, or `mixed-business-coding`.
- Records harness preflight, project mode, criteria, evidence, assumptions, probes, design, implementation plan, verification plan, adversarial review, and final handoff artifacts.
- Stops at explicit `PROCEED` gates before implementation.
- Uses optional companion skills such as `repo-map`, `verification-plan`, `adversarial-plan-review`, `ultraplan`, `grill-me`, `grill-with-docs`, `handoff`, and Superpowers skills when available.
- Uses Codex subagents only when the user or session explicitly allows them, with a bounded local fallback otherwise.

## Sample Prompts

Use the skill directly when you want Codex to plan deeply before touching implementation files:

```text
Use $deep-planning-orchestrator to plan an OAuth login migration in this repo. Use the Git workflow, create evidence-backed planning artifacts, and stop before implementation until I say PROCEED.
```

For a business project with coding but no commit workflow:

```text
Use $deep-planning-orchestrator to plan a weekly clinic KPI packet that includes data extraction scripts and an executive-ready memo. Treat this as mixed business-coding work, do not use git commits, and define stakeholder validation before execution.
```

For a high-risk backend/API change:

```text
Use $deep-planning-orchestrator to plan a multi-service API contract change. Include repo mapping, assumption attacks, targeted probes, verification criteria, rollback triggers, and adversarial plan review before implementation.
```

For explicit subagent forward planning:

```text
Use $deep-planning-orchestrator to plan this migration. You may use subagents for repo-map, verification-plan, and adversarial-plan-review, but keep planning artifacts in .deep-planning/ and stop at each PROCEED gate.
```

To resume an existing planning run:

```text
Resume the existing .deep-planning workflow for this project, re-read the current state and evidence catalog, update stale assumptions, and continue only to the next PROCEED gate.
```

## Source Provenance

This folder is a Codex-native derivative of:

- Source gist: `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96`
- Source file: `deep_planning.txt`
- Source revision: `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83`
- Source revision captured: `2026-06-13`
- Source type: user-authored Claude-native deep planning prompt template
- Port depth: new Codex-native orchestration skill derived from the source workflow

## Claude-Native Source Assumptions

The source gist assumes a Claude Code style harness:

| Claude-native feature | Source role |
| --- | --- |
| Slash commands such as `/mattpocock:grill-with-docs`, `/ultraplan`, and `/superpowers:writing-plans` | Orchestrate each phase through named Claude command workflows. |
| Claude model routing such as Sonnet vs Opus | Choose model strength per phase. |
| `/mattpocock:handoff` after phase gates | Preserve continuity across long Claude sessions. |
| Claude-oriented subagent and command conventions | Delegate work through Claude workflow affordances. |
| One large master prompt | Carries most orchestration state in prompt text and phase instructions. |

## Codex Conversion

The Codex port keeps the intent but changes the harness shape:

| Source behavior | Codex adaptation |
| --- | --- |
| One master prompt | A master skill plus reusable companion skills. |
| Slash-command choreography | Skill invocations and explicit fallback behavior. |
| Claude handoff loops | Durable `.deep-planning/` artifacts and state updates. |
| Model routing | Phase contracts, risk gates, and optional Codex subagent strategy. |
| Claude execution assumptions | Sandbox-aware write scopes, `PROCEED` gates, and validator script checks. |
| Code-only planning bias | Project modes for software, business, and mixed work. |

This differs from the Claude-native approach because Codex planning quality depends heavily on explicit artifacts, verification contracts, tool/sandbox constraints, and optional rather than assumed subagent use.

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and default prompt.
- [`references/`](./references): phase contracts, project modes, artifact contracts, proceed gates, and subagent strategy.
- [`scripts/validate_deep_planning_artifacts.py`](./scripts/validate_deep_planning_artifacts.py): deterministic artifact validator.

## Validation Evidence

Validation before publication covered:

- metadata validation for all four planning workflow skills;
- static scan for Claude-only active instruction tokens and placeholders;
- Python syntax compilation for the validator script;
- functional validator execution on a mixed business-coding fixture;
- live subagent forward tests showing that the orchestrator selected `mixed-business-coding`, wrote preflight/state/project-map artifacts, stopped at `READY_FOR_PROCEED`, and did not execute implementation.

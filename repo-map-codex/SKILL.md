---
name: repo-map-codex
description: "Use when planning needs a durable project map before execution, especially unfamiliar codebases, no-git folders, business artifact projects, mixed business-coding work, dependency discovery, test command discovery, or evidence cataloging."
---

# Codex Repo Map

## Overview

Create a durable map of the project so later planning is grounded in evidence rather than memory. The map adapts to software with Git, software without Git, business artifact work, and mixed business-coding projects.

## Workflow

1. Determine the project mode: `software-git`, `software-no-git`, `business-artifact`, or `mixed-business-coding`.
2. Explore read-only first. Prefer `rg --files`, `rg`, normal file reads, and parallel reads with `multi_tool_use.parallel` when available.
3. Build a concise `repo-map.md` or equivalent project map.
4. Build an `evidence-catalog.md` that lists source materials, attempt/outcome status, and relevance.
5. Record unknowns separately from facts. Do not ask the user for facts that can be discovered.

## When Invoked By deep-planning-codex

- Use the orchestrator-selected project mode unless discovered evidence contradicts it. If the mode changes, record the reason in `.deep-planning/project-mode.md`.
- Write `.deep-planning/repo-map.md` and `.deep-planning/evidence-catalog.md` using the deep-planning artifact contract. The evidence catalog must include `Failure mechanism` for failed, partial, stale, or unreached evidence.
- End with a Deep Planning Delta for the orchestrator to merge into `.deep-planning/state.md`. Use `READY_FOR_PROCEED` only when the map and evidence catalog are complete enough for the next planning phase.
- If required evidence is missing, set status to `BLOCKED_BY_MISSING_EVIDENCE` and make `Next action` name the exact source, access, or probe needed.

## Mode References

Read the relevant reference before writing the map:

- `references/software-git.md`
- `references/software-no-git.md`
- `references/business-artifact.md`
- `references/mixed-business-coding.md`

## Minimum Output

The map must include:

- project mode and why it was selected;
- key source materials;
- entrypoints or primary deliverables;
- relevant commands, if any;
- source-of-truth data/docs;
- dependencies and external systems;
- generated or derived artifacts;
- validation surfaces;
- risk areas;
- unknowns that require user or stakeholder input.

## Write Scope

When used inside deep planning, write only to the target project's `.deep-planning/repo-map.md` and `.deep-planning/evidence-catalog.md` unless the user specifies another planning workfolder.

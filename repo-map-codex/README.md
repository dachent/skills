# Codex Repo Map Skill

> **Deprecated for GPT-5.6 Sol — do not install or invoke.** Native Codex Plan Mode performs read-first repository grounding and evidence collection. The remainder of this document is retained as historical implementation reference.

`repo-map-codex` creates a durable project map and evidence catalog before planning or execution. It is a companion skill for `deep-planning-codex`, but it can also be used directly when Codex needs grounded context for an unfamiliar project.

## What This Skill Does

- Selects the project mode: `software-git`, `software-no-git`, `business-artifact`, or `mixed-business-coding`.
- Explores read-only first with `rg --files`, `rg`, normal file reads, and parallel reads when available.
- Writes `.deep-planning/repo-map.md` and `.deep-planning/evidence-catalog.md`.
- Separates discovered facts from unknowns that require user or stakeholder input.
- Captures validation surfaces, dependencies, generated artifacts, and risk areas.

## Source Provenance

This folder is a Codex-native derivative of:

- Source gist: `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96`
- Source file: `deep_planning.txt`
- Source revision: `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83`
- Source phases adapted: Phase 1 cataloging and Phase 2a evidence review
- Source type: user-authored Claude-native deep planning prompt template
- Port depth: new Codex-native companion skill

## Codex Conversion

The source gist describes a Claude phase that catalogs relevant files, logs, code, inputs, outputs, and dependencies. The Codex version turns that phase into an invokable skill with explicit mode references and a narrow write scope.

The conversion is Codex-native because it does not depend on Claude slash commands, Claude model routing, or implicit handoff behavior. It uses Codex file-search conventions, optional parallel reads, and durable `.deep-planning/` artifacts instead.

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and default prompt.
- [`references/`](./references): mode-specific mapping guidance.

## Validation Evidence

Validation before publication covered metadata checks, static forbidden-token scans, and live subagent forward testing on a mixed business-coding fixture. The live run selected the correct mode and wrote only the expected map and evidence artifacts.

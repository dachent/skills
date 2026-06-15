# Codex Adversarial Plan Review Skill

`adversarial-plan-review-codex` red-teams a plan before execution. It is a companion skill for `deep-planning-codex`, and it can also be used directly when a plan needs hostile review for stale assumptions, missing validation, rollback gaps, sequencing errors, stakeholder risks, or unsafe execution.

## What This Skill Does

- Reads the plan, criteria, evidence catalog, assumptions, dead ends, probes, and verification plan.
- Selects software, business, or mixed review lenses.
- Checks evidence, order of operations, validation relevance, rollback, permissions, and stakeholder/data risks.
- Classifies findings as `BLOCKING`, `IMPORTANT`, or `NOTE`.
- Returns `PASS`, `FAIL`, or `PARTIAL`.

## Source Provenance

This folder is a Codex-native derivative of:

- Source gist: `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96`
- Source file: `deep_planning.txt`
- Source revision: `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83`
- Source phases adapted: Phase 3 grilling, Phase 6 UltraPlan review, and Phase 7 execution-plan validation
- Source type: user-authored Claude-native deep planning prompt template
- Port depth: new Codex-native companion skill

## Codex Conversion

The source gist relies on Claude-native grilling and planning commands to challenge assumptions. The Codex version makes that challenge explicit as a reusable review skill with severity labels, pass/fail criteria, and write scope.

The conversion is Codex-native because it works without Claude slash commands, does not assume subagents are available, and can review code plans, no-Git work, business artifacts, and mixed workflows using the same artifact contract.

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and default prompt.
- [`references/`](./references): software, business, and mixed review lenses.

## Validation Evidence

Validation before publication covered metadata checks, static forbidden-token scans, and live subagent forward testing on a deliberately flawed plan. The live run returned `FAIL` with blocking findings before execution.

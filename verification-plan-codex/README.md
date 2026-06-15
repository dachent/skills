# Codex Verification Plan Skill

`verification-plan-codex` defines proof criteria before execution. It is a companion skill for `deep-planning-codex`, and it can also be used directly when a plan needs concrete acceptance checks, failure signals, and rollback or recovery triggers.

## What This Skill Does

- Maps each success criterion to at least one proof method.
- Maps each failure criterion to an observable failure signal.
- Supports software, business, and mixed business-coding validation.
- Requires commands, manual checks, expected results, evidence artifacts, and owners where applicable.
- Defines rollback or recovery triggers before execution starts.

## Source Provenance

This folder is a Codex-native derivative of:

- Source gist: `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96`
- Source file: `deep_planning.txt`
- Source revision: `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83`
- Source phases adapted: Phase 7 final plan validation/rollback and Phase 8c verification-before-completion
- Source type: user-authored Claude-native deep planning prompt template
- Port depth: new Codex-native companion skill

## Codex Conversion

The Claude-native source assumes verification is coordinated through the larger prompt and Superpowers workflows. The Codex version makes verification an explicit reusable skill so another agent can invoke it independently, inspect the artifact, and run a deterministic validator.

The conversion is different because Codex benefits from proof artifacts that survive context changes, sandbox boundaries, no-Git projects, and business deliverables where there may be no test suite.

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and default prompt.
- [`references/`](./references): software, business, and rollback/recovery validation guidance.

## Validation Evidence

Validation before publication covered metadata checks, static forbidden-token scans, and live subagent forward testing on a verification fixture. The live run produced concrete commands, expected outputs, failure signals, and recovery triggers.

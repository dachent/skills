# Codex Grill Me Skill

`grill-me-codex` is a Codex-native adaptation of Matt Pocock's upstream
`grill-me-codex` skill. It gives Codex a focused interview mode for stress-testing a
plan, design, product idea, architecture, or implementation direction before the
user commits to it.

## What This Skill Does

- Asks one pointed question at a time.
- Provides a recommended answer with each question.
- Walks the design decision tree in dependency order.
- Reads the codebase or existing artifacts before asking questions whose
  answers are discoverable.
- Keeps the session read-only unless the user separately asks for an artifact or
  implementation work.
- Finishes with confirmed decisions, open questions, risks, and the recommended
  next action.

## Upstream Provenance

This folder is adapted from:

- Source repository: `https://github.com/mattpocock/skills`
- Source branch: `main`
- Source revision: `694fa30311e02c2639942308513555e61ee84a6f`
- Source commit date: `2026-06-10 16:01:44 +0100`
- Source commit subject: `Refine quiz guidelines by standardizing answer length to prevent user clues and enhance assessment integrity.`
- Source folder: `skills/productivity/grill-me`
- Source files reviewed: `SKILL.md`, root `LICENSE`
- Upstream license: MIT License, preserved in [`LICENSE`](./LICENSE)

## Claude-Specific Source Features

The upstream skill is already close to the portable `SKILL.md` convention and
does not use Claude Code tool names, Claude subagents, `$ARGUMENTS`,
`AskUserQuestion`, slash-command-only behavior, or companion `CLAUDE.md`
instructions.

The Claude-specific surface is therefore mostly contextual: the original folder
comes from a skills collection commonly used by Claude-style agents, where the
assistant is expected to infer how to inspect a codebase and how to ask the user
follow-up questions.

## Codex Conversion

The Codex port keeps the upstream behavior and makes the host assumptions
explicit:

| Upstream behavior | Codex adaptation |
| --- | --- |
| Portable `name` and `description` frontmatter | Preserved with a trigger-focused Codex description. |
| "Explore the codebase instead" | Expanded to Codex-native `rg --files`, `rg`, and file-read guidance. |
| Ask questions one at a time | Preserved as the core loop. |
| Provide recommended answers | Preserved and made part of each question. |
| No write behavior specified | Made read-only by default unless the user asks for an artifact. |

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and
  default prompt.
- [`LICENSE`](./LICENSE): upstream MIT license.

## Validation Coverage

Validation for this port covers:

- trigger phrases: `$grill-me-codex`, `grill me`, and stress-test language;
- one-question-at-a-time behavior;
- recommended answer included with each question;
- repo exploration before asking discoverable questions;
- read-only behavior when the user asks only for an interview;
- static checks that no Claude-only active instructions remain.

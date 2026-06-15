# Codex Grill With Docs Skill

`grill-with-docs-codex` is a Codex-native adaptation of Matt Pocock's upstream
engineering skill. It combines a one-question-at-a-time design grilling session
with documentation stewardship for domain language and durable architectural
decisions.

## What This Skill Does

- Stress-tests a plan against existing project terminology, `CONTEXT.md`, ADRs,
  docs, and code.
- Calls out conflicts between user language, documented language, and code
  behavior.
- Asks one pointed question at a time and includes a recommended answer.
- Updates `CONTEXT.md` immediately when domain terms are resolved.
- Offers ADRs sparingly for hard-to-reverse, surprising, tradeoff-backed
  decisions.
- Creates context files and ADR directories lazily only when there is something
  real to write.

## Upstream Provenance

This folder is adapted from:

- Source repository: `https://github.com/mattpocock/skills`
- Source branch: `main`
- Source revision: `694fa30311e02c2639942308513555e61ee84a6f`
- Source commit date: `2026-06-10 16:01:44 +0100`
- Source commit subject: `Refine quiz guidelines by standardizing answer length to prevent user clues and enhance assessment integrity.`
- Source folder: `skills/engineering/grill-with-docs`
- Source files reviewed: `SKILL.md`, `CONTEXT-FORMAT.md`, `ADR-FORMAT.md`,
  root `LICENSE`
- Upstream license: MIT License, preserved in [`LICENSE`](./LICENSE)

## Claude-Specific Source Features

The upstream skill is mostly portable and does not use Claude Code tool names,
Claude subagents, `$ARGUMENTS`, `AskUserQuestion`, `argument-hint`, companion
`CLAUDE.md` behavior, or hidden Claude environment variables.

The source does assume a Claude-style agent will know how to explore a codebase,
ask the user questions, and edit files during the session. It also uses
Markdown links to sibling reference files.

## Codex Conversion

The Codex port preserves the behavior while making host-specific mechanics
explicit:

| Upstream behavior | Codex adaptation |
| --- | --- |
| Explore the codebase when answers are discoverable | Uses Codex-native `rg --files`, `rg`, and file-read guidance. |
| Update `CONTEXT.md` inline | Preserved, with explicit write scope limited to domain docs and accepted ADRs. |
| Sibling `CONTEXT-FORMAT.md` and `ADR-FORMAT.md` | Moved into `references/context-format.md` and `references/adr-format.md` for Codex progressive loading. |
| Ask one question at a time | Preserved. |
| Offer ADRs sparingly | Preserved with the three-condition gate. |
| Portable frontmatter | Kept as Codex-valid `name` and `description` only. |

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and
  default prompt.
- [`references/context-format.md`](./references/context-format.md): glossary
  structure and multi-context guidance.
- [`references/adr-format.md`](./references/adr-format.md): ADR format,
  numbering, and creation criteria.
- [`LICENSE`](./LICENSE): upstream MIT license.

## Validation Coverage

Validation for this port covers:

- trigger phrases: `$grill-with-docs-codex`, docs-backed grilling, and domain-language
  stress testing;
- discovery of `CONTEXT.md`, `CONTEXT-MAP.md`, and `docs/adr/`;
- lazy creation rules for missing docs;
- one-question-at-a-time behavior;
- recommended answer included with each question;
- glossary-only `CONTEXT.md` updates;
- ADR offer gate and numbering behavior;
- static checks that no Claude-only active instructions remain.

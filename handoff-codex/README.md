# Codex Handoff Skill

`handoff-codex` is a Codex-native adaptation of Matt Pocock's upstream handoff skill.
It writes a compact, redacted continuation document for another agent or a
future session.

## What This Skill Does

- Summarizes the current session for a fresh agent.
- Tailors the handoff to the user's invocation text when a next-session focus is
  provided.
- Writes the document to the OS temporary directory rather than the repository.
- References existing artifacts instead of duplicating PRDs, plans, ADRs,
  issues, commits, or diffs.
- Redacts secrets and sensitive personal information.
- Suggests relevant skills for the next agent to invoke.

## Upstream Provenance

This folder is adapted from:

- Source repository: `https://github.com/mattpocock/skills`
- Source branch: `main`
- Source revision: `694fa30311e02c2639942308513555e61ee84a6f`
- Source commit date: `2026-06-10 16:01:44 +0100`
- Source commit subject: `Refine quiz guidelines by standardizing answer length to prevent user clues and enhance assessment integrity.`
- Source folder: `skills/productivity/handoff`
- Source files reviewed: `SKILL.md`, root `LICENSE`
- Upstream license: MIT License, preserved in [`LICENSE`](./LICENSE)

## Claude-Specific Source Features

The upstream skill contains one Claude-style frontmatter field:

| Claude-specific feature | Purpose upstream |
| --- | --- |
| `argument-hint: "What will the next session be used for?"` | Provides slash-command argument help in Claude-style skill UIs. |

The upstream file does not use Claude Code tool names, Claude subagents,
`$ARGUMENTS`, `AskUserQuestion`, companion `CLAUDE.md` behavior, or hidden
Claude environment variables.

## Codex Conversion

The Codex port preserves the handoff behavior and maps the UI-specific field to
Codex metadata:

| Upstream behavior | Codex adaptation |
| --- | --- |
| `argument-hint` frontmatter | Removed from `SKILL.md`; represented as `agents/openai.yaml` `default_prompt`. |
| "If the user passed arguments" | Rephrased as "treat the user's invocation text as the next-session focus." |
| Save to the user's OS temporary directory | Preserved, with Windows and POSIX temp-directory guidance. |
| Do not duplicate other artifacts | Preserved. |
| Redact sensitive information | Preserved and expanded with examples. |

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and
  default prompt.
- [`LICENSE`](./LICENSE): upstream MIT license.

## Validation Coverage

Validation for this port covers:

- trigger phrases: `$handoff-codex`, `handoff-codex`, session summary, and continuation note;
- replacement of `argument-hint` with Codex UI metadata;
- writing to an OS temp path instead of a repo file during actual skill use;
- redaction requirements;
- suggested-skills section;
- artifact-reference behavior instead of duplicating existing docs;
- static checks that no Claude-only active instructions remain.

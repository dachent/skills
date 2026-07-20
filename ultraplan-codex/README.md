# Codex UltraPlan Skill

> **Deprecated for GPT-5.6 Sol — do not install or invoke.** Use native Codex Plan Mode for grounded, decision-complete implementation plans. The remainder of this document is retained as historical implementation reference.

`ultraplan-codex` is a Codex-native adaptation of the upstream UltraPlan skill by
`6missedcalls`. It guides Codex through a deep, read-only implementation
planning workflow before any code is changed.

Use it when a task needs a grounded implementation plan, architectural
decisions, staged codebase exploration, or a durable `.ultraplan/plan.md` that
another agent or engineer can execute.

## What This Skill Does

- Creates or refines `.ultraplan/plan.md` as durable planning state.
- Reads repository context before asking the user questions.
- Asks only for user-owned decisions such as scope, requirements, priorities,
  and tradeoffs.
- Searches for existing code, tests, patterns, and reusable utilities before
  proposing changes.
- Produces one recommended implementation approach instead of a menu of
  alternatives.
- Validates critical file references and verification commands before presenting
  the plan.
- Supports optional adversarial plan review for high-risk changes.
- Falls back cleanly when a directory is not a Git repository.

The skill is intentionally read-only during planning. It allows only the plan
file to be created or updated; implementation edits happen only after the user
separately approves execution.

## Upstream Provenance

This folder is adapted from:

- Source repository: `https://github.com/6missedcalls/ultraplan`
- Source branch: `main`
- Source revision: `06779940475f9c52b4d3b546d309b2c31ebbf8ea`
- Source commit date: `2026-03-31T21:48:42Z`
- Source commit subject: `Initial release: ultraplan skill with autonomous mode companion`
- Source files reviewed: `SKILL.md`, `CLAUDE.md`, `references/planning-patterns.md`,
  `references/anti-patterns.md`, `references/index.md`, `README.md`, `LICENSE`
- Upstream license: MIT License, preserved in [`LICENSE`](./LICENSE)

## Claude-Specific Source Features

The upstream skill was written for Claude Code and included several
Claude-specific surfaces:

| Claude-specific feature | Purpose upstream |
| --- | --- |
| `argument-hint` frontmatter | Shows slash-command argument help in Claude Code. |
| `$ARGUMENTS` | Injects command arguments into the skill prompt. |
| `AskUserQuestion` | Uses Claude Code's structured user-question tool. |
| `Agent` subtypes such as `Explore` and `Plan` | Launches specialized Claude Code subagents. |
| Claude tool names such as `Glob`, `Grep`, `Read`, and `Bash` | Names Claude Code's built-in tools directly. |
| Slash-command UX | Assumes invocation as a Claude Code command-style workflow. |
| Companion `CLAUDE.md` | Adds global autonomous behavior and prompt preferences. |
| Hidden Claude environment variables | Documents Claude-specific switches for planning-agent behavior. |

Those features were not copied as native Codex behavior when no equivalent
exists.

## Codex Conversion

The Codex port preserves the planning workflow while mapping the host-specific
interfaces to Codex-native behavior:

| Upstream behavior | Codex adaptation |
| --- | --- |
| Extra frontmatter fields | `SKILL.md` keeps only `name` and `description`; UI prompt text lives in `agents/openai.yaml`. |
| `$ARGUMENTS` | The user's skill invocation text is treated as the task. |
| `AskUserQuestion` | Codex asks concise direct questions and uses structured question tooling only when available. |
| Claude file/search tool names | Instructions use `rg --files`, `rg`, normal file reads, shell commands, and `multi_tool_use.parallel`. |
| Claude `Explore` and `Plan` agents | Codex explorer/default subagents are used only when the user explicitly asks for parallel agent work; otherwise the workflow runs locally. |
| Claude slash command | Invoke as `$ultraplan-codex`, through the skills picker, or by saying `ultraplan-codex`. |
| Companion `CLAUDE.md` autonomy | Mapped to optional Codex `AGENTS.md`, memories, permissions, or plugin packaging guidance, but not embedded in the skill. |
| Hidden Claude env vars | Documented as unsupported in Codex and excluded from active instructions. |

The port also adds two Codex-specific refinements discovered during live
forward-testing:

- non-Git directories record `Git context: not a git repository` and continue;
- report-only or forward-test prompts do not ask for execution approval.

## Files

- [`SKILL.md`](./SKILL.md): active Codex skill instructions.
- [`agents/openai.yaml`](./agents/openai.yaml): Codex app display metadata and
  default prompt.
- [`references/planning-patterns.md`](./references/planning-patterns.md):
  optional plan structures and exploration patterns.
- [`references/anti-patterns.md`](./references/anti-patterns.md): planning
  failure modes and mitigations.
- [`references/codex-port-notes.md`](./references/codex-port-notes.md): port
  mapping, validation matrix, and static-check guidance.
- [`LICENSE`](./LICENSE): upstream MIT license.

## Validation Evidence

The port was validated before publication with:

- Codex skill metadata validation via `skill-creator/scripts/quick_validate.py`.
- Static scan of active `SKILL.md` for Claude-only live instruction terms:
  `AskUserQuestion`, `$ARGUMENTS`, `argument-hint`, Claude `subagent_type`
  strings, and `CLAUDE_CODE_PLAN`.
- Whole-folder checks for required files, ASCII content, missing placeholders,
  existing referenced paths, and feature-coverage markers.
- Live subagent forward-testing on fixture projects:
  - baseline planning without the skill,
  - normal `$ultraplan-codex` planning,
  - existing-plan refinement,
  - explicit parallel-agent wording with local fallback,
  - report-only planning in a non-Git directory.

The live tests verified that skill-guided runs wrote only `.ultraplan/plan.md`,
kept implementation files unchanged, produced file-path-grounded plans, included
verification commands, handled non-Git fixtures, and avoided execution approval
questions for report-only prompts.

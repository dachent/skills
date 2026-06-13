# Codex Port Notes

This skill is adapted from `6missedcalls/ultraplan` for Codex. The original planning workflow is preserved, but Claude Code-specific surfaces are mapped to Codex-native behavior.

## Mapping

| Original surface | Codex adaptation |
| --- | --- |
| Extra frontmatter fields | Keep only `name` and `description` in `SKILL.md`; put UI prompt text in `agents/openai.yaml`. |
| Invocation argument token | Treat the user's skill invocation text as the task. |
| Claude structured question helper | Ask concise direct questions; use Codex structured question tooling only when available. |
| Claude file/search/shell tool names | Use Codex file reads, `rg --files`, `rg`, shell commands, and `multi_tool_use.parallel`. |
| Claude exploration/design agent subtypes | Use Codex explorer/default subagents only when explicitly authorized; otherwise do local exploration and design. |
| Claude slash command UX | Invoke as `$ultraplan`, via the skills picker, or by using "ultraplan" in the prompt. |
| Global `CLAUDE.md` companion | Use Codex `AGENTS.md`, permissions, memories, or plugin packaging when the user explicitly wants durable behavior. |
| Hidden Claude environment variables | Unsupported in Codex; do not represent these as Codex features. |

## Port Boundaries

- This package is a portable skill folder, not an installed global skill.
- Do not modify `~/.codex`, `.agents`, `AGENTS.md`, project config, or plugin manifests unless the user explicitly asks.
- Do not copy global autonomy instructions into the skill. Planning should remain read-only until the user approves execution.

## Feature Validation Matrix

Use this matrix when changing the port:

- Triggering: `$ultraplan`, plain "ultraplan", implicit complex planning prompts, and app metadata.
- Setup: new `.ultraplan/plan.md`, existing-plan detection, continue-vs-fresh prompt, git context capture.
- Non-git fallback: copied fixtures and archives should record that git metadata is unavailable and continue planning.
- Read-only mode: no implementation edits, installs, commits, pushes, migrations, or formatting during planning.
- Requirements interview: explores before asking and asks only non-discoverable questions.
- Exploration: uses repository search, file reads, reusable utility discovery, test discovery, and path/line capture.
- Parallel exploration: uses Codex subagents only when explicitly permitted; local fallback remains complete.
- Architecture design: synthesizes one recommended approach and avoids alternative paralysis.
- Plan output: concise final plan with context, changes, implementation sequence, risks, and verification.
- Plan validation: rereads critical files, verifies references, checks sequence, and checks verification relevance.
- Adversarial review: used for high-risk plans, through an authorized Codex reviewer/default subagent or local review.
- Execution handoff: rereads `.ultraplan/plan.md`, follows sequence, runs verification, and reports failures honestly.
- Report-only prompts: should not ask for execution approval when the user explicitly requested a planning report or forward-test summary.
- References: loads `planning-patterns.md` and `anti-patterns.md` only when relevant.
- Claude-specific companion features: not represented as native Codex capabilities.

## Static Checks

Before distributing, scan active instructions for unsupported Claude-only names that should not remain as live commands. The active `SKILL.md` should not instruct Codex to use Claude-specific helper names, invocation variables, or hidden environment variables.

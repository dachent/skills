---
name: handoff-codex
description: "Use when the user asks for a handoff, session summary, context packet, continuation note, or wants another agent or future session to pick up the current work."
---

# Codex Handoff

## Purpose

Write a concise handoff document so a fresh agent or future session can continue the work without rereading the whole conversation.

## Destination

Save the handoff document to the operating system temporary directory, not the current workspace:

- Windows: use `$env:TEMP`.
- macOS/Linux: use `${TMPDIR:-/tmp}`.

If the session permissions block the OS temp directory, use the nearest approved temporary location and state that substitution clearly. Do not modify repository files for a handoff unless the user explicitly asks for a repo-tracked artifact.

After writing the file, tell the user its absolute path.

## When Invoked By deep-planning-codex

- Write the handoff under `.deep-planning/handoffs/<gate>.md` unless the user or current permissions explicitly forbid repo planning artifacts.
- Include the current `.deep-planning/state.md` status, next action, blockers, and validation gaps.
- End with a Deep Planning Delta for the orchestrator to merge into `.deep-planning/state.md`, including the handoff path as an updated artifact.
- Keep the same redaction rules as temp-directory handoffs.

## Input Focus

Treat the user's invocation text as the intended focus of the next session. If the user gives no focus, infer it from the latest active task and call out that inference in the handoff.

## Required Content

Include:

- next-session objective;
- current status;
- important decisions and assumptions;
- relevant files, branches, commits, PRs, issues, and URLs;
- commands already run and their important results;
- remaining tasks in recommended order;
- known blockers, risks, and validation gaps;
- suggested skills the next agent should invoke.

Do not duplicate content already captured in PRDs, plans, ADRs, issues, commits, diffs, or other artifacts. Reference those artifacts by path or URL instead.

## Safety

- Redact API keys, passwords, tokens, private personal data, and other sensitive information.
- Preserve enough context to continue the work, but do not copy long private conversation passages.
- Do not commit, push, install dependencies, run migrations, or make implementation edits as part of writing a handoff.

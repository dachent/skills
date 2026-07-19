---
name: handoff-codex
description: "Use when the user asks for a handoff, session summary, context packet, continuation note, or wants another agent or future session to pick up the current work."
---

# Codex Handoff

## Purpose

Write a concise handoff document so a fresh agent or future session can continue the work without rereading the whole conversation.

## Destination

Save the handoff under the active session folder unless the user specifies another destination. For projectless sessions, follow the workstation policy for resolving the real Documents folder and creating a dated session folder.

Use the operating system temporary directory only when the active instructions explicitly permit it. Do not modify repository files for a handoff unless the user explicitly asks for a repo-tracked artifact.

After writing the file, tell the user its absolute path.

## Native Plan Mode

- Include the current objective, next action, blockers, decisions, and validation gaps from the conversation and inspected artifacts.
- Do not require or create a repository planning workfolder.
- If the current collaboration mode prohibits writes, return the complete handoff in conversation instead of writing a file.
- Keep the same redaction rules for every destination.

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

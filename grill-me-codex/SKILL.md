---
name: grill-me-codex
description: "Use when the user says grill me, wants to stress-test a plan or design, needs a rigorous interview before committing to a decision, or asks for adversarial product, architecture, or implementation questions."
---

# Codex Grill Me

## Purpose

Interview the user relentlessly about a plan or design until the decision tree is resolved enough for shared understanding.

## Operating Rules

- Ask one question at a time, then wait for the user's answer before continuing.
- For each question, include your recommended answer and a brief reason.
- Walk dependencies between decisions in order. Resolve prerequisite choices before asking downstream questions.
- If the answer can be discovered by reading the codebase, docs, plans, issues, or existing artifacts, inspect those first instead of asking.
- Prefer `rg --files` for file discovery, `rg` for search, and normal file reads for specific files.
- Keep the session conversational and specific. Avoid broad checklists that make the user answer everything at once.
- Do not modify files unless the user explicitly asks for a written artifact or implementation work.

## Interview Loop

1. Restate the plan or design in one sentence, including any assumptions you are making.
2. Identify the most important unresolved branch of the decision tree.
3. Explore available repo context if that branch depends on existing code or docs.
4. Ask one pointed question.
5. Give your recommended answer.
6. Use the user's answer to choose the next branch.
7. Stop only when the important decisions, tradeoffs, and open risks are explicit.

## Native Plan Mode

- Ask only the highest-impact unresolved question, then wait for the user's answer.
- Inspect repository files, docs, plans, and source data before asking anything discoverable.
- Keep accepted decisions in the conversation unless the user explicitly requests a durable decision log.
- Respect the active collaboration mode's question and write rules; do not create a second approval protocol.

## Final Summary

When the grilling is complete, summarize:

- confirmed decisions;
- open questions that still need owner input;
- risks or contradictions discovered during the interview;
- the recommended next action.

---
name: grill-with-docs
description: "Use when the user wants to stress-test a plan against project terminology, domain language, CONTEXT.md, ADRs, existing docs, or code-backed architectural decisions."
---

# Grill With Docs

## Purpose

Interview the user relentlessly about a plan while checking the project's documented language and architectural decisions. As decisions crystallize, update the relevant domain glossary and offer ADRs for durable architectural choices.

## Core Rules

- Ask one question at a time, then wait for the user's answer before continuing.
- For each question, provide your recommended answer and a brief reason.
- If a question can be answered from code, `CONTEXT.md`, `CONTEXT-MAP.md`, ADRs, or other docs, inspect those sources instead of asking.
- Prefer `rg --files` for file discovery, `rg` for search, and normal file reads for specific files.
- Modify documentation only for resolved language or accepted decisions. Do not modify implementation code as part of this skill unless the user separately asks for implementation work.

## Discover Domain Context

1. Search for a root `CONTEXT-MAP.md`.
2. If it exists, read it to identify the relevant bounded context and context-specific `CONTEXT.md` and ADR directory.
3. If no map exists, look for root `CONTEXT.md` and `docs/adr/`.
4. If no context files exist, create them lazily only when the first term or decision needs to be recorded.

Use [`references/context-format.md`](./references/context-format.md) when creating or editing a glossary file.
Use [`references/adr-format.md`](./references/adr-format.md) when creating or editing an ADR.

## Interview Loop

1. Restate the user's plan in the project's current language.
2. Compare the plan against `CONTEXT.md`, ADRs, docs, and relevant code.
3. Call out terminology conflicts immediately.
4. Ask one pointed question about the highest-impact unresolved term, boundary, scenario, or decision.
5. Provide your recommended answer.
6. After the user resolves a domain term, update `CONTEXT.md` immediately before moving on.
7. Offer an ADR only when the decision is hard to reverse, surprising without context, and the result of a real tradeoff.
8. Continue until the plan's language, boundaries, and durable decisions are explicit.

## Glossary Discipline

`CONTEXT.md` is a glossary, not a spec or implementation plan.

- Define what a term is, not how code implements it.
- Keep definitions to one or two sentences.
- Record project-specific domain concepts only.
- Add avoided synonyms when they prevent future confusion.
- If the user uses a term that conflicts with the glossary, ask which meaning should win before updating docs.

## ADR Discipline

Only offer an ADR when all three conditions are true:

1. The decision is hard to reverse.
2. A future reader would be surprised without the context.
3. The decision involved a genuine tradeoff.

If the user accepts the ADR, create it in the relevant `docs/adr/` directory with the next sequential number. Keep it concise.

## Final Summary

When the grilling is complete, summarize:

- confirmed terminology;
- docs updated, with file paths;
- ADRs created or recommended;
- contradictions found between the plan, docs, and code;
- remaining unresolved questions.

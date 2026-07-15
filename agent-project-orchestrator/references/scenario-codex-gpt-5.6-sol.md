# Scenario: Codex with GPT-5.6 Sol

## Operating contract

Provide a lean outcome contract containing the objective, current-state evidence, hard constraints, authority boundaries, success criteria, allowed capability graph, and required output schemas. Avoid duplicating detailed provider methodology in the top-level prompt.

## Control policy

- Continue autonomously within an approved bounded sprint.
- Stop only for a reserved human decision, material scope change, destructive/external action, failed foundational assumption, unavailable required capability, or inability to demonstrate correctness.
- Update durable state at milestones using structured deltas.
- Load providers lazily when their capabilities become necessary.
- Permit up to two bounded repair attempts.
- Limit parallel workers to three and keep one authoritative state writer.
- Keep intermediate artifacts compact while preserving evidence and resume fidelity.

## Routing behavior

The router supplies an approved capability graph rather than a universal fixed sequence. Sol may choose and reorder capabilities within that graph as evidence changes, but it may not weaken project invariants, invent a missing required provider, or change the success contract silently.

## Verification

Require a sealed or fresh-context terminal review at independence level 3 or higher. The terminal reviewer receives the original contract, actual outputs, current workspace revision, required checks, and fresh evidence rather than the implementer's prior verdict.

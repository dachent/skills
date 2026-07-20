# Code Intelligence

Supported Claude Code provider router for explicit repository-analysis routing across persistent graphs, Python-specific mapping, and selective semantic flow.

It is not for Codex GPT-5.6 Sol. Native direct inspection, Plan Mode, explorer work, and subagents cover the same routing function without an added analyzer.

The folder intentionally contains rich architectural context because provider choice, freshness, privacy, and performance are part of correctness. Start with `SKILL.md`, then read `references/implementation-plan.md` and the ADRs.

## Current implementation

- deterministic route helper;
- low-overhead provider and Graphify-state preflight;
- alternating runtime benchmark harness;
- unit tests;
- provider-neutral contracts and architectural decisions.

## Supported scope

Use only when Claude Code must select among already-installed Graphify, `code-mapper-skill`, and selective CodeQL providers. Provider selection remains benchmark-driven. Graphify is not assumed to be the permanent best code-only discovery engine; other engines remain evaluation candidates rather than automatic routes.

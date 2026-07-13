# Code Intelligence

Experimental control-plane skill for routing repository questions across persistent graphs, exact semantic navigation, Python-specific mapping, semantic flow, and durable planning.

The folder intentionally contains rich architectural context because provider choice, freshness, privacy, and performance are part of correctness. Start with `SKILL.md`, then read `references/implementation-plan.md` and the ADRs.

## Current implementation

- deterministic route helper;
- low-overhead provider and Graphify-state preflight;
- alternating runtime benchmark harness;
- unit tests;
- provider-neutral contracts and architectural decisions.

## Current status

Experimental. The initial control plane is usable, but default provider selection must remain benchmark-driven. Graphify is not assumed to be the permanent best code-only discovery engine; Codebase-Memory, Serena/LSP, SCIP, CodeQL, and Joern/codebadger are explicitly included in the evaluation path.

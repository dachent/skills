# ADR-0006: Keep the MVP Provider Set Minimal

- Status: accepted
- Date: 2026-07-12

## Context

The initial design considered Serena, Joern/codebadger, SCIP/Sourcegraph, Semgrep, Aider-style maps, and a generic provider framework. Each adds real capability, but none currently addresses a demonstrated recurring gap that outweighs its installation, maintenance, failure, and cognitive cost.

## Decision

The MVP supports only direct source, Graphify, `code-mapper-skill`, selective CodeQL already integrated into the mapper, and explicit `repo-map-codex`. Codebase-Memory remains benchmark-only. All other provider integrations are out of scope.

## Consequences

- The router remains a thin policy layer rather than becoming a platform.
- Every active route maps to an implemented, differentiated capability.
- Future additions require a recurring use case, benchmark evidence, an ADR, and a failure fallback.

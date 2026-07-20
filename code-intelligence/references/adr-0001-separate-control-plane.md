# ADR-0001: Create a Separate Code-Intelligence Control Plane

- Status: accepted
- Date: 2026-07-12

## Context

`code-mapper-skill` is a supported Python-focused analyzer with a stable command and output contract. Graphify and other graph or semantic engines have different scopes, dependencies, refresh lifecycles, privacy boundaries, and failure modes.

## Decision

Create `code-intelligence` as a separate top-level supported Claude Code provider router. Keep providers independently installed and independently callable. Do not use this router for Codex GPT-5.6 Sol, whose native inspection and planning controls already cover the routing need.

## Consequences

- Existing mapper behavior and benchmarks remain meaningful.
- The router can support non-Python and future providers without misrepresenting the mapper.
- Repository taxonomy, metadata, validation, and rollback are explicit.
- There is an additional skill surface and potential trigger overlap, which must be controlled by precise descriptions and routing rules.

## Rejected alternatives

- Embed Graphify inside `code-mapper-skill`: rejected because it changes the mapper's scope and lifecycle.
- Rename code-mapper into the umbrella router: rejected as a breaking semantic change.
- Create a separate GitHub repository immediately: rejected because the router is tightly coupled to this repository's skills and has no independent release requirement yet.

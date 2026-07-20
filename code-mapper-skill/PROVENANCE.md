# Provenance

## 2026-07-19 modernization

- Replaced ambient dependency installation with a read-only exact-version preflight.
- Removed raw Git clone, fetch, and pull behavior; only approved local worktrees are accepted.
- Required an explicit session work root for all reports and caches.
- Gated CodeQL writes behind explicit consent and removed automatic pack installation.
- Preserved the local-path CLI and JSON graph contract for Claude Code and Codex callers.

## Source

`code-mapper-skill` is a repository-owned implementation first added in commit
`8e618aa9f4d94b436d9edad8d075d3f715269641`, expanded with artifact and contract
mapping in `232aadd204b760dfef0fcfce6636242b362e604d`, and converted to the current
single-entrypoint selective CodeQL lifecycle in
`979de60502346f555f2a260cd2ba5fad6134948c`.

No external source repository was copied into this skill. It composes public
libraries and tools with repository-owned orchestration and extraction logic.

## Classification

- Source classification: repo-owned original
- Third-party Python dependencies: `grimp==3.15`, `jedi==0.20.0`
- Optional external tool: CodeQL CLI
- Current interface: one JSON-producing `blast_radius.py` entrypoint
- CodeQL modes: `off`, `existing`, `auto`, and `build`, all subject to policy and budget gates
- Standards parsed or emitted: OpenAPI, AsyncAPI, GraphQL, Protobuf, JSON Schema, Avro, Pact, Backstage, and OpenLineage-compatible events

## Authorship boundary

The import and reference graph, AST and contract extraction, CodeQL policy and
lifecycle, output graph, tests, and benchmarks are maintained in this repository.
Third-party package and CodeQL CLI code is not vendored.

## License review

Dependency and tool licenses remain governed by their upstream projects. The
repository does not yet publish a root license, so redistribution rights for the
combined repository should not be assumed until the licensing policy is resolved.

## Last review

- Reviewed: 2026-07-11
- Owner: `@dachent`

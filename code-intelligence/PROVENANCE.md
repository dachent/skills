# Provenance

## Source

`code-intelligence` is a repository-owned original orchestration skill created for `dachent/skills` on 2026-07-12. It does not copy or vendor Graphify, code-mapper, Serena, SCIP, Sourcegraph, CodeQL, Joern, codebadger, Codebase-Memory, Semgrep, or Aider implementation code.

## Classification

- Source classification: repo-owned original
- Runtime classification: prompt and lightweight Python control plane
- External providers: optional and independently installed
- Canonical directory: `code-intelligence/`
- Current status: supported Claude Code provider router
- Codex GPT-5.6 Sol: not applicable; native direct inspection, Plan Mode, explorer work, and subagents provide the routing capability without this package

## Authorship boundary

This repository owns the routing policy, freshness policy, provider contract, performance gates, deterministic helper scripts, tests, implementation plan, and architectural decision records.

Third-party provider code, indexes, models, CLIs, MCP servers, language servers, and licenses remain governed by their upstream projects.

## Research basis

The alternatives review uses public primary documentation and project repositories reviewed on 2026-07-12. Performance and quality claims attributed to external projects are identified as project-reported or paper-reported and are not treated as independently reproduced results.

## License review

No third-party source is vendored. Invoking an external provider does not grant redistribution rights. Each provider must pass a separate license, privacy, and deployment review before being made a default dependency.

## Owner

- Owner: `@dachent`
- Last reviewed: 2026-07-12

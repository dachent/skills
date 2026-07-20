# Benchmark Plan

## Benchmark 1: Router overhead on code-mapper — RETIRED

The router is not a runtime process. `route.py` exposes `decide_route` as an
importable, side-effect-free policy function; Claude applies the decision tree
in-context by reading `routing-policy.md`. There is no CLI to invoke between the
request and `code-mapper-skill`, so there is no per-call router overhead to
measure and no gate to meet.

This benchmark previously measured invoking `route.py` as a subprocess ahead of
the mapper. That path was removed: it added ~130 ms of interpreter and import
startup per call (dominated by `argparse`→`shutil` and `dataclasses`→`inspect`
imports) for zero routing benefit, and it failed its own 75 ms / 5 % / 200 ms
gates by 2–5x when measured. Correctness of the policy is covered by
`scripts/test_route.py`, which imports `decide_route` directly at ~0 ms marginal
cost. The freshness / provider-independence invariants that used to ride on this
benchmark (zero graph JSON reads, zero Graphify subprocesses on the known-target
path) are asserted structurally by `test_route.py` / `test_preflight.py` instead.

## Benchmark 2: Discovery-provider value

Compare only:

1. direct source exploration;
2. Graphify;
3. Codebase-Memory;
4. router-selected Graphify/direct-source flow.

Use pinned unfamiliar repositories across Python, TypeScript, Java, Go, Rust, a polyglot service repository, and at least one mixed code/document/media project.

Measure:

- key-fact precision and recall;
- top-one and top-three file or symbol accuracy;
- source citation accuracy;
- false relationship rate;
- answer quality under fixed model, token, turn, and time budgets;
- index build, incremental update, query latency, memory, disk, tokens, and tool calls.

Codebase-Memory remains unintegrated unless it demonstrates a material advantage without a material precision regression.

## Benchmark 3: Selective CodeQL value inside code-mapper

Compare:

1. mapper structural output without CodeQL;
2. mapper with its existing selective CodeQL enrichment.

Use curated and pinned real-world Python source-to-sink tasks. Measure true paths, false paths, missed paths, path explainability, database/build cost, query cost, and whether unrelated mapper requests incur any additional work.

Acceptance requirements:

- selective CodeQL improves useful path evidence on its intended tasks;
- it remains off by default for unrelated work;
- failure or absence degrades explicitly to structural mapper output rather than silently changing claims.

## Evaluation discipline

- Pin repository and provider revisions.
- Alternate baseline and candidate order.
- Use at least two warmups and 15 measured runs; use 30 for stable p95 estimates.
- Publish raw samples and environment metadata.
- Separate index-build cost from warm-query cost.
- Separate router overhead from deliberate provider work.
- Use equal model, token, turn, source-access, and time budgets for quality comparisons.

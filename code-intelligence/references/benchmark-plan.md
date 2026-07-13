# Benchmark Plan

## Benchmark 1: Router overhead on code-mapper

### Question

How much latency and resource overhead does `code-intelligence` add when the correct route is directly to `code-mapper-skill`?

### Conditions

- baseline: invoke `code-mapper-skill/scripts/blast_radius.py` directly;
- candidate: invoke through the router with identical mapper arguments;
- fixtures: 11, 123, and at least 603 Python modules plus contracts;
- modes: module-only and Jedi symbol references;
- caches: warm and cold;
- Graphify states: absent, installed without graph, fresh graph, stale flag, and large graph present.

### Metrics and gates

- median absolute overhead at most 75 ms;
- median relative overhead at most 5 percent;
- p95 absolute overhead at most 200 ms;
- zero graph JSON reads;
- zero Graphify subprocesses;
- equivalent mapper output apart from route provenance.

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

## Experimental discipline

- Pin repository and provider revisions.
- Alternate baseline and candidate order.
- Use at least two warmups and 15 measured runs; use 30 for stable p95 estimates.
- Publish raw samples and environment metadata.
- Separate index-build cost from warm-query cost.
- Separate router overhead from deliberate provider work.
- Use equal model, token, turn, source-access, and time budgets for quality comparisons.

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

### Metrics

- median and p95 wall time;
- CPU time and peak RSS;
- subprocess count;
- bytes read from `graphify-out`;
- output equivalence;
- provider route accuracy.

### Gates

- median absolute overhead at most 75 ms;
- median relative overhead at most 5 percent;
- p95 absolute overhead at most 200 ms;
- zero graph JSON reads;
- zero Graphify subprocesses.

## Benchmark 2: Discovery quality

### Conditions

Compare:

1. direct grep and file exploration;
2. Graphify;
3. Codebase-Memory;
4. Aider-style repository map;
5. graph discovery followed by precise provider;
6. router-selected hybrid.

Use unfamiliar repositories across Python, TypeScript, Java, Go, Rust, and a polyglot service repository.

### Task families

- locate feature implementation;
- explain request-to-database flow;
- identify likely files for a defect;
- architecture and boundary questions;
- impact of a proposed subsystem change;
- cross-service route and event relationships.

### Metrics

- key-fact precision and recall;
- correct file and symbol ranking;
- source citation accuracy;
- false relationship rate;
- answer quality under fixed model, token, turn, and time budgets;
- indexing time, incremental update time, query latency, memory, disk, tokens, and tool calls.

## Benchmark 3: Exact semantic navigation

Compare code-mapper/Jedi, tree-sitter graph providers, Serena/LSP, and SCIP indexes for definitions, references, implementations, type hierarchy, and change impact.

Measure precision, recall, unresolved symbols, cross-repository coverage, setup time, and update latency.

## Benchmark 4: Data flow and security

Compare current mapper CodeQL enrichment, full CodeQL, Joern/codebadger, and Semgrep on curated and real-world source-to-sink tasks.

Measure true paths, false paths, missed paths, path explainability, build time, query time, peak resources, and language coverage.

## Experimental discipline

- Pin repository revisions and provider versions.
- Alternate baseline and candidate execution order.
- Use at least two warmups and 15 measured runs; use 30 runs for stable p95 estimates.
- Publish raw samples and environment metadata.
- Separate index-build cost from query cost.
- Separate router overhead from deliberate provider work.
- Do not compare quality under unequal model, token, turn, or source-access budgets.

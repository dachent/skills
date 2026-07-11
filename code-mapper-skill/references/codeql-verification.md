# CodeQL integration verification

The test matrix covers:

1. **Policy truth table:** all modes/intents, thresholds, cache/database states, CLI/version states, timeout/failure history, reuse, temporary repositories, and time/storage budgets. Repository size alone must never build.
2. **AST triggers:** exact/unresolved paths, transforms, parameters, file modes, literal/dynamic SQL, config, HTTP, events, models, subprocesses, deterministic sink locations, and fingerprints.
3. **Lifecycle with mocked CLI:** no default probe/build, no installation, version gate, `--build-mode=none`, external cache location, atomic replacement, partial cleanup, invalidation, result reuse, query/sink keying, timeouts, and base-map survival.
4. **Real CodeQL smoke:** official CLI builds a tiny Python database, compiles/runs the generated query, decodes BQRS with string entities, and verifies merged semantic edges.
5. **Canonical interface:** one mapper command, one JSON graph, rejected removed flags, no duplicate mapper entrypoints, valid UTF-8 output, and no agent-specific interface.
6. **Read-only behavior:** target tree hash before/after; writes restricted to mapper caches.
7. **Performance:** 12-, 122-, and 602-module structural and sink-heavy fixtures; cold/warm median and p95; default policy without a database. Gates are 10% median scanner overhead and 5 ms default-policy median.
8. **Repository validation:** compileall, scanner and CLI integration tests, policy/runtime tests, benchmark gates, repository validators, and hosted Windows CI.

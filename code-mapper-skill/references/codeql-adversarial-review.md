# Adversarial review: selective CodeQL integration

## Verdict

**PASS after revision.** The initial plan had blocking safety and policy gaps; the implementation and tests address them.

## Findings and resolutions

- **BLOCKING — Query value and database-build value were conflated.** A cheap query threshold cannot justify indexing. The implementation uses separate semantic-need and build scores; builds additionally require reuse and budget evidence.
- **BLOCKING — Silent default builds would break latency expectations.** Default mode is `existing`: use current cached results or a current database, but never build. `off`, `auto`, and explicit `build` modes are available.
- **BLOCKING — Extraction could execute target code.** Database creation requires CodeQL 2.16.4+ and always uses Python `--build-mode=none`; there is no fallback to autobuild or project commands.
- **BLOCKING — Stale databases/results could appear current.** Database freshness keys repository root, Python-source fingerprint, and CodeQL version. Results additionally key query template and selected sinks.
- **BLOCKING — CodeQL failure could destroy the base map.** Missing CLI, unsupported version, build/query failure, corrupt output, and timeouts retain Grimp/Jedi/AST output. Partial databases are removed. Matching timeouts suppress automatic retry.
- **IMPORTANT — Broad queries would duplicate AST work.** The AST layer selects concrete sink file, line, and argument positions. One generated query combines local value and local taint flow.
- **IMPORTANT — Capability labels overstated cross-function analysis.** The metric is `parameterizedHighValueSinks`; global/interprocedural flow is out of scope.
- **IMPORTANT — Exact SQL was incorrectly counted as dynamic.** Dynamic SQL follows actual resolution confidence.
- **IMPORTANT — Mock tests cannot validate QL syntax.** CI installs the official CLI and runs a live database/create/query/decode smoke test.
- **NOTE — Heuristic weights require calibration.** Decisions, timings, failures, builds, queries, and findings are persisted locally; budgets remain configurable.

## Operational controls

- `--codeql off` disables semantic enrichment.
- All CodeQL data is under the mapper cache; deleting it cannot affect target source.
- There is one mapper entrypoint and one JSON graph. No legacy output or compatibility path is maintained.

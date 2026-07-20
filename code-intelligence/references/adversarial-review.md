# Adversarial Review

Reviewed: 2026-07-12
Method: six independent review lenses applied before the final implementation gate.

## Verdict

PASS after the scope reductions and CI repairs in the final implementation plan. The earlier broad provider catalog was over-designed and the earlier completion claim was invalid because required CI had not concluded successfully.

## Independent review lenses

### Minimalism and product value

**BLOCKING:** The original design treated many engines, protocols, and wrappers as peer providers without demonstrated recurring use.

**Required fix:** Limit the Claude Code router to direct source, Graphify, code-mapper, and mapper-owned selective CodeQL. Durable planning remains harness-native, not a provider route. Keep only Codebase-Memory as a benchmark candidate.

### Correctness and evidence

**IMPORTANT:** Provider outputs can be mistaken for final truth.

**Required fix:** Preserve evidence type and require verification against current source and tests.

### Performance

**BLOCKING:** Any graph read or subprocess on the known-target mapper path is unjustified overhead.

**Required fix:** Enforce the zero-Graphify fast path and benchmark gates in issue #53.

### Operations and maintainability

**BLOCKING:** Serena, Joern/codebadger, SCIP/Sourcegraph, Semgrep, Aider-style maps, and a generic provider registry add installation, version, failure, documentation, and support surfaces before value is proven.

**Required fix:** Remove them from active routing and preflight. Do not implement speculative adapters.

### Security and privacy

**IMPORTANT:** Automatic index building, semantic extraction, or external service use could expose private repositories or create unbounded work.

**Required fix:** Never auto-build or auto-refresh. Keep CodeQL selective and explicit through the existing mapper path.

### Delivery and CI

**BLOCKING:** Three files referenced by `SKILL.md` were missing, and work was reported complete before required PR checks finished.

**Required fix:** Add the missing files, run repository-wide validation, wait for the final required check, and treat a red or pending PR as incomplete.

## Re-review result

The final plan passes because it removes speculative integrations, retains only differentiated components, establishes measurable adoption gates, and makes green required CI a completion condition.

# Minimal Provider Contract

## Principle

This is an orchestration envelope, not a generalized plugin framework. Preserve provider-native output and add only the metadata needed to route, audit, and verify it.

## Route input

```json
{
  "repository": "/path/to/repo",
  "intent": "broad-discovery | python-impact | artifact-lineage | security-flow | durable-plan | direct-source",
  "language": "python",
  "targetFile": "pkg/service.py",
  "targetSymbol": "run",
  "graphState": "fresh | code_stale | semantic_stale | unknown | corrupt | missing",
  "available": ["graphify", "code-mapper", "codeql"]
}
```

Only fields relevant to the task are required.

## Route result

```json
{
  "primary": "code-mapper",
  "secondary": [],
  "mustLoadGraph": false,
  "requiresSourceVerification": true,
  "reasons": ["exact Python target is already known"],
  "warnings": []
}
```

## Evidence envelope

When a provider is invoked, record:

- provider and version;
- repository root and revision;
- freshness state, if persistent data was used;
- invocation scope and relevant options;
- latency and failure status;
- source locations or provider-native evidence artifact;
- warnings, inference status, and fallback use.

Do not translate all evidence into a common anonymous graph. A Graphify inferred relationship, a mapper AST extraction, a Jedi reference, and a CodeQL path are not equivalent evidence.

## Boundaries

- `code-mapper-skill` remains Graphify-agnostic.
- Graphify is never loaded on the known-target mapper path.
- CodeQL is currently reached through the mapper's selective Python integration, not through a new standalone adapter.
- `repo-map-codex` is invoked only for an explicit durable planning deliverable.
- Direct source and tests remain the final authority.

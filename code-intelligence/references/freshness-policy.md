# Persistent Graph Freshness Policy

## States

| State | Meaning | Allowed use |
| --- | --- | --- |
| `missing` | No usable graph | Build only when justified or use another route |
| `fresh` | Provenance matches current source state | Query normally |
| `code_stale` | Code changed after graph provenance | Refresh deterministic code index before material use |
| `semantic_stale` | Documents or other semantic sources changed | Warn or refresh under explicit privacy/model policy |
| `unknown` | Provenance cannot establish freshness | Exploratory use with
# Agent project state

Planned authoritative contents:

- `state.db` — SQLite source of truth;
- `events.jsonl` — append-only audit and recovery log;
- `config.yaml` — project and policy configuration;
- `views/` — generated human-readable state;
- `evidence/` — indexed evidence artifacts;
- `handoffs/` — generated continuation packets;
- `exports/` — portable snapshots.

Do not manually create `state.db` from this template. Use the future runtime initializer.

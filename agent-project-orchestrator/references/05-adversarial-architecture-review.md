# Adversarial architecture review

## Review method

The design was attacked from independent perspectives covering:

- systems architecture;
- simplicity and implementation scope;
- state integrity;
- concurrency and crash recovery;
- provider contracts;
- skill invocation semantics;
- QC and smoke testing;
- bootstrap reliability;
- security and prompt injection;
- supply-chain trust;
- licensing;
- terminal-review independence;
- memory quality;
- workspace drift;
- observability;
- long-running autonomy.

The environment used for the review did not expose a literal subagent dispatcher, so these were separate adversarial passes rather than isolated spawned agents.

## Overall verdict

The conceptual direction is strong. The first proposed implementation was too broad and too dynamic.

The design should proceed only after narrowing the first release to:

- one deterministic project runtime;
- one authoritative state store;
- two thin harness adapters;
- fixed, pinned provider bindings;
- explicit trust and approval boundaries;
- deterministic QC;
- fresh terminal review;
- staged migration from the existing scaffold.

## Finding 1: distributed monolith risk

A superficially modular design can still require simultaneous changes across:

- schemas;
- runtime;
- templates;
- Claude adapter;
- Codex adapter;
- provider contracts;
- smoke tests;
- handoff rendering;
- migration logic;
- generated documentation.

### Correction

Keep the runtime core narrow:

- state machine;
- transactional storage;
- backlog and memory;
- evidence and traceability;
- policy enforcement;
- provider invocation protocol.

Keep detailed planning methodology in skill/provider instructions and references.

## Finding 2: premature abstraction

The initial proposal included too many dimensions before a working runtime existed:

- seven project-state modes;
- six delivery modes;
- five workflow profiles;
- multiple execution backends;
- dynamic providers;
- external trackers;
- plugins, adapters, ports, and generated templates.

### Correction

Start with:

- project states: `greenfield`, `brownfield`, `recovery`;
- delivery modes: `software-git`, `software-no-git`, `mixed-artifact`;
- profiles: `standard`, `autonomous`;
- backends: native Claude Code and native Codex;
- fixed provider bundle.

Add distinctions only when they change real behavior.

## Finding 3: YAML and Markdown are unsafe authoritative state

Human-readable files are appropriate views and exports, not a concurrent source of truth.

They do not safely provide:

- multi-record transactions;
- concurrent task claims;
- stale-writer rejection;
- crash recovery;
- schema migration;
- indexing;
- idempotent mutations.

### Correction

Use:

```text
.agent-project/
├── state.db
├── events.jsonl
├── config.yaml
├── views/
├── evidence/
├── handoffs/
└── exports/
```

Use SQLite in WAL mode as the operational store. Generate Markdown and YAML views.

## Finding 4: revision numbers alone are insufficient

Long-running and concurrent work also needs:

- project identity;
- workspace fingerprint;
- run and session IDs;
- task leases and expiry;
- transaction IDs;
- idempotency keys;
- stale-session handling;
- quarantine of late results.

### Correction

Every mutation should carry:

```yaml
run_id: RUN-0184
session_id: SES-0082
workspace_fingerprint: sha256:...
base_revision: 142
idempotency_key: ...
task_lease:
  task_id: TASK-0142
  owner: RUN-0184
  expires_at: ...
```

## Finding 5: capability labels can hide incompatible behavior

Two providers may both claim `implementation_planning` while producing materially incompatible artifacts.

### Correction

Provider contracts must define observable obligations:

- preconditions;
- required outputs;
- result schema;
- allowed writes;
- forbidden actions;
- evidence requirements;
- failure behavior.

Do not attempt to normalize hidden reasoning.

## Finding 6: skill availability does not imply orchestrator invocation rights

A visible skill may be:

- user-invoked only;
- model-invoked;
- native-tool invoked;
- prompt-adapted;
- runtime executed.

### Correction

Record invocation mode in the provider registry. Bind orchestration to reusable model-invoked capabilities where possible, not merely user-facing slash commands.

## Finding 7: full LLM smoke testing at every initialization is excessive

Calling every prompt skill against a fixture during project creation is:

- slow;
- costly;
- nondeterministic;
- context-consuming;
- prone to false negatives;
- potentially interactive.

### Correction

Separate:

- full provider fixture/evaluation tests in CI and certification;
- deterministic package, state, tool, and resolution checks at installation and project initialization;
- a bounded first-use canary only when invocation compatibility cannot otherwise be established.

## Finding 8: the skill cannot certify a broken installation of itself

If the skill is partially loaded or operating under conflicting instructions, it is not a reliable self-diagnostician.

### Correction

Provide an external deterministic command:

```bash
projectctl doctor
```

The skill invokes it, but users and CI can run it independently.

This package includes a preliminary `scripts/doctor.py` for package and provider-declaration checks; it is not yet the full future runtime doctor.

## Finding 9: missing trust boundary

Repositories, issues, handoffs, generated docs, and third-party skill text can contain instruction-like content.

### Required policy

- designate trusted instruction sources;
- treat project content as untrusted data;
- constrain write roots and command classes;
- control network and connector access;
- protect secrets and PII;
- require trusted approval provenance;
- never allow repository text to satisfy an approval gate.

## Finding 10: supply-chain metadata must be enforceable

Provider availability alone is insufficient.

Record:

- source repository;
- immutable revision;
- content hash;
- license;
- trust level;
- allowed tools;
- allowed write paths;
- contract version;
- certification date.

## Finding 11: licensing blocks careless bundling

The repository is mixed-license. The original gist's license remains unresolved in the current provenance record.

### Correction

- explicitly license the gist or document its owner and permission;
- keep the runtime and new architecture repository-owned original;
- retain notices for external derivatives;
- use direct dependencies instead of copying upstream skill text when practical;
- do not publicly redistribute the verbatim scaffold until its license is resolved.

## Finding 12: review tone is not review independence

The same model in the same context can perform an adversarial prompt and still share the implementer's framing.

### Independence levels

| Level | Meaning |
| --- | --- |
| 0 | Implementer self-check |
| 1 | Separate prompt in same context |
| 2 | Fresh subagent, same model |
| 3 | Fresh sealed-context session |
| 4 | Different model or harness |
| 5 | External deterministic or human validation |

Autonomous project closure should require at least Level 2 and preferably Level 3.

## Finding 13: project memory can amplify errors

Memory needs provenance and supersession.

Each item should record:

- type;
- source;
- evidence;
- confidence;
- scope;
- valid dates;
- last verification;
- superseded-by relationship.

## Finding 14: workspace drift invalidates planning

Before each sprint, compare current workspace state to the plan baseline.

Material drift should invalidate affected:

- repository maps;
- assumptions;
- plans;
- validation baselines;
- task leases.

## Finding 15: autonomy is a backend capability, not a label

A harness may support one response but not continuous looping, resumability, compaction hooks, retries, or subagents.

Record backend capabilities explicitly and do not promise an autonomous sprint when the environment cannot supervise one.

## Finding 16: observability is mandatory

Record:

- provider invocation;
- harness and model;
- task selection;
- state mutation;
- tool failure;
- validation attempt;
- retry;
- stop reason;
- workspace revision;
- duration and cost when available.

The system should always answer:

> Why did the run stop?

## Rejected designs

### One universal monolithic skill

Rejected because it mixes methodology, state, tools, providers, and harness branches.

### Wrap every underlying skill

Rejected because it creates unnecessary forks and drift.

### Make the Codex port canonical for all harnesses

Rejected because Codex-specific invocation and tool assumptions would leak into the core.

### Prompt-only state enforcement

Rejected for concurrency, crash recovery, and trust-sensitive invariants.

### Dynamic provider marketplace in the first release

Rejected as premature complexity and supply-chain risk.

### Mandatory Zenith runtime

Rejected initially because it would couple the proven workflow to an additional operational dependency before the shared state interface is stable.

## Final adversarial conclusion

Preserve the operating model. Replace its weakest implementation assumptions:

- prose state → transactional state;
- scattered names → pinned provider bindings;
- same-context verification → fresh review;
- implicit trust → policy engine;
- full cutover → shadow-mode migration;
- ambitious ecosystem → fixed first-release bundle.

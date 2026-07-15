# Reading guide

## Use this order for a complete review

1. **Scenario routing MVP** — `10-scenario-routing.md`
2. **Selected scenario contract** — one of the three `scenario-*.md` files
3. **Historical source** — `01-original-scaffold.md`
4. **Observed operating context and skill lineage** — `02-lineage-and-observed-context.md`
5. **Generalized lifecycle and project model** — `03-generalized-operating-model.md`
6. **Complete comparison with Zenith and RALPH** — `04-zenith-comparison.md`
7. **Adversarial review of the proposed system** — `05-adversarial-architecture-review.md`
8. **Selected architecture after adversarial correction** — `06-final-architecture.md`
9. **Instantiation QC and smoke-test policy** — `07-qc-and-smoke-testing.md`
10. **Implementation and migration sequence** — `08-implementation-roadmap.md`
11. **Source and licensing record** — `09-sources-and-provenance.md`

## Fast paths

### Initialize or execute a project

Read:

- `10-scenario-routing.md`
- the resolved scenario reference
- `03-generalized-operating-model.md`
- `07-qc-and-smoke-testing.md`

### Understand what changed from the original gist

Read:

- `01-original-scaffold.md`
- `02-lineage-and-observed-context.md`
- `03-generalized-operating-model.md`
- `10-scenario-routing.md`

### Decide whether this should use Zenith

Read:

- `04-zenith-comparison.md`
- `05-adversarial-architecture-review.md`
- `06-final-architecture.md`

### Implement the package

Read:

- `10-scenario-routing.md`
- `06-final-architecture.md`
- `07-qc-and-smoke-testing.md`
- `08-implementation-roadmap.md`
- `09-sources-and-provenance.md`

### Review provider and harness handling

Read:

- `10-scenario-routing.md`
- `02-lineage-and-observed-context.md`
- `06-final-architecture.md`
- `provider-bindings.json`
- `scenario-profiles.json`

## Terminology

- **Scaffold**: the original phase-oriented Claude Code operating prompt and its later structured variants.
- **Orchestrator**: the harness-facing skill that selects phases, capabilities, approvals, scenario policy, and stop behavior.
- **Scenario**: one exact supported harness/model pair plus its tested orchestration policy.
- **Runtime**: deterministic state, policy, validation, and transaction code; planned command name `projectctl`.
- **Provider**: a skill or implementation that supplies an observable capability such as debugging, planning, or review.
- **Harness**: Claude Code, Codex, Hermes, or another agent execution environment.
- **Project state**: backlog, memory, decisions, evidence, approvals, runs, leases, and current sprint status.
- **Sprint**: a bounded set of approved work that can continue autonomously until completion or a stop trigger.
- **Terminal review**: a fresh review against original requirements and actual outputs before completion is accepted.

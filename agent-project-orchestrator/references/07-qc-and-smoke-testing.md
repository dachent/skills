# QC and smoke-testing model

## Decision

Require both:

1. capability and environment preflight;
2. deterministic runtime/package smoke testing.

Do not hard-stop because every known skill is absent. Hard-stop when a capability required by the selected route is unavailable, incompatible, inaccessible, or fails validation and no approved tested fallback exists.

## Capability categories

### Required

Failure blocks the selected workflow.

Typical examples:

- project state management;
- repository/current-state mapping;
- verification planning;
- evidence traceability;
- terminal verification;
- required execution backend;
- destructive-action safeguards.

### Conditional

Required only when the selected project and profile need it.

Examples:

- failure autopsy;
- Git delivery;
- browser validation;
- parallel execution;
- Office application automation;
- external issue tracker synchronization.

### Optional

May improve quality or efficiency without affecting correctness.

Examples:

- additional design perspectives;
- polished handoff rendering;
- optional visualization;
- cost reporting.

## Preflight outcomes

| Result | Meaning | Behavior |
| --- | --- | --- |
| `READY` | Required graph resolved and validated | Continue |
| `READY_WITH_DEGRADATION` | Only permitted optional or substitutable capabilities are absent | Continue and disclose |
| `BLOCKED_MISSING_CAPABILITY` | No provider for required capability | Hard stop |
| `BLOCKED_INCOMPATIBLE_PROVIDER` | Version or contract mismatch | Hard stop |
| `BLOCKED_PROVIDER_INACCESSIBLE` | Declared provider cannot be loaded or invoked | Hard stop |
| `BLOCKED_TOOLING` | Required tool, permission, or backend missing | Hard stop or choose another profile |
| `BLOCKED_SMOKE_TEST` | Deterministic test failed | Hard stop |
| `BLOCKED_STATE_RUNTIME` | State cannot be safely read or written | Hard stop |
| `BLOCKED_POLICY` | Trust or permission policy cannot be satisfied | Hard stop |

## Validation boundaries

### Build and CI

Run the broadest suite:

- package structure;
- schemas;
- provider manifests;
- source hashes and licenses;
- adapter tests;
- provider fixture invocations;
- side-effect checks;
- repeated stochastic evaluations where useful;
- Claude/Codex conformance fixtures;
- migration tests;
- security and prompt-injection tests.

### Installation

Run deterministic checks:

- files and checksums;
- runtime imports;
- schemas and migrations;
- provider declarations;
- executable and tool presence;
- harness compatibility;
- license and notice inventory;
- policy configuration.

### Project initialization

Run:

- project identity creation;
- filesystem permission test;
- state create/read/update/reload transaction;
- event-log write and replay test;
- provider-resolution check;
- selected tool checks;
- execution-backend capability check;
- route-specific hard-stop evaluation.

Do not automatically invoke every prompt provider.

### Session resume

Run a lightweight check:

- state integrity;
- migration status;
- incomplete transaction recovery;
- active sprint consistency;
- stale leases;
- workspace identity and drift;
- provider lock drift;
- changed permissions.

### Sprint preflight

Before every autonomous sprint verify:

- contract and approval are current;
- selected tasks are ready;
- dependencies are satisfied;
- workspace matches planning baseline;
- providers and tools remain accessible;
- validation environment works;
- no stale or conflicting lease exists;
- execution backend supports the promised mode.

### Completion preflight

Before claiming completion verify:

- all acceptance criteria are covered;
- evidence is current and tied to the active workspace revision;
- no blocking finding remains;
- fresh terminal reviewer is available;
- rollback or recovery conditions are met;
- final outputs are accessible and usable.

## Correct smoke-test scope

### Deterministic core smoke test

Use a temporary project to:

1. create state;
2. add a task;
3. claim the task;
4. add a decision and memory item;
5. register evidence;
6. transition task state;
7. generate a handoff view;
8. validate traceability;
9. close and reload the database;
10. replay or verify the event log;
11. remove the fixture.

### Provider static validation

For simple prompt providers validate:

- entrypoint exists;
- metadata is valid;
- references resolve;
- declared contract matches;
- harness-specific prohibited tool names are absent;
- invocation mode is allowed.

### Provider fixture testing

Run in CI or certification for critical reasoning providers:

- mapping;
- debugging;
- planning;
- verification planning;
- adversarial review;
- terminal review.

Validate observable outputs and side effects rather than prose style.

### Environment integration tests

Use for providers that depend on:

- Git;
- browsers;
- Office desktop applications;
- subagents;
- connectors;
- external services.

Use harmless read or sandboxed operations. Do not push, migrate, or modify production state.

## First-use canary

Run a bounded provider canary only when:

- the current harness/provider fingerprint has not been certified;
- static checks cannot prove invocation compatibility;
- later failure would be materially expensive;
- the canary can be non-destructive and bounded.

Cache the result by:

```text
harness version
+ orchestrator version
+ provider source hash
+ adapter version
+ contract version
+ relevant tool configuration
```

Rerun when any component changes or an unexpected provider failure occurs.

## Controlled degradation

A degradation is acceptable only when:

- it does not affect correctness or safety;
- a tested alternate mode exists;
- the requested result remains materially satisfied;
- the effect is disclosed and recorded.

Example:

```yaml
requested_profile: autonomous
resolved_profile: autonomous-serial
degradation:
  capability: parallel_execution
  reason: multi-agent support unavailable
  effect: ready tasks execute serially
```

Do not degrade terminal verification, state integrity, evidence traceability, or approval enforcement.

## Hard-stop rule

Hard-stop when the missing or failed capability affects:

- correctness;
- state integrity;
- safety;
- evidence;
- required review independence;
- explicit user promise;
- irreversible action control;
- approval provenance.

## Current package doctor

`scripts/doctor.py` is a preliminary package-level check. It validates:

- required package files;
- SKILL.md frontmatter;
- reference links;
- provider binding structure;
- duplicate capability declarations;
- optional discovery of provider entrypoints under supplied skill roots;
- strict failure when no declared provider for a required capability is found.

It does not implement or certify the future SQLite runtime, state transactions, execution backend, or terminal review.

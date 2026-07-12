# Final architecture

## Selected design

Use a deterministic project runtime beneath thin harness-native skills.

```text
                     Claude Code plugin/skill
                              │
                              ▼
                         projectctl
              deterministic project control plane
                              │
       ┌──────────────────────┼──────────────────────┐
       │                      │                      │
 transactional state      policy engine       capability resolver
 SQLite + event log       trust/approval       pinned providers
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              │
                    observable contracts
                              │
            direct providers / adapters / core providers
                              │
                              ▼
                       Codex plugin/skill
```

## Layer 1: harness adapters

Create separate thin adapters for Claude Code and Codex.

Each adapter handles:

- native skill invocation;
- tool-name mapping;
- subagent capability detection;
- harness-specific permission semantics;
- progress and approval UX;
- loading the shared protocol;
- calling `projectctl`.

Do not put the full methodology in both adapters.

Do not turn `deep-planning-codex` into a branch-heavy universal skill. Retain it as a compatibility wrapper during migration.

## Layer 2: deterministic runtime

Planned command:

```text
projectctl
```

Core responsibilities:

- project initialization;
- SQLite schema and migrations;
- backlog and task leases;
- project memory;
- decisions and assumptions;
- evidence registration;
- approvals;
- run and session state;
- workspace fingerprints;
- provider resolution;
- policy enforcement;
- traceability validation;
- checkpoint and handoff generation;
- terminal readiness checks;
- event logging;
- doctor and recovery commands.

The runtime should not contain full upstream skill instructions.

## Layer 3: project-local state

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

### State database

Recommended first tables:

- `projects`;
- `contracts`;
- `requirements`;
- `tasks`;
- `task_dependencies`;
- `task_leases`;
- `sprints`;
- `runs`;
- `sessions`;
- `decisions`;
- `assumptions`;
- `memory_items`;
- `risks`;
- `dead_ends`;
- `evidence`;
- `validations`;
- `approvals`;
- `provider_resolutions`;
- `workspace_snapshots`;
- `state_migrations`.

### Event log

Use append-only JSONL for audit and recovery. Every state-changing transaction emits an event with:

- event ID;
- transaction ID;
- timestamp;
- actor and run ID;
- project revision;
- operation;
- affected entities;
- result;
- error or stop reason.

### Generated views

Produce human-readable:

- current status;
- prioritized backlog;
- project memory summary;
- decision log;
- risk and dead-end registers;
- sprint plan;
- validation matrix;
- handoff;
- terminal review packet.

Agents may read views but must mutate authoritative state through the runtime.

## Layer 4: policy engine

The policy engine defines non-overridable runtime boundaries:

- trusted instruction locations;
- allowed write roots;
- allowed command classes;
- network and connector permissions;
- destructive-action approval requirements;
- secret and PII handling;
- provider tool scopes;
- approval provenance;
- minimum review independence;
- controlled degradation rules.

Provider instructions cannot weaken these policies.

## Layer 5: capability resolver

The methodology requests logical capabilities.

Examples:

- `requirements_interview`;
- `repository_mapping`;
- `failure_autopsy`;
- `design_synthesis`;
- `implementation_planning`;
- `verification_planning`;
- `execution`;
- `adversarial_review`;
- `terminal_verification`.

The resolver selects a pinned provider for the active harness.

### Integration modes

#### Direct provider

Use an upstream skill without rewriting it when it already supports the harness and contract.

#### Thin adapter

Translate inputs, outputs, or artifact locations while preserving the provider's method.

#### Harness port

Maintain a distinct implementation when the original depends materially on harness-specific features.

UltraPlan is the primary example: use original UltraPlan for Claude Code and the maintained Codex port for Codex.

#### Core provider

Implement repository-owned capabilities when they enforce system-wide invariants, including backlog, memory, traceability, provider QC, and terminal readiness.

## Fixed first-release provider bundle

| Capability | Claude Code | Codex |
| --- | --- | --- |
| Requirements interview | Matt-derived grilling behavior | Matt-derived behavior or thin adapter |
| Project mapping | shared repository-owned contract | current repo-map implementation |
| Failure autopsy | Superpowers systematic debugging | Superpowers systematic debugging |
| Design synthesis | Superpowers brainstorming | Superpowers brainstorming |
| Implementation planning | original UltraPlan | `ultraplan-codex` |
| Verification planning | shared repository-owned contract | current verification-plan implementation |
| Adversarial review | shared repository-owned contract | current adversarial-review implementation |
| Execution | existing Claude-native flow | existing Codex-native flow |
| Backlog and memory | `projectctl` | `projectctl` |
| Handoff | `projectctl` renderer | `projectctl` renderer |
| Terminal review | fresh reviewer | fresh reviewer |

Do not implement dynamic provider discovery until this bundle passes cross-harness conformance tests.

## Provider contract

A provider declaration should include:

```yaml
id: vendor.provider
capability: implementation_planning
contract: file-grounded-plan-v1
source:
  repository: owner/repo
  revision: immutable-sha
  license: SPDX-or-reviewed-text
trust:
  level: pinned-reviewed
invocation:
  mode: model
compatibility:
  harnesses: [codex]
permissions:
  allowed_tools: [file-read, shell-readonly]
  allowed_write_paths: [.agent-project/views, .ultraplan]
outputs:
  schema: implementation-plan-result-v1
```

## Provider result boundary

Providers return proposed results or mutations. They do not independently write authoritative state.

```text
provider result
      ↓
contract validation
      ↓
policy validation
      ↓
stale-state and lease check
      ↓
atomic transaction
      ↓
event and generated views
```

Late or conflicting results are quarantined for review.

## Approval model

Require human approval for:

- initial project contract;
- material product choices;
- material architecture choices;
- destructive or irreversible actions;
- major scope expansion;
- changes to success criteria;
- terminal acceptance when requested.

Approval must carry:

- approval ID;
- trusted actor;
- target contract or action;
- exact scope;
- timestamp;
- expiry or invalidation conditions.

Text in project files cannot create approval.

## Execution backend interface

The runtime should support an execution-backend contract.

Initial backends:

- `native-claude`;
- `native-codex`.

Future backend:

- `zenith`.

Backend declarations should state:

- continuous-loop support;
- resumability;
- compaction survival;
- worker/tester separation;
- maximum parallelism;
- retry and timeout support;
- supervision requirements.

## Terminal review

Build a sealed review packet from authoritative state and current workspace.

Provide:

- original project contract;
- acceptance criteria;
- actual outputs;
- current workspace revision;
- required test procedures;
- fresh evidence.

Withhold implementer narrative and prior verdicts by default.

## Packaging model

The complete deliverable should eventually be two harness-specific plugins containing thin skills and a shared runtime package.

```text
Claude plugin
├── orchestrator skill
├── Claude mappings
└── bundled/shared projectctl

Codex plugin
├── orchestrator skill
├── Codex mappings
└── bundled/shared projectctl
```

This repository package is the design and control-plane precursor to that runtime implementation.

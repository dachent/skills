# Generalized operating model

## Objective

Move a project from a verified current state to an explicit target state through prioritized, independently validated increments.

Maintain enough durable state that a fresh human or agent can understand, review, continue, or reverse the work without reconstructing the entire conversation.

## Core lifecycle

1. Establish operating context.
2. Classify the project and requested delivery mode.
3. Initialize or reconcile project state.
4. Establish the verified current state.
5. Define the target state and success contract.
6. Calculate the delta between current and target state.
7. Investigate material uncertainty and prior failures.
8. Create and prioritize the backlog.
9. Select and approve a bounded sprint.
10. Execute autonomously while sprint conditions remain valid.
11. Validate completed work independently where practical.
12. Reconcile backlog, memory, evidence, decisions, and risks.
13. Continue, replan, escalate, recover, or stop.
14. Perform a fresh terminal review before declaring project completion.

## Classification axes

Use two independent axes.

### Project-state mode

| Mode | Meaning | Initial emphasis |
| --- | --- | --- |
| `greenfield` | No meaningful existing implementation | requirements, feasibility, architecture |
| `brownfield-stable` | Working project receiving planned changes | baseline, delta, regression protection |
| `brownfield-degraded` | Existing project has defects or inconsistent behavior | reproduction, failure corpus, root cause |
| `recovery` | Previous work failed, stalled, or diverged | state reconstruction, salvage, dead ends |
| `continuation` | Resume prior human or agent work | stale assumptions, state reconciliation |
| `audit-only` | Review without implementation | evidence, findings, recommendations |
| `migration` | Move platform, framework, or format | parity contract, cutover, rollback |

The first implementation may collapse these to `greenfield`, `brownfield`, and `recovery`, but the full model preserves the distinctions.

### Delivery mode

| Mode | Examples |
| --- | --- |
| `software-git` | Application or library with branch/commit/PR workflow |
| `software-no-git` | Local code without allowed version-control delivery |
| `business-artifact` | Report, policy, model, deck, operating document |
| `research-analysis` | Evidence synthesis, experimentation, technical research |
| `operational-workflow` | Automation, integration, repeatable process |
| `mixed` | Code plus business artifacts or operations |

The first implementation may combine the non-code modes as `mixed-artifact`.

## Workflow profiles

| Profile | Use |
| --- | --- |
| `standard` | Normal planning, implementation, and review |
| `autonomous` | Multi-hour execution against a bounded approved sprint |
| `quick` | Future optional low-risk profile |
| `forensic` | Future optional high-uncertainty or failed-project profile |
| `regulated` | Future optional formal evidence and approval profile |

Do not add profiles until they change real operating behavior.

## Project contract

The project contract defines:

- objective;
- users and stakeholders;
- desired outcomes;
- acceptance criteria;
- failure criteria;
- non-goals;
- constraints;
- quality requirements;
- risk tolerance;
- rollback or recovery requirements;
- decisions reserved for the human owner;
- evidence required for completion.

The contract is the reference for terminal review. It must not be silently rewritten during execution.

## Current-state reconstruction

For existing projects, map:

- relevant files and artifacts;
- architecture and operating patterns;
- inputs and outputs;
- tests and validation commands;
- dependencies and external systems;
- prior attempts and partial results;
- known failures and their evidence;
- open issues and constraints;
- existing decisions and terminology.

Separate:

- verified facts;
- user directives;
- model inferences;
- assumptions;
- unknowns.

## Failure autopsy and Dead Ends Registry

When prior failures exist:

1. reproduce or characterize the failure;
2. trace root cause rather than patch symptoms;
3. identify decision points where the work diverged;
4. preserve partial accomplishments;
5. record approaches that should not be repeated;
6. attach evidence and conditions under which a dead end might become valid again.

A dead end is not an eternal prohibition. Record its scope, evidence, and expiry conditions.

## Targeted probes

Use the smallest test that can remove material uncertainty.

A probe should define:

- assumption being tested;
- expected observation;
- allowed side effects;
- cost and time budget;
- pass/fail interpretation;
- resulting backlog or design mutation.

Do not implement broad features merely to answer a narrow feasibility question.

## Backlog model

Every actionable item belongs in one authoritative backlog.

Each task should include:

- stable ID;
- title and intended outcome;
- human priority class;
- agent-calculated ordering score when useful;
- status;
- dependencies;
- acceptance criteria;
- validation method;
- risks;
- evidence references;
- parent workstream or initiative;
- active sprint and task lease when applicable.

### Recommended statuses

```text
candidate
triaged
ready
in_progress
blocked
implementation_complete
validation_failed
needs_review
done
rejected
superseded
```

Keep `implementation_complete` distinct from `done`.

### Prioritization order

1. blocking dependencies;
2. risk reduction;
3. information gain;
4. user value;
5. architectural sequence;
6. reversibility;
7. execution efficiency.

Agents may reorder within human priority classes but must not silently override explicit human priorities.

## Project memory

Separate memory into four types.

### User directives

Authoritative product, scope, and operating instructions provided by the human owner.

### Verified project knowledge

Facts supported by code, tests, documentation, or external evidence.

### Decisions

Accepted architectural, product, process, and scope choices, including rejected alternatives and supersession history.

### Episodic history

Sprint summaries, failures, discoveries, and resume information.

Each memory item should record source, evidence, confidence, scope, date, and supersession status. A model inference must not silently become a verified project fact.

## Sprint contract

A sprint is a first-class bounded object.

It defines:

- sprint objective;
- included task IDs;
- explicitly excluded adjacent work;
- execution sequence or parallel workstreams;
- required outputs;
- validation requirements;
- task and validation-cycle budgets;
- stop triggers;
- decisions reserved for human review;
- approval provenance.

### Autonomous continuation

Continue without interruption while:

- work remains within the approved contract;
- selected tasks remain ready and unblocked;
- required tools and providers remain available;
- validation is passing or progressing within the allowed retry policy;
- risk limits are not exceeded;
- no product or architecture decision is required;
- workspace drift has not invalidated the plan.

### Immediate stop triggers

Stop and create a checkpoint when:

- a foundational assumption fails;
- repeated validation exposes an architectural problem;
- the workspace materially diverges from the planned baseline;
- an irreversible or destructive action is reached;
- a required provider or tool becomes unavailable;
- scope or success criteria would need to change;
- correctness cannot be demonstrated;
- a human product or architecture decision is required.

## Validation

Map every acceptance criterion to:

```text
requirement
→ backlog task
→ implementation output
→ validation procedure
→ evidence
→ verdict
```

Validation records should include:

- method;
- environment;
- command or procedure;
- expected result;
- observed result;
- evidence location;
- freshness and workspace revision;
- limitations;
- reviewer identity and independence level.

## Sprint reconciliation

At sprint end:

- update task statuses;
- attach evidence;
- record decisions and changed assumptions;
- update project memory;
- record new risks and dead ends;
- compare actual outcome with sprint objective;
- add discovered work to the backlog;
- identify divergence;
- decide whether to continue, replan, recover, escalate, or stop;
- generate a concise handoff from authoritative state.

## Terminal review

Completion requires a fresh review against:

- the original project contract;
- actual workspace and deliverables;
- acceptance criteria;
- required validation commands;
- current evidence.

Do not rely only on:

- completed backlog status;
- implementer claims;
- sprint summaries;
- prior PASS statements;
- the implementation plan.

For autonomous projects, use at least a fresh subagent review and preferably a fresh sealed-context session.

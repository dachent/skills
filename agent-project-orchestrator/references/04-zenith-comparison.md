# Complete comparison with Zenith

## Scope

This document preserves the complete conceptual comparison developed between:

1. the original and evolved deep-planning scaffold;
2. the Codex ports and supporting skills;
3. RALPH-style repeated-gap loops;
4. Zenith's continuous-improvement harness.

It distinguishes published Zenith claims from observations about the existing scaffold.

## Executive conclusion

The scaffold and Zenith solve overlapping but different layers of the problem.

- The **scaffold** is a proven human-agent project operating model. It excels at intent alignment, forensic reconstruction, architecture decisions, durable handoffs, explicit human boundaries, and high-quality bounded execution.
- **Zenith** is a more agent-native execution harness. It excels at repeated state inspection, dynamic worker/tester allocation, replanning, independent verification, runtime state, and stopping discipline across long missions.

The strongest design is not to replace the scaffold with Zenith or embed Zenith immediately. It is:

```text
human-agent project contract and adaptive deep planning
        ↓
transactional project state and approved sprint contract
        ↓
selected execution backend
        ├── native Claude/Codex sprint execution
        └── optional Zenith backend later
        ↓
fresh terminal review and durable learning
```

## What Zenith is

Zenith describes itself as a continuous-improvement harness for long-running tasks that may run for days or weeks. A single orchestrator session reads task state on each turn and decides whether to:

- spawn workers;
- spawn testers;
- register reusable skills;
- replan;
- continue;
- stop.

Workers and testers operate in separate contexts and report back to the orchestrator.

Zenith supports agent providers such as Claude Code, Codex, and Hermes through MCP/ACP adapters.

At the reviewed source revision, the repository states that the dominant failure mode addressed is premature completion rather than inability to make progress.

## Zenith's stated control mechanisms

The Zenith technical framing emphasizes:

1. repeated gap finding;
2. revisable planning;
3. independent verification;
4. adaptive orchestration;
5. stopping discipline.

These mechanisms should be evaluated separately from the implementation or benchmark claims.

## RALPH and Zenith

### RALPH's strength

RALPH is a strong simple baseline because each new loop or session reopens the gap between:

- original requirement;
- current project state;
- remaining work.

This repeated reopening helps prevent premature success claims.

### RALPH's weakness

A simple RALPH loop is expensive and underspecified:

- it may repeat broad investigation;
- it lacks a principled task graph;
- it lacks a strong stopping rule;
- it may not allocate independent testers;
- it can lose useful intermediate structure;
- it may re-derive knowledge instead of preserving reusable state.

### Why Zenith is an upgrade over RALPH

Zenith preserves repeated gap detection while adding:

- persisted runtime state;
- explicit contracts;
- task graphs;
- validators and gates;
- dynamic worker/tester allocation;
- replanning and attention queues;
- explicit stopping decisions;
- terminal review separated from mission history.

Therefore, Zenith is best understood as an evolution of the useful RALPH mechanism rather than a completely unrelated methodology.

## Published Zenith evidence

The reviewed Zenith README reports an eight-task ablation:

| Method | Mean rank | Mean cost per task | Wins |
| --- | ---: | ---: | ---: |
| One-session | 5.00 | $22.21 | 0 |
| Plan-RALPH | 4.00 | $161.53 | 0 |
| Milestone-RALPH | 2.88 | $209.47 | 0 |
| RALPH | 1.75 | $407.58 | 3 |
| Zenith | 1.38 | $175.68 | 5 |

The repository characterizes Zenith as achieving the best mean rank at less than half of RALPH's per-task cost in that study.

These results are **author-reported and task-set-specific**. They support the plausibility of the control mechanisms. They do not prove that Zenith will outperform every scaffold, model, repository, or product-development workflow.

The comparison should not treat benchmark rankings as a substitute for direct evaluation on this user's projects.

## What the original scaffold does better

### 1. Human intent formation

The scaffold begins with explicit success criteria, failure criteria, scope boundaries, and user grilling.

Zenith assumes a mission contract but is not primarily a product-discovery method. It can execute and revise against a mission, but the quality of product intent remains dependent on the supplied mission.

### 2. Failure-corpus reconstruction

The scaffold explicitly catalogs prior attempts, outcomes, failure mechanisms, partial accomplishments, and dead ends before selecting a new path.

This is stronger than a generic repeated-gap loop when the project has a complex history of failed attempts.

### 3. Product-owner and architect boundaries

The scaffold places humans at meaningful decision points:

- criteria and scope;
- architecture selection;
- path approval;
- execution approval;
- terminal acceptance.

This is appropriate when several solutions are technically valid but business consequences differ.

### 4. Natural handoff points

Repeated handoffs make context boundaries explicit and provide opportunities to detect:

- planning drift;
- unrecorded assumptions;
- incomplete execution;
- false continuity between sessions.

The reported practical results indicate these stopping points have been useful rather than merely bureaucratic.

### 5. Rich project-specific reasoning

The scaffold's combination of grilling, systematic debugging, targeted probes, brainstorming, UltraPlan, and final execution planning creates a high-resolution path before implementation.

Zenith is more focused on continuous execution control after a mission is defined.

## What Zenith does better

### 1. Adaptive routing during execution

The scaffold is comparatively phase-oriented. Zenith evaluates state repeatedly and selects the next control action dynamically.

### 2. Runtime state as a first-class system

Zenith treats contracts, task state, validators, and orchestration state as executable runtime concepts rather than only documents.

### 3. Separation of worker and tester contexts

A tester with a fresh context is less exposed to implementer framing and sunk-cost bias.

### 4. Stopping discipline

Zenith directly addresses the question:

> Is the mission truly complete, or has the agent merely stopped finding work?

The scaffold has strong verification phases, but its stopping logic is less formally encoded.

### 5. Dynamic allocation

Zenith can decide whether the next best action is implementation, testing, replanning, or skill creation. The original scaffold determines more of that sequence in advance.

### 6. Long-horizon supervision

Zenith is explicitly designed as a harness for work that may extend across many cycles, sessions, and contexts.

## Full comparison matrix

| Dimension | Evolved scaffold | Zenith |
| --- | --- | --- |
| Primary abstraction | Human-agent project/sprint operating model | Continuous-improvement execution harness |
| Product intent | Strong interactive formation | Consumes a mission contract |
| Human role | Product owner and architect | Executive sponsor and mission owner; operational control shifts inward |
| Planning | Deep, staged, evidence-heavy | Revisable and state-driven |
| Prior failure analysis | Explicit failure corpus and Dead Ends Registry | Can investigate through task flow but not the defining feature |
| Backlog | Present in evolved practice; needs formal runtime | Task graph and persisted runtime state |
| Project memory | Strong in evolved practice; currently artifact-oriented | Runtime state and registered reusable knowledge |
| Execution allocation | Chosen after planning; can use subagents or batches | Dynamically chooses workers, testers, replanning, or stopping |
| Verification | Explicit verification planning and final verification | Independent testers and validators are core |
| Stopping | Human gates plus verification | Explicit repeated stop decision |
| Handoffs | Major strength | State persistence reduces dependence on manual handoffs |
| Harness portability | Claude origin plus Codex ports | Designed for multiple providers through adapters |
| Runtime enforcement | Limited; largely instructions and validators | Stronger harness-level control |
| Best use | High-stakes product and architecture work requiring human decisions | Long-running execution where premature completion is the main risk |
| Main risk | Process rigidity and prose-state inconsistency | Mission quality, harness complexity, and operational dependency |

## Does the additional context materially change the assessment?

Yes.

Without usage evidence, the scaffold could be criticized as:

- overly linear;
- artifact-heavy;
- gate-heavy;
- dependent on named skills;
- weaker than a formal runtime.

The reported behavior demonstrates that several apparent costs are functional controls:

- gates create effective product and architecture boundaries;
- handoffs catch divergence;
- persistent planning artifacts survive long sessions;
- backlog and project memory support multi-week continuity;
- the system can sustain substantial autonomous execution.

The correct criticism is therefore not that the scaffold fails as an operating model. The criticism is that its successful operating model should be implemented with stronger state, provider, trust, and runtime guarantees.

## Does Zenith better reflect LLM-agent-first development?

Zenith is more agent-native in its execution-control model.

It internalizes more functions normally associated with:

- technical lead;
- project manager;
- QA coordinator;
- scheduler;
- continuous reviewer.

The scaffold remains more deliberately human-governed at product and architecture boundaries.

Neither is universally superior. The appropriate division is:

- humans own goals, values, priority, and material tradeoffs;
- the orchestrator owns state reconstruction, sequencing, monitoring, and escalation within the contract;
- specialized agents implement and validate;
- a fresh reviewer determines whether completion is evidenced.

## Is Zenith an upgrade over the scaffold?

Not as a complete replacement.

Zenith is an upgrade in:

- adaptive execution control;
- stateful replanning;
- worker/tester separation;
- stopping discipline;
- runtime enforcement.

The scaffold is stronger in:

- project inception and success-contract formation;
- forensic recovery;
- product-owner interaction;
- explicit architecture selection;
- durable human-readable handoffs;
- demonstrated fit with the user's working style.

The proper design is to borrow Zenith's runtime principles underneath the scaffold's project-contract and sprint model.

## Is Zenith an upgrade over RALPH?

Architecturally, yes.

It retains repeated gap review while reducing repeated undirected investigation and adding task state, validation, allocation, and stopping controls.

Empirically, the authors' eight-task ablation supports this claim for the tested tasks. It is not universal proof.

## How long can Zenith run autonomously?

Separate three claims.

### Architectural intent

Zenith is explicitly intended for tasks that may run for days or weeks.

### Published demonstration

The reviewed public materials describe long-horizon benchmarks and architecture, but they do not establish a universal unattended-duration guarantee for arbitrary repositories.

### Practical expectation

A correctly configured harness could plausibly supervise:

- multi-hour runs;
- overnight or day-scale missions;
- multi-day work with resumable state;
- longer projects with periodic human product decisions.

The limiting factors become:

- changing requirements;
- workspace and dependency drift;
- compounding implementation errors;
- merge conflicts;
- tool or provider failures;
- weak mission contracts;
- external service changes;
- unresolved human tradeoffs.

Do not promise a duration merely because the architecture supports repeated cycles.

## Are named skills fragile?

### In a controlled environment

No. Named skills can improve:

- determinism;
- version control;
- specialization;
- discoverability;
- auditability;
- repeatability.

The user's maintained environment makes named dependencies a strength.

### Across environments

Direct names become brittle when:

- a provider renames a skill;
- Claude and Codex expose different invocation surfaces;
- one skill is user-only and another is model-invoked;
- versions drift;
- a package is absent;
- a tool contract changes.

### Correct implementation

Preserve concrete names in provider configuration, but have the methodology request logical capabilities:

```text
repository_mapping
failure_autopsy
implementation_planning
verification_planning
adversarial_review
```

A harness adapter resolves the logical capability to the pinned provider.

The problem is not named skills. The problem is scattering provider names through the methodology without a registry, version lock, invocation-mode declaration, and preflight.

## What to borrow from Zenith

Adopt:

- repeated current-state versus target-state comparison;
- revisable plans;
- explicit task graph and contracts;
- independent worker and tester contexts;
- attention and replanning triggers;
- formal stop reasons;
- history-blind terminal review;
- runtime event logging;
- persistent state across sessions.

## What not to adopt immediately

Defer:

- making Zenith a mandatory runtime dependency;
- replacing the existing proven scaffold in one cutover;
- dynamic provider marketplace behavior;
- unrestricted multi-agent concurrency;
- external issue trackers as co-equal state stores;
- automatic product or architecture decisions that should remain human-owned.

## Recommended hybrid

### Planning and contract layer

Use the generalized scaffold to:

- establish current state;
- define target state;
- reconstruct failures;
- resolve product and architecture decisions;
- create the prioritized backlog;
- approve a bounded sprint.

### Runtime layer

Use a deterministic state runtime to:

- store backlog and memory transactionally;
- enforce task leases and approvals;
- resolve providers;
- detect workspace drift;
- record evidence;
- select the execution backend;
- expose stop reasons.

### Execution backend

Initially support harness-native Claude Code and Codex execution with fixed providers.

Later expose Zenith as an optional backend when:

- the mission contract is stable;
- the provider and tool environment passes QC;
- long autonomous execution is valuable;
- the project can tolerate the additional runtime dependency.

### Closure

Use a fresh terminal reviewer that receives:

- original contract;
- actual deliverables and workspace;
- acceptance criteria;
- required test procedures;

but not the implementer's narrative or prior success claims unless necessary to reproduce a failure.

## Final comparative judgment

The evolved scaffold is a demonstrated human-agent development operating system.

Zenith is a stronger agent-native continuous execution and stopping harness.

The generalized package should preserve the scaffold's human governance, forensic depth, backlog discipline, project memory, and handoffs, while adopting Zenith-like runtime state, adaptive replanning, independent verification, and stopping discipline through a separate deterministic control plane.

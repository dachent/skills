# Lineage and observed operating context

## Why the initial assessment changed

A surface reading of the original gist can make it look like a large planning prompt with many mandatory gates. That interpretation is incomplete.

The actual system consists of:

- a top-level Claude Code scaffold;
- specialized upstream skills used as implementation components;
- Codex ports that preserve the same methodology under Codex conventions;
- a maintained prioritized backlog and task-state model;
- durable project-specific memory;
- state and handoff artifacts that allow a fresh session to resume accurately;
- human product-owner and architect decisions at meaningful boundaries;
- autonomous execution inside approved work packages.

In practice, the system has reportedly supported:

- multi-week project work;
- four-to-six-hour autonomous execution intervals;
- limited human steering during approved sprints;
- natural stop points that surface divergence rather than concealing it;
- handoffs that expose gaps between planning and implementation;
- product outcomes described as high quality and closely aligned with intent.

This empirical context changes the proper unit of analysis. The system is not merely a prompt. It is a **human-agent project operating model**.

## Source and harness lineage

The current planning ecosystem draws from several sources.

### User-owned scaffold

The original gist defines the phase sequence and the combination of grilling, failure autopsy, probes, design, UltraPlan, execution planning, state setup, subagent execution, verification, and handoff.

### Matt Pocock skills

These contribute reusable interview and handoff disciplines, including:

- grilling a user through unresolved decisions;
- grounding questions in repository documents and terminology;
- compacting a session into a continuation artifact.

The original user-facing command and the reusable underlying model-invoked behavior are not necessarily the same invocation surface. The generalized system must record invocation mode rather than assuming every visible skill can be called programmatically.

### UltraPlan

UltraPlan contributes deep, repository-grounded implementation planning. The original implementation is Claude-oriented. `ultraplan-codex` is a substantial Codex adaptation rather than an unrelated alternative.

### Superpowers

Superpowers contributes process disciplines such as:

- brainstorming;
- systematic debugging;
- writing plans;
- executing plans;
- parallel or subagent-driven development;
- code review;
- verification before completion.

Superpowers is already designed for multiple harnesses, but installation and tool mapping remain harness-specific.

### Current Codex ports

The repository includes:

- `deep-planning-codex`;
- `repo-map-codex`;
- `verification-plan-codex`;
- `adversarial-plan-review-codex`;
- `ultraplan-codex`;
- `grill-me-codex`;
- `grill-with-docs-codex`;
- `handoff-codex`.

These are not conceptually separate project methodologies. They are Codex implementations or extracted components of the same broader operating model.

## Correct abstraction

The generalized system should be understood as:

```text
Human product owner / architect
        ↓
Project contract and approval boundaries
        ↓
Adaptive project and sprint orchestrator
        ↓
Prioritized backlog + durable project memory
        ↓
Harness-native capability providers
        ↓
Execution, validation, reconciliation, handoff
```

The team-sprint analogy is accurate:

- the human owns business intent, priorities, and material tradeoffs;
- the agent system reconstructs current state and proposes a target path;
- a sprint contract defines a bounded autonomous interval;
- specialized agents or skills implement and review;
- sprint reconciliation functions as review and retrospective;
- the backlog and project memory survive context boundaries.

## Human-led versus agent-native development

The existing scaffold is primarily a **human-led agent development model**:

- humans retain product intent;
- humans approve architecture and scope boundaries;
- agents perform deep analysis and implementation;
- natural stopping points return control when judgment is needed.

Zenith represents a more **agent-native harness model**:

- the orchestrator internalizes more project-management, technical-lead, reviewer, and scheduling behavior;
- workers and testers receive separate contexts;
- the harness repeatedly decides whether to spawn work, test, replan, register knowledge, or stop.

This distinction should not be overstated. Zenith does not create business intent independently. The human remains the source of mission goals and priority. Zenith moves more operational control inside the harness.

## Updated assessment

Given the observed results, the original scaffold merits a higher assessment than a prompt-only review would suggest.

Its strongest properties are:

- durable state beyond a conversation;
- evidence-grounded failure analysis;
- explicit dead-end preservation;
- high-quality human decision boundaries;
- strong handoff discipline;
- successful long autonomous intervals;
- effective separation between planning and execution.

Its primary limitations are architectural rather than methodological:

- phase routing is more fixed than necessary;
- state remains too prose-oriented for safe concurrent writers;
- provider availability and versions are not formalized;
- harness differences are embedded in skill instructions;
- terminal review is not always independently isolated;
- approval and trust boundaries need explicit enforcement;
- the system lacks a deterministic runtime with transactional state.

The generalized package therefore preserves the operating model while changing its implementation structure.

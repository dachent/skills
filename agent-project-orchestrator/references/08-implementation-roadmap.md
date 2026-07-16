# Implementation and migration roadmap

## Principle

Do not replace the demonstrated scaffold in one cutover.

Introduce deterministic behavior in shadow mode, verify parity, then transfer authority incrementally.

## Status update: Stage 1 mirror-import rejected (issue #62)

A drafted Stage 1 implementation used a `mirror-import` command as its primary write path, parsing the gist
scaffold's Markdown output into the task/decision/evidence schema below. An adversarial review plus a spike
against real production scaffold artifacts found the premise false: real Phase-1 catalogs and Dead Ends
Registries are Markdown tables with per-project column sets, and handoffs are free prose under convention
headers — not a fixed, generically parseable grammar. See
`references/05-adversarial-architecture-review.md`'s "Generic mirror-import of scaffold Markdown into a
fixed schema" rejected-design entry and issue #62 for the full finding.

Stage 1 as described below has not been built. Any future attempt should design the state-capture mechanism
against real captured scaffold output first, not an assumed grammar.

## Stage 0: package and source hygiene

Complete before runtime implementation:

- resolve or explicitly restrict the original gist license;
- register all material dependencies, including Superpowers and Zenith analysis sources;
- pin immutable revisions;
- establish provider invocation modes;
- freeze MVP taxonomy and provider bundle;
- define security and approval policy;
- define terminal-review independence requirement.

Deliverable:

- this architecture package;
- reviewed source map;
- provider binding file;
- package doctor;
- approved implementation contract.

## Stage 1: shadow-state prototype

Keep the existing Claude Code workflow authoritative.

Build a minimal `projectctl` prototype that observes and mirrors:

- backlog;
- task statuses;
- decisions;
- assumptions;
- evidence;
- sprint events;
- handoff data.

Do not allow the prototype to block or direct work yet.

Compare generated state with existing planning and handoff artifacts.

Exit criteria:

- no meaningful state loss across several real sprints;
- generated views are more accurate or easier to resume from;
- migration and recovery are reliable;
- users can inspect state without a special UI.

## Stage 2: authoritative state on Claude Code

Make `projectctl` authoritative for:

- backlog;
- memory;
- decisions;
- evidence;
- sprint status;
- task leases;
- approvals;
- handoffs.

Keep existing Claude skills and methodology.

Claude adapter responsibilities:

- map skill invocation;
- read state and views;
- request approved mutations;
- detect backend capabilities;
- surface stop reasons.

Exit criteria:

- forced interruption and resume succeeds;
- stale mutations are rejected;
- workspace drift invalidates affected plans;
- approval provenance is enforced;
- current successful long-sprint behavior is not degraded.

## Stage 3: Codex adapter

Connect existing Codex planning ports to the same runtime.

Use fixed provider bindings.

Retain `deep-planning-codex` as a compatibility entrypoint, but delegate state and policy to `projectctl`.

Exit criteria:

- same project can be inspected and resumed from Claude or Codex;
- state transitions are equivalent;
- provider differences are explicit;
- prohibited actions and approval rules match;
- handoff and terminal review packets are compatible.

## Stage 4: cross-harness conformance

Create fixtures for:

- greenfield feature;
- stable brownfield enhancement;
- degraded project failure recovery;
- interrupted sprint;
- stale workspace;
- parallel task conflict;
- provider unavailable;
- validation failure;
- false completion claim;
- malicious repository instruction;
- destructive action awaiting approval.

Compare observable invariants, not wording:

- task transitions;
- evidence coverage;
- stop conditions;
- prohibited mutations;
- approval requirements;
- completion verdicts;
- resume state.

## Stage 5: provider certification and substitution

Only after fixed bindings work:

- formalize provider registry and lockfile;
- add provider contract tests;
- support alternate providers one capability at a time;
- maintain a certification matrix by harness and version;
- add drift detection and recertification triggers.

Do not add runtime provider discovery from arbitrary repositories.

## Stage 6: optional Zenith backend

Add Zenith through an execution-backend interface.

Prerequisites:

- stable mission and sprint contract;
- stable state adapter;
- backend capability declaration;
- provider/tool preflight;
- event and stop-reason integration;
- independent terminal-review compatibility;
- benchmark on representative user projects.

Evaluate Zenith against native execution on:

- completion quality;
- human interventions;
- false-completion rate;
- duration;
- cost;
- provider failures;
- rework;
- state consistency.

Do not assume public benchmark results transfer directly.

## Stage 7: external trackers and richer profiles

Add only after core reliability:

- GitHub Issues, Linear, or other trackers as selected backends;
- `quick`, `forensic`, or `regulated` profiles;
- richer dashboards;
- automated drift alerts;
- cost and performance telemetry.

Use one authoritative backlog backend. Other systems are mirrors or integrations, not co-equal truth stores.

## Recommended implementation order inside projectctl

1. project identity and config;
2. SQLite schema and migrations;
3. event log;
4. task and dependency model;
5. task leases and idempotent mutations;
6. memory, decisions, and assumptions;
7. evidence and validation;
8. approvals and policy engine;
9. workspace fingerprinting;
10. generated views and handoffs;
11. provider resolution;
12. doctor and recovery;
13. execution-backend interface;
14. terminal review packet.

## Initial non-goals

- general marketplace;
- arbitrary provider installation;
- automatic business-priority decisions;
- mandatory Zenith;
- broad external tracker support;
- comprehensive UI;
- identical prose across harnesses;
- replacing all existing planning skills.

## Success measures

Measure whether the new system improves:

- accurate resume after interruption;
- percentage of tasks with current evidence;
- false completion rate;
- unplanned human interventions;
- time spent reconstructing context;
- repeated dead ends;
- provider/environment failures discovered before execution;
- state conflicts;
- plan invalidation after workspace drift;
- quality of terminal acceptance.

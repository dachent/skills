# Agent Project Orchestrator

`agent-project-orchestrator` is an experimental architecture and control-plane skill for long-running human-agent projects.

It generalizes a proven Claude Code deep-planning scaffold into a project operating model with:

- explicit current-state and target-state contracts;
- prioritized backlog and task-state control;
- durable project memory and decision history;
- autonomous sprint boundaries and natural stopping conditions;
- capability/provider preflight and hard-stop rules;
- independent terminal verification;
- a staged path toward a deterministic `projectctl` runtime;
- explicit orchestration policies for three initial harness/model scenarios.

## Initial supported scenarios

| Scenario | Control style |
| --- | --- |
| `claude-code-opus-4.8` | Explicit, phase-bounded, comprehensive artifacts, higher gate density |
| `claude-code-sonnet-5` | Goal-bounded, task-batch or sprint execution, recorded optional skips |
| `codex-gpt-5.6-sol` | Lean outcome contract, adaptive capability use within an approved graph, lower gate density |

The project methodology remains shared. Scenario profiles change sequencing, continuation, delegation, gate density, repair budgets, state-update frequency, and artifact detail. They cannot weaken approval, evidence, trust, or terminal-verification invariants.

## Resolve a scenario

```bash
python scripts/resolve_scenario.py \
  --harness codex \
  --model "GPT-5.6 Sol" \
  --profile autonomous
```

The resolver hard-stops on unsupported harness/model pairs. It can also validate that capabilities selected by the shared project router have providers for the resolved harness.

## Why this package exists

The original scaffold was not merely a planning prompt. In use, it supported multi-week projects, substantial autonomous sprints, limited steering, strong handoffs, and effective divergence detection. The generalized design preserves that operating model while addressing cross-harness portability, provider drift, state integrity, security, and stronger runtime concepts.

The three-scenario MVP avoids premature dimensional abstraction. Shared behavior should be extracted only after common fixtures show that two or more scenarios have the same observable semantics.

## Reading order

1. [`references/00-reading-guide.md`](references/00-reading-guide.md)
2. [`references/10-scenario-routing.md`](references/10-scenario-routing.md)
3. The selected scenario reference
4. [`references/03-generalized-operating-model.md`](references/03-generalized-operating-model.md)
5. [`references/05-adversarial-architecture-review.md`](references/05-adversarial-architecture-review.md)
6. [`references/06-final-architecture.md`](references/06-final-architecture.md)
7. [`references/07-qc-and-smoke-testing.md`](references/07-qc-and-smoke-testing.md)
8. [`references/08-implementation-roadmap.md`](references/08-implementation-roadmap.md)

Historical lineage, Zenith comparison, and source records remain in references `01`, `02`, `04`, and `09`.

## Validation

```bash
python scripts/doctor.py
python scripts/test_doctor.py
python scripts/test_resolve_scenario.py
```

Scenario-aware provider preflight:

```bash
python scripts/doctor.py \
  --skills-root <path> \
  --strict \
  --profile autonomous \
  --scenario codex-gpt-5.6-sol
```

The doctor validates package structure, scenario profiles, exact scenario references, provider declarations, cross-scenario harness coverage, and scenario-specific provider discovery. It does not certify a future autonomous runtime that has not yet been implemented.

## License

The original scaffold and this repository have the same owner. Repository-owned material follows the repository license policy; absent an explicit open-source license, it remains all rights reserved. Third-party references retain their own attribution and license boundaries.

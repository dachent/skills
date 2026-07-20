# Agent Project Orchestrator

> **Deprecated — do not install or invoke.** It adds no demonstrated value over the original Claude Code predecessor for Claude Code, and no value over native planning and execution controls for Codex GPT-5.6 Sol. The predecessor is [gist `cdc05151d047708c290bd4da0aaeed96`](https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96).

The remaining content is retained as historical, non-operational design documentation.

> [!WARNING]
> **Evaluation finding: not currently high value; not better or more performant than the original gist scaffold.**
> Real code in this package is limited to `scripts/doctor.py` and `scripts/resolve_scenario.py` — a package
> validator and a harness/model policy lookup. None of the claimed value-add (durable backlog/memory/evidence
> beating prose state) is implemented. A full Stage 1 (`projectctl` shadow-state) implementation was drafted,
> then independently invalidated by an adversarial review (7/20 findings confirmed on re-verification) and a
> spike against a real production project's actual scaffold output: the design's core premise (a fixed,
> generically parseable Markdown grammar) does not match how the scaffold actually gets used, and the draft
> had two real data-loss bugs besides. Using this package today over the raw gist adds ceremony and a
> hard-stop on uncertified models, with no offsetting capability gained. Full finding: issue
> [#62](https://github.com/dachent/skills/issues/62), resolution in PR
> [#63](https://github.com/dachent/skills/pull/63). Re-evaluate only against a design grounded in real
> captured scaffold output, not an assumed grammar.

`agent-project-orchestrator` is a deprecated architecture and control-plane package retained only for historical reference.

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

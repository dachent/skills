# Agent Project Orchestrator

`agent-project-orchestrator` is an experimental architecture and control-plane skill for long-running human-agent projects.

It generalizes a proven Claude Code deep-planning scaffold into a project operating model with:

- explicit current-state and target-state contracts;
- prioritized backlog and task-state control;
- durable project memory and decision history;
- autonomous sprint boundaries and natural stopping conditions;
- capability/provider preflight and hard-stop rules;
- thin Claude Code and Codex adapters over shared project state;
- independent terminal verification;
- a staged path toward a deterministic `projectctl` runtime.

## Why this package exists

The original scaffold was not merely a planning prompt. In use, it supported multi-week projects, four-to-six-hour autonomous sprints, limited steering, strong handoffs, and effective divergence detection. The generalized design preserves that operating model while addressing cross-harness portability, provider drift, state integrity, security, and the stronger runtime concepts demonstrated by Zenith.

## Reading order

1. [`references/00-reading-guide.md`](references/00-reading-guide.md)
2. [`references/01-original-scaffold.md`](references/01-original-scaffold.md)
3. [`references/02-lineage-and-observed-context.md`](references/02-lineage-and-observed-context.md)
4. [`references/03-generalized-operating-model.md`](references/03-generalized-operating-model.md)
5. [`references/04-zenith-comparison.md`](references/04-zenith-comparison.md)
6. [`references/05-adversarial-architecture-review.md`](references/05-adversarial-architecture-review.md)
7. [`references/06-final-architecture.md`](references/06-final-architecture.md)
8. [`references/07-qc-and-smoke-testing.md`](references/07-qc-and-smoke-testing.md)
9. [`references/08-implementation-roadmap.md`](references/08-implementation-roadmap.md)
10. [`references/09-sources-and-provenance.md`](references/09-sources-and-provenance.md)

## Validation

```bash
python scripts/doctor.py
python scripts/test_doctor.py
```

The doctor validates this package and can optionally inspect installed skill roots. It does not certify a future autonomous runtime that has not yet been implemented.

## License

The original scaffold and this repository have the same owner. Repository-owned material follows the repository license policy; absent an explicit open-source license, it remains all rights reserved. Third-party references retain their own attribution and license boundaries.

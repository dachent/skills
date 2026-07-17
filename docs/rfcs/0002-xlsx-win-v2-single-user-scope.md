# RFC 0002: xlsx-win v2 — single-user scope amendment to RFC 0001

- Status: Proposed
- Date: 2026-07-17
- Scope: `xlsx-win` v2 runtime (amends RFC 0001)
- Decision owner: repository maintainer

## Summary

Amends RFC 0001 for the actual deployment target: one person, one Windows desktop, one interactive session, one LLM agent caller, jobs one at a time. Not a hosted or multi-tenant service, and no plan to make it one.

## Review basis

This amendment follows an independent, solution-blind review: a separate reviewer model was given only the current runtime's observed failure modes (indefinite hangs on modal prompts/slow refresh, a returned COM call treated as proof of success while data can still be stale, Excel relaunched per operation, validation limited to a post-hoc visible-error scan) and the single-desktop constraint — no RFC text, no Path A/Path C vocabulary, no proposed architecture. It was asked (1) whether this is the right problem to solve and (2) what the most optimal solution shape would be given the constraint.

Its answer independently converged on RFC 0001's core mechanisms — process supervision from outside the COM apartment, staged/transactional output, evidence-based validation — using different vocabulary. It also surfaced concrete refinements, folded into the decisions below, and an explicit technical argument against Path C for this deployment (decision 1).

## Decisions

1. **Out of scope: Issue #37** (Path C in-process Excel-DNA add-in) and its productionization. Two independent reasons: disproportionate engineering for a personal tool, and a live collision risk — an in-process add-in runs inside the user's own Excel, so a job can end up sharing the instance the human is using interactively at that moment.
2. **Out of scope: RFC 0001 Phase 5** and the fleet-operations portions of #39 (durable queue, multiple isolated Windows workers, quarantine/recycle, capacity metrics). There is one machine, not a fleet.
3. The roadmap exit criterion "Path C is the default production backend" does not apply to this implementation. The exit bar here is: hardened Path A (#36) + job contract (#34) + validation/publication gates (#38), reliable on one desktop.
4. **Job contract (#34):** a job is an ordered list of steps (`open`, `refresh[conn...]`, `recalc`, `run-macro`, `read-range`, `save-as`, ...), not a single `operation` enum field. This is how several related steps share one Excel lifecycle without one-op-per-manifest CLI round-trips.
5. **Result contract (#34/#38):** add a top-level `ok: boolean`, true only when every step succeeded and every declared invariant passed. Callers — especially an LLM agent — read one field, never AND several together to decide whether output is trustworthy.
6. **Validation scope (#38):** bounded to *completion evidence* (did each connection finish, did a freshness marker advance, did calculation reach done, are there visible errors) plus *declared invariants* (contract-supplied assertions: row-count minimums, freshness windows, sentinel cell values). Not "prove the data is correct" — the tool has no ground truth for that. State this boundary explicitly in the contract docs so it doesn't scope-creep later.
7. **Dialog handling (#36):** prevention first — `DisplayAlerts=False`, `AskToUpdateLinks=False`, `AutomationSecurity=msoAutomationSecurityForceDisable` (macros enabled only per-step when a step needs them), `Workbooks.Open(..., UpdateLinks:=0)`. UI-Automation/WinEvent modal detection is the fallback for what prevention can't cover (e.g. credential prompts), not the primary mechanism.
8. **Process termination (#36):** always PID-tracked from the Excel instance's own `Hwnd` (captured at launch), never a blind `taskkill /im excel.exe` — the user may have their own Excel open.
9. **Staging (#38):** stage and operate on a local copy outside any OneDrive/SharePoint-synced path; swap back to the original location atomically only after validation passes. Sync-locked and AutoSave-managed paths interact badly with COM automation independent of the reliability work.

## Updated acceptance criteria — Issue #34

In addition to the criteria already written into #34:

- Job schema accepts an ordered `steps` array; each step is one of the enumerated step types; unknown step types are rejected the same as unknown top-level fields.
- Result schema has a top-level `ok: boolean`, computed from the other fields (not independently settable) — `true` iff every step succeeded and every declared invariant (if any) passed.
- CLI dry-run validates a multi-step manifest without Excel and reports which step, if any, is structurally invalid.
- Nothing in #34's scope touches Excel COM directly — that remains #36.

## Non-changes

Everything else in RFC 0001 stands as written: the versioned schema-first approach, the state machine, the file-backend router (#35), and the documentation model (RFC/ADR + roadmap + child issues).

# xlsx-win v2 certification (issue #39, single-machine subset)

Certification evidence for the reduced, single-machine scope agreed in
[RFC 0002](../../../docs/rfcs/0002-xlsx-win-v2-single-user-scope.md) --
decision 2 explicitly drops the fleet-operations portions of the original
issue #39 (durable queue, multiple isolated Windows workers,
quarantine/recycle, soak testing) as moot for "one machine running one job
at a time." This directory builds only what RFC 0002 leaves in scope: a
corpus generator, two new fault-injection tests in the existing supervisor
test project, one end-to-end pipeline script, and one benchmark script.

Related documents:

- [RFC 0001](../../../docs/rfcs/0001-xlsx-win-runtime-v2.md) -- "Testing
  strategy", "Certification corpus", and "Metrics and targets" sections
  describe the original full vision this is a deliberately reduced slice of.
- [RFC 0002](../../../docs/rfcs/0002-xlsx-win-v2-single-user-scope.md) --
  decision 2 (no worker-pool/fleet), decision 1 (Path C/#37 out of scope).
- `../supervisor/README.md` -- the supervisor (#36) this directory
  certifies, including its own "Known limitations" section (referenced
  below).
- `../control_plane/` -- `file_router.py` (#35), `invariant_evaluator.py` /
  `macro_policy.py` (#38) this directory chains together.

## Adversarial review fixes (issue #39 follow-up)

A subsequent adversarial review of this directory raised six findings.
Applied here:

1. **`macro_enabled` overstated what it verifies** -- reworded this item's
   description (`corpus.py`), the corpus table above, and added the "What
   `macro_enabled` does and does not prove" section below; also strengthened
   `run_corpus.py`'s `_check_macro_policy` to additionally assert
   `workbook_inventory.inspect_workbook(...).has_macros is True`, tying the
   "macro-enabled" label to something the harness actually verifies, rather
   than leaving the check as a content-independent allowlist lookup alone.
2. **`benchmark.py`'s Comparison section didn't check either leg actually
   succeeded** before printing a faster/slower narrative -- added an
   explicit success gate (`supervisor_result["ok"] is True` and
   `legacy_result["reported_status"] == "success"` with exit code 0) that
   prints a clear "not a valid timing comparison" message and returns a
   nonzero exit code instead, if either leg did not succeed.
3. **Skip-vs-fail classification was substring matching on free-form
   `detail` text** -- added an explicit `skipped: bool` field to
   `run_corpus.py`'s `CheckResult`, set directly at each call site; `main()`
   now reads `check.skipped` instead of checking whether `"SKIPPED"`
   appears in the detail string.
4. **Unused `field` import** in `corpus.py` -- removed (`CorpusItem` never
   used `dataclasses.field`).
5. **Unused `notes` field** on `CorpusItem` -- removed (never populated by
   any corpus item, never read anywhere).
6. **Tautological `elif output_path is None:`** in `run_corpus.py`'s
   `run_item()` -- replaced with `else:` (restructured around the new
   `skipped` field so the remaining branch's condition, `not
   supervisor_check.skipped`, is independently meaningful rather than a
   three-way dispatch that only had two real outcomes).

Re-verified after the fixes: all Python unit tests (`pytest xlsx-win/v2/tests`),
the C# unit test projects, the two new fault-injection integration tests,
`run_corpus.py`, and `benchmark.py` (both with and without
`XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1`) -- see the re-run benchmark numbers
below and the no-orphan-Excel-process confirmation after each Excel-touching
run.

## What's in the corpus, and why (`corpus.py`)

`corpus.py` generates five throwaway workbooks on demand into a caller-given
temp directory (nothing here is a committed binary fixture -- same pattern
as `tests/wb_fixtures.py` / `FixtureWorkbookBuilder.cs` elsewhere in this
repo), each with a documented expected outcome:

| Item | What it is | Expected router decision | Other documented outcome |
| --- | --- | --- | --- |
| `plain_formulas` | Plain xlsx, formulas, no risk features | `openpyxl` | Passes a validation contract (required sheet, min row count, sentinel cell) evaluated directly against the file -- no Excel involved |
| `macro_enabled` | `.xlsm` with a placeholder `xl/vbaProject.bin` part | `excel_required` | Confirms `workbook_inventory.inspect_workbook(...).has_macros` is `True` for this file, and that `macro_policy.is_macro_approved` returns `False` against an empty allowlist. **Not** a proof of Excel-level macro rejection -- see below |
| `table_connection` | Worksheet Table, two data rows, no live connection | `openpyxl` | Deliberately still pushed through the real supervisor (open, refresh(all), recalc, save_as) -- see "known gap" below for why the router says `openpyxl` here and why that's not a bug |
| `external_link` | Plain xlsx + a placeholder `xl/externalLinks/*.xml` part | `excel_required` | Router-decision-only; never opened by real Excel (see corpus.py) |
| `failing_contract` | Otherwise-plain xlsx | `openpyxl` | Paired with a contract requiring 50 rows against 2 actual -- proves the harness detects and reports a failure, not just happy paths |

Two items (`macro_enabled`, `external_link`) inject a single placeholder
zip entry at the exact OOXML path `workbook_inventory.py`'s namelist-based
detection keys on (`xl/vbaProject.bin`, `xl/externalLinks/*.xml`), rather
than fabricating a genuinely valid compiled VBA project or external-link
relationship. That's sufficient to prove the *router's* decision (which only
inspects the raw zip namelist -- see `workbook_inventory.py`'s own module
docstring) without needing real Excel to ever open either file. Neither
item is opened by real Excel anywhere in this issue's harness -- see each
build function's docstring in `corpus.py` for the specific reasoning per
item.

### What `macro_enabled` does and does not prove

`macro_enabled`'s corpus workbook is not a real compiled VBA project -- it's
an openpyxl-written `.xlsm` with a fabricated placeholder byte blob injected
at `xl/vbaProject.bin` (see `corpus.py`'s `_build_macro_workbook` docstring).
Its paired check (`run_corpus.py`'s `_check_macro_policy`) asserts two
things, and only two things:

1. `workbook_inventory.inspect_workbook(...).has_macros` is `True` for this
   file -- i.e. the router's zip-namelist detection actually fired on the
   injected part, tying the "macro-enabled" label to something the harness
   verifies rather than just the item's name.
2. `control_plane/macro_policy.py`'s `is_macro_approved(...)` returns `False`
   against an empty allowlist.

`is_macro_approved` is a pure `sha256(workbook) + entrypoint-name` lookup
against a caller-supplied allowlist -- it never inspects the workbook's
actual content. Given the empty allowlist used here, it returns the
identical `False`, for the identical reason, for any input file, macro-bearing
or not (it would return `False` for `plain_formulas.xlsx` too). So this check
does **not** prove that a genuinely macro-bearing workbook is treated any
differently from a plain one, and it does not touch Excel-level enforcement
at all. The one place that would actually gate macro execution at the
Excel/COM level -- the supervisor's `run_approved_macro` step -- is
unimplemented (`../supervisor/README.md`: "not implemented ... returns
`MACRO_EXECUTION_DEFERRED`"). **Proving Excel-level `AutomationSecurity`
macro rejection is an open gap**, tracked here alongside the
`run_approved_macro` non-implementation, not something this corpus item or
check stands in for.

### Known gap surfaced by `table_connection`

`file_router.py`'s seven tracked risk fields
(`has_macros`, `is_signed`, `has_data_model`, `has_pivots`, `has_slicers`,
`has_embedded_objects`, `has_external_links`) do not include "has a
workbook connection." A workbook with a real Power-Query/OLEDB connection
loaded into a worksheet table -- and, this corpus item confirms, even one
with just a plain Table and no connection at all -- routes to `openpyxl`,
not `excel_required`, under the currently-merged #35 router. This is a real,
verified finding (not assumed from reading the code -- `run_corpus.py`
actually asserts and prints this decision), not a defect introduced by this
issue. Fixing #35's router to track connections is out of scope here;
`run_corpus.py` documents the gap by exercising this item through the
supervisor via an explicit per-item override (`exercise_supervisor=True`,
independent of the router's decision) rather than silently assuming
`excel_required` would fire.

### `power_query_minimal`: a genuine Power Query connection -- a real bug found, root-caused, and fixed

Added after the original five corpus items, at the requester's direction, specifically because none of the other five (including `table_connection`) exercise real Power Query M code -- `table_connection` uses a plain worksheet Table with **no connection at all**. `power_query_minimal` is built by shelling out to the existing `xlsx-win/scripts/power_query_excel.ps1` (`upsert-query` then `load-worksheet`) against a blank workbook -- launching Excel twice -- rather than hand-crafting the `xl/connections.xml` + `customXml` query-definition parts the way the `macro_enabled`/`external_link` items fabricate their placeholder OOXML entries; Power Query's real representation is not something this issue attempts to reproduce by hand. This is the one corpus item whose *generation*, not just its exercise through the supervisor, requires real Excel -- gated in `run_corpus.py`'s `main()`, not inside `corpus.py` (which otherwise stays Excel-free).

Router decision: `openpyxl` -- the same known gap as `table_connection` immediately above, now confirmed against a genuine M-code-backed connection instead of only a plain Table. More consequential here: `SKILL.md`'s own existing guidance is explicit that Power Query M work must go through Excel COM, never file-only libraries, so this specific misrouting is not merely suboptimal but contrary to the skill's own documented rule.

**Bug found, then fixed and reverified.** The job's actual work -- open, refresh, recalc, save -- always completed in ~9 seconds (confirmed via `events.jsonl` reaching `SAVING` then `SUCCEEDED`, and a correct `output.xlsx`), but the first two real runs (60s, then 300s budgets) both saw `EXCEL.EXE` never exit afterward, forcing the supervisor's Job-Object kill every time (zero orphaned processes both times, but a genuine `TIMED_OUT` verdict on a job that had actually succeeded). This is the same phenomenon `supervisor/README.md` already documented from earlier `PerConnectionRefreshTests` observations, now confirmed against a **genuine Power Query M / Mashup-provider connection** specifically -- and, unlike those earlier observations, actually root-caused instead of left open:

**Root cause** (found via web research -- this is a well-documented .NET/COM interop category, not something new or unsolvable -- then confirmed by direct code inspection): `StepRunner.cs`'s `RunRefresh` obtained `Workbook.Connections`, each `Connection`, and each `OLEDBConnection`/`ODBCConnection` via COM property access and never released any of them with `Marshal.ReleaseComObject`. `Application.Quit()` only *requests* an exit -- Excel will not actually terminate until every outstanding COM reference is released, and the .NET GC alone can take multiple collection cycles to get there, or in this case apparently never resolved within any budget tried.

**Fix:** explicit `Marshal.ReleaseComObject` on every one of those intermediate objects (in `finally` blocks, surviving exceptions), plus strengthening `ExcelSession.cs`'s single `GC.Collect(); GC.WaitForPendingFinalizers();` to the standard double-collect pattern. See `supervisor/README.md`'s "Connection-refresh shutdown latency" section for the full technical writeup and sources.

**Reverified twice after the fix, identical both times:** `power_query_minimal`'s `supervisor_job` check now reports `SUCCEEDED`, `ok=True`, in **12.5 seconds** -- down from timing out past 300s. The full real-Excel integration suite (all 6 tests, including the pre-existing `PerConnectionRefreshTests`) was also re-run: 5/6 passed outright, and the one failure was a separate, unrelated, pre-existing assertion bug in `PerConnectionRefreshTests` itself -- it asserted the refresh message does **not** contain the substring `"RefreshAll"`, but the correct success message legitimately says `"...individually (no RefreshAll)."`; this assertion had simply never run before, since that test always timed out before reaching it. Fixed alongside (see that test file). All 13 corpus checks plus all 6 integration tests pass now.

**Why this matters beyond this one item:** the earlier "practical implication" concern -- that a real-world workbook with substantive or multi-source Power Query could take far longer, or never clear -- no longer applies as an open risk. The actual defect was in this codebase's own COM lifecycle management, not an inherent Excel/Power-Query limitation; fixing it should generalize to any genuine Power Query connection this supervisor drives, not just this minimal fixture.

## Two new fault-injection tests (C#, existing project)

Added to the **existing**
`xlsx-win/v2/supervisor/XlsxWinSupervisor.IntegrationTests/` project --
same house style, same `ExcelIntegrationGate` preflight/postflight, same
`SupervisorRunner`/`TestTempDir` helpers as `HappyPathTests`,
`TimeoutKillTests`, `DialogPreventionTests`, `PerConnectionRefreshTests`.

- **`WorkerCrashMidJobTests`** -- the #36 review's blocker finding (a worker
  that dies before writing result.json must never cause a stale/prior
  result to be echoed as success) was fixed and unit-tested at the
  `Program.cs` level, but never proven through a real end-to-end supervisor
  invocation with an actually-crashing worker process. This test adds
  `XLSXWIN_TEST_SIMULATE_CRASH_AFTER_STEP` (a worker env var, same pattern
  as the existing `XLSXWIN_TEST_SIMULATE_HANG_SECONDS`) that makes the
  worker throw a genuinely unhandled exception after completing N steps but
  before writing its result, seeds a stale prior "success" result document
  at the same path before running, and confirms the supervisor overwrites it
  with a real `FAILED`/`ok:false`/`WORKER_EXITED_WITHOUT_RESULT` document
  instead. Before the crash, `NativeMethods.SetErrorMode` (kernel32,
  `SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX`) is called so the OS's
  "program has stopped working" crash dialog (and any registered JIT
  debugger prompt) is suppressed for this process -- a deliberate,
  documented deviation from a completely literal "just throw and see what
  happens," made specifically so this test can never leave an unclosable
  dialog on a real, actively-used desktop. Confirmed empirically to work: the
  test completes in seconds, not hanging.
- **`InvalidManifestRejectedBeforeExcelTests`** -- confirms a job manifest
  with an unrecognized step `type` (the same `UNKNOWN_STEP_TYPE` failure
  category `control_plane/schemas.py` classifies) is rejected by the
  supervisor's own manifest parsing (`JobManifest`'s `[JsonPolymorphic]`
  discriminator has no fallback, so it fails to deserialize) before
  `EnsureParentDirectory`/truncation or the worker process ever runs --
  confirmed by asserting `events.jsonl`/`result.json` don't even exist
  afterward, and that zero `EXCEL.EXE` processes exist at all, not just that
  the supervisor reported an error.

Both were run for real against the built executables this session (see
"Verification performed" below).

## Running `run_corpus.py`

```powershell
python xlsx-win/v2/certification/run_corpus.py
```

Without `XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1` set, every check that
doesn't need Excel still runs (router decisions, macro-policy rejection,
contract evaluation against the four items that don't need Excel); the one
item that's pushed through the real supervisor (`table_connection`) reports
its two Excel-dependent checks as `SKIP` (not a failure) with an explicit
message naming the env var.

To run everything for real:

```powershell
$env:XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS = "1"
python xlsx-win/v2/certification/run_corpus.py
```

`certification/excel_safety.py` is the Python-side equivalent of the C#
tests' `ExcelIntegrationGate`/`SupervisorRunner`/`BuiltExecutables`: it
refuses to run unless the env var is `1`, refuses if `EXCEL.EXE` is already
running, and polls for/asserts zero surviving `EXCEL.EXE` processes after
every supervisor invocation. It never enumerates Excel processes in order to
kill them -- termination is entirely the supervisor's own Job Object
mechanism (`JobObjectHandle.cs`); this script only ever runs the supervisor
executable as a subprocess and, as a last-resort test-level safety net,
kills the exact subprocess it itself started if it somehow doesn't exit
within a hard wall-clock timeout (never a by-name kill).

## Running `benchmark.py`

```powershell
$env:XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS = "1"
python xlsx-win/v2/certification/benchmark.py
```

Same safety gate as `run_corpus.py`. Refuses to run at all (rather than
running only one leg) if the env var isn't set or Excel is already running.

### Benchmark scope deviation: no live connection in the timed workbook

The issue's own text asks for "the same throwaway workbook (with at least
one refreshable connection)". This benchmark does **not** include one, and
that's a deliberate choice, not an oversight:

1. `supervisor/README.md`'s own "Known limitations" section already
   documents a reproduced, environment-specific finding: on this machine,
   after any real `WorkbookConnection.Refresh()` call (observed with both an
   OLEDB "Mashup"/Power Query connection and a plain TEXT/QueryTable
   connection), `EXCEL.EXE` can take anywhere from seconds to -- in four
   repeated observations in that earlier review -- apparently indefinitely,
   requiring the supervisor's Job Object to force-terminate it. Re-running
   that exact scenario here would very likely reproduce the same
   multi-minute forced-timeout outcome again, adding cost and desktop risk
   without new information.
2. Building a benchmark fixture with a genuinely live connection from this
   script would need bespoke Excel-COM-driving code (Python has no
   supported way to create a real `WorkbookConnection` via `openpyxl`, and
   this repo's control plane deliberately never imports `pywin32`). Any such
   code, running outside the supervisor's own Job-Object-protected path,
   would need its own timeout/kill safety net to be safe on a real
   desktop -- and this issue's safety rules explicitly forbid writing any
   new process-kill logic. Rather than either skip the safety net (unsafe)
   or violate that rule, this benchmark uses a connection-free workbook.

Both benchmark legs instead use the same `table_connection`-shaped workbook
as the corpus (`corpus._build_table_workbook` -- built entirely by
`openpyxl`, no Excel involved in fixture creation), so `refresh` runs over
zero connections on both sides. This is a legitimate structural comparison
(same step shape on both legs) but explicitly **not** a live-connection
refresh timing comparison -- `benchmark.py`'s own docstring and console
output say so too, not just this README.

### Real benchmark numbers measured (this session, this machine)

```
=== Supervisor leg ===
{
  "leg": "supervisor",
  "wall_clock_seconds": 63.74,
  "events_span_seconds": 2.68,
  "exit_code": 0,
  "ok": true,
  "final_state": "SUCCEEDED"
}

=== Legacy refresh_excel.ps1 leg ===
{
  "leg": "legacy_refresh_excel_ps1",
  "wall_clock_seconds": 8.65,
  "process_exit_code": 0,
  "reported_status": "success",
  "reported_duration_seconds": 4,
  "reported_exit_code": 0
}

Supervisor total wall-clock:        63.74s
Legacy refresh_excel.ps1 wall-clock: 8.65s
Supervisor was slower by 55.09s on this run.
```

**Reported honestly, per the issue's own instruction not to manufacture a
percentage**: on this run, the supervisor path was slower overall, not
faster. `events_span_seconds` (2.68s -- the time between the worker's first
and last `events.jsonl` phase transitions, i.e. the actual
open/refresh/recalc/save work) shows the real automation work was fast; the
remaining ~61s of the supervisor's 63.74s total was
`ExcelSession.CloseAndWait()` blocking on `EXCEL.EXE` actually exiting after
`Quit()` -- notably, on a workbook with **no** connection at all, which is a
new observation beyond `supervisor/README.md`'s existing
connection-refresh-specific finding. For comparison, an *identically-shaped*
job (open, refresh(all) over zero connections, recalc, save_as) run earlier
in this same session via `run_corpus.py`'s `table_connection` item completed
in 7.2s total. Two real measurements of the same step shape, 7.2s and
63.7s, is itself the honest finding here: Excel's own process-exit latency
on this machine varies a lot, for reasons not fully understood and not
specific to connection refresh, and the supervisor's wall-clock total is
directly exposed to that variance because (by design, see
`supervisor/README.md`'s "Why the worker blocks on Excel's own process
exit") it never reports success until `EXCEL.EXE` is confirmed gone. The
legacy script's `Close()`/`Quit()` in its `finally` block does not wait for
`EXCEL.EXE` to actually exit before the script itself returns, so its
reported number is not exposed to this variance the same way -- meaning the
legacy script's number is not strictly an apples-to-apples "total automation
latency" figure either; it can return before Excel has actually finished
tearing down.

#### Re-run after the adversarial-review fixes (new session, same machine)

Re-measured after applying the fixes described in "Adversarial review fixes"
below (`ok`/success-gated comparison added to `benchmark.py`; no other
change touches timing behavior):

```
=== Supervisor leg ===
{
  "leg": "supervisor",
  "wall_clock_seconds": 6.75,
  "events_span_seconds": 1.95,
  "exit_code": 0,
  "ok": true,
  "final_state": "SUCCEEDED"
}

=== Legacy refresh_excel.ps1 leg ===
{
  "leg": "legacy_refresh_excel_ps1",
  "wall_clock_seconds": 8.39,
  "process_exit_code": 0,
  "reported_status": "success",
  "reported_duration_seconds": 4,
  "reported_exit_code": 0
}

Supervisor total wall-clock:        6.75s
Legacy refresh_excel.ps1 wall-clock: 8.39s
Supervisor was faster by 1.64s on this run, for this no-live-connection job shape.
```

Both legs reported `ok`/success this time (the new success-gate in
`benchmark.py` printed the normal comparison rather than the "not a valid
timing comparison" warning, because both legs actually succeeded). This
run's `EXCEL.EXE` teardown was fast (6.75s total vs. the earlier 63.74s),
consistent with this section's own point above: Excel's own process-exit
latency on this machine varies run to run, for reasons not fully understood.
Three real measurements of the same step shape now exist across sessions --
7.2s, 63.7s, and 6.75s (supervisor total wall-clock) -- which only reinforces
that this benchmark measures real, variable Excel teardown latency, not a
stable percentage either implementation "wins" by. Both runs are left in
this document rather than overwriting the earlier one, so the variance is
visible rather than silently replaced by whichever number happened to be
measured most recently.

The real value of the supervisor over the legacy script demonstrated by
this issue's work is **bounded, attributable failure and no orphan Excel
process under fault conditions** (the two new fault-injection integration
tests above, plus the pre-existing `TimeoutKillTests`) -- not raw speed for
a clean run. That is exactly what RFC 0001's "at least 30% lower automation
overhead" target was framed around (eliminating *multiple* Excel launches
for one logical operation), not a single equivalent job against an
already-single-lifecycle legacy script.

## Real-world validation against production workbooks

Beyond the synthetic corpus, the repo maintainer provided two real, external production workbooks for validation -- not committed to this repo (confidentiality; they're the maintainer's own business data, on their own machine) and not part of the automated corpus, but run through the same pipeline (`workbook_inventory` -> `file_router` -> the real supervisor) for real, once per file, on this machine:

- **Workbook A** -- small, self-contained, all data inside the file. Router: correctly detected real PivotTables and routed to `excel_required` (no macros/signature/data-model/external-links/slicers/embedded-objects). Run through the supervisor (open, refresh, recalc, save-as to a new output): `SUCCEEDED`, `ok=true`. Zero connections to refresh (matches "all data inside the file"). Output verified structurally intact (same sheet names/count as the input) before discarding.
- **Workbook B** -- large (100 sheets, ~38MB), with a genuine Data Model, external workbook links, PivotTables, and 10 real Power Query connections pulling data from other files on the same drive. Router: correctly detected all three tracked risk features simultaneously (`has_data_model`, `has_external_links`, `has_pivots`) and routed to `excel_required`. Run through the supervisor: `SUCCEEDED`, `ok=true`, all 10 connections refreshed individually, full recalculation reached `xlDone`, saved to a new output (38,547,943 bytes vs. the 38,560,372-byte input -- normal resave variance, not data loss). Total wall-clock ~3 minutes (open ~8s, refresh of all 10 connections ~2m39s, calc+save ~10s). Zero orphaned Excel processes after either workbook.

Both files were staged to a local temp copy before any Excel automation touched them; neither original was ever opened, written to, or had the supervisor's `save_as` step point at its real location. Neither was run through the crash-simulation or forced-kill fault-injection tests -- those stay scoped to the synthetic corpus; these two only exercised the real happy-path pipeline.

**Why Workbook B matters beyond "it worked":** it's the real-world case the `power_query_minimal` finding above predicted would be at risk -- a large workbook with genuine, multi-source Power Query connections is exactly the shape that reproduced the Excel-not-exiting bug on the minimal synthetic fixture. Workbook B succeeding cleanly, with all 10 connections refreshed and the process exiting promptly, is the strongest evidence available on this machine that the COM-release fix generalizes beyond the minimal repro case rather than only fixing that one specific fixture.

## Explicitly out of scope for this issue (RFC 0002 decision 2)

Per the issue's own instruction, listed here with one-line reasons rather
than built:

- **Worker provisioning, connector/driver certification across a fleet** --
  there is one machine, one worker, provisioned once, by hand, already.
- **Health checks, quarantine, recycle across workers** -- there is no pool
  to quarantine or recycle from; the supervisor only ever runs one worker
  process at a time, by construction.
- **Upgrade/rollback runbooks** -- no fleet to roll out to.
- **Soak testing (repeated-run duration/memory/handle telemetry over many
  hours)** -- moot for one machine running one job at a time; the fault
  suite above already proves the no-orphan property under the fault
  conditions in scope.
- **"Path C passes certification"** -- moot; Path C (#37) is closed, not
  planned (RFC 0002 decision 1).

## What this issue could not fully satisfy against the original acceptance criteria, and why

- *"100% of test jobs reach bounded final states"* / *"at least 95% of
  injected failures identify the failing phase and normalized cause"* --
  satisfied for the fault scenarios actually built here (worker crash,
  invalid manifest, timeout/hang, dialog prevention) but not against the
  original issue's full fault list (expired credentials, locks, rejected
  COM calls, desktop disconnects, add-in failure/version mismatch) -- most
  of those don't apply to this reduced scope (no add-in/Path C, no fleet) or
  would need dedicated fixture engineering beyond this issue's "keep it
  lean" instruction.
- *"Benchmark report quantifies startup overhead, total duration, peak
  memory, retries, and fidelity"* -- this benchmark reports total duration
  and (via `events_span_seconds`) a startup/work-time breakdown, but not
  peak memory or retries (the increment being certified has no retry logic
  to measure, and process memory sampling was judged out of proportion for
  a single-job, single-machine benchmark).
- *"Operational documentation permits rebuilding and certifying a clean
  Windows worker without undocumented manual steps"* -- out of scope per
  RFC 0002 decision 2 (no fleet to provision workers for); this machine's
  own Excel/`.NET` SDK install was not re-provisioned from scratch as part
  of this issue.

#!/usr/bin/env python3
"""End-to-end certification pipeline proof for issue #39 (single-machine subset).

For each corpus workbook from `corpus.py`, chains the real control-plane
pieces together and asserts the documented expected outcome:

1. `file_router.choose_backend` (via the Python modules directly -- never
   the CLI) to get a routing decision; asserted against the item's own
   documented `expected_backend`.
2. For the one item whose documented purpose is to exercise the
   supervisor's refresh step end-to-end (`exercise_supervisor=True` --
   independent of the router decision; see corpus.py), builds a job
   manifest, invokes the built `XlsxWinSupervisor.exe` as a subprocess
   (gated behind `excel_safety`'s opt-in + preflight + no-survivor checks),
   and reads back its result.json.
3. `invariant_evaluator.evaluate_contract` against a small validation
   contract for that workbook (the supervisor's output, if step 2 ran;
   otherwise the original input), asserted against the item's own
   documented `expected_contract_pass`.
4. For the macro-enabled item, `macro_policy.is_macro_approved` with an
   empty allowlist, asserted False.

This is the one piece of new Python -> supervisor wiring in this issue --
kept local to this script, per the issue's own instruction not to touch
`control_plane/cli.py`.

Usage:
    python xlsx-win/v2/certification/run_corpus.py

Set XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1 first to allow the one corpus item
that launches real Excel (via the supervisor) to actually run; without it,
that item's supervisor-exercising check is skipped (reported, not silently
omitted) and every router/contract/macro-policy check that doesn't need
Excel still runs normally.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
if str(_V2_ROOT) not in sys.path:
    sys.path.insert(0, str(_V2_ROOT))
_CERT_ROOT = Path(__file__).resolve().parent
if str(_CERT_ROOT) not in sys.path:
    sys.path.insert(0, str(_CERT_ROOT))

import excel_safety  # noqa: E402
from corpus import CorpusItem, build_corpus, build_power_query_item  # noqa: E402
from control_plane.file_router import choose_backend  # noqa: E402
from control_plane.invariant_evaluator import evaluate_contract  # noqa: E402
from control_plane.macro_policy import is_macro_approved  # noqa: E402
from control_plane.workbook_inventory import inspect_workbook  # noqa: E402

# Bounded, generous timeouts for items exercised through the real
# supervisor. table_connection has no live workbook connection, so
# supervisor/README.md's "connection-refresh shutdown latency" issue does
# not apply to it -- but power_query_minimal DOES have a genuine Power Query
# connection, and a first run at a tighter budget (60s) reproduced that
# exact same documented issue against it (TIMED_OUT at 69.4s elapsed; no
# orphaned Excel process afterward -- the supervisor's kill still worked
# correctly). Budget widened here accordingly; see README.md's own note on
# the actual number this required.
_SUPERVISOR_TIMEOUTS = {
    "start_excel_seconds": 30,
    "open_workbook_seconds": 30,
    "refresh_total_seconds": 300,
    "calculation_seconds": 30,
    "save_seconds": 30,
    "close_seconds": 300,
}
_SUPERVISOR_HARD_TIMEOUT_SECONDS = 420


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    skipped: bool = False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_router_decision(item: CorpusItem) -> CheckResult:
    inventory = inspect_workbook(item.input_path)
    decision = choose_backend(item.intent, inventory)
    passed = decision.backend == item.expected_backend
    return CheckResult(
        name=f"{item.name}: router_decision",
        passed=passed,
        detail=(
            f"expected={item.expected_backend!r} actual={decision.backend!r} "
            f"reason={decision.reason!r}"
        ),
    )


def _check_macro_policy(item: CorpusItem) -> CheckResult:
    """Two independent assertions, deliberately not conflated into one claim
    of "macro rejection": (1) the router's own zip-namelist detection
    actually identified this workbook as macro-bearing (has_macros is True)
    -- tying the "macro-enabled" label to something the harness actually
    verifies, rather than trusting the corpus item's own name; (2)
    is_macro_approved(...) returns False against an empty allowlist. Neither
    assertion, alone or together, proves this workbook's macro content is
    treated differently from a plain workbook's at Excel/COM execution time
    -- is_macro_approved is a content-independent sha256+entrypoint lookup
    that would return the identical False for plain_formulas.xlsx too. See
    corpus.py's description for this item and README.md for the open gap
    this does not close (Excel-level AutomationSecurity macro rejection;
    the supervisor's run_approved_macro step is unimplemented)."""
    macro_name, allowlist = item.macro_check
    workbook_sha256 = _sha256_file(item.input_path)
    inventory = inspect_workbook(item.input_path)
    approved = is_macro_approved(workbook_sha256, macro_name, allowlist)
    passed = inventory.has_macros is True and approved is False
    return CheckResult(
        name=f"{item.name}: macro_policy_rejects_unapproved_macro",
        passed=passed,
        detail=(
            f"has_macros={inventory.has_macros!r} (expected True) "
            f"is_macro_approved(...)={approved!r} (expected False; allowlist={allowlist!r}) "
            "-- NOTE: this only proves zip-namelist detection fired and a "
            "content-independent allowlist lookup returned False; it does not prove "
            "Excel-level macro rejection (see docstring)"
        ),
    )


def _build_job_manifest(item: CorpusItem, output_path: Path) -> dict:
    steps = list(item.steps) + [
        {"type": "save_as", "output_path": str(output_path), "overwrite": True}
    ]
    # This manifest deliberately is not run through
    # control_plane.schemas.validate_job: job.schema.json does not yet
    # declare a top-level "timeouts" object (additionalProperties: false
    # would reject it) -- see supervisor/README.md, "Known gap vs
    # job.schema.json". The C# supervisor's own JobManifest model tolerates
    # it. This script writes the manifest directly for that reason, exactly
    # as documented there.
    return {
        "schema_version": "2.0",
        "idempotency_key": f"certification-{item.name}",
        "steps": steps,
        "timeouts": _SUPERVISOR_TIMEOUTS,
    }


def _run_through_supervisor(item: CorpusItem, run_dir: Path) -> tuple[CheckResult, Path | None]:
    """Returns (check_result, output_path_or_None). output_path is None when
    the supervisor step was skipped (opt-in not set) or failed."""
    try:
        excel_safety.preflight_or_raise()
    except excel_safety.ExcelSafetyError as exc:
        return (
            CheckResult(
                name=f"{item.name}: supervisor_job",
                passed=False,
                skipped=True,
                detail=f"SKIPPED (not a failure): {exc}",
            ),
            None,
        )

    job_path = run_dir / f"{item.name}.job.json"
    events_path = run_dir / f"{item.name}.events.jsonl"
    result_path = run_dir / f"{item.name}.result.json"
    output_path = run_dir / f"{item.name}.output.xlsx"

    manifest = _build_job_manifest(item, output_path)
    job_path.write_text(json.dumps(manifest), encoding="utf-8")

    try:
        run_result = excel_safety.run_supervisor(
            job_path, events_path, result_path, _SUPERVISOR_HARD_TIMEOUT_SECONDS
        )
    finally:
        excel_safety.assert_no_excel_survives()

    if not result_path.exists() or result_path.stat().st_size == 0:
        return (
            CheckResult(
                name=f"{item.name}: supervisor_job",
                passed=False,
                detail=(
                    f"No result.json written. exit_code={run_result.exit_code} "
                    f"stdout={run_result.stdout!r} stderr={run_result.stderr!r}"
                ),
            ),
            None,
        )

    result_doc = json.loads(result_path.read_text(encoding="utf-8"))
    ok = result_doc.get("ok") is True
    matched_expectation = ok == item.expected_supervisor_ok
    detail = (
        f"exit_code={run_result.exit_code} elapsed={run_result.elapsed_seconds:.1f}s "
        f"final_state={result_doc.get('final_state')!r} ok={result_doc.get('ok')!r} "
        f"expected_ok={item.expected_supervisor_ok!r} "
        f"steps={[(s.get('type'), s.get('status')) for s in result_doc.get('steps', [])]}"
    )

    # A genuine job success always has a trustworthy output. The one other
    # case where an output is still usable: this item DOCUMENTED that a
    # TIMED_OUT verdict is the expected outcome (expected_supervisor_ok is
    # False) and the run matched that expectation -- meaning the worker's own
    # events already showed it completed its real work (SAVING/SUCCEEDED)
    # before the supervisor's separate, correct wait for Excel's actual
    # process exit ran out the clock (see corpus.py's power_query_minimal
    # description). An UNEXPECTED failure (matched_expectation is False)
    # never gets its output trusted, regardless of whether a file happens to
    # exist at that path -- that's exactly the "possibly nonexistent/stale
    # output" case run_item()'s caller already guards against.
    output_is_usable = ok or (
        matched_expectation and output_path.exists() and output_path.stat().st_size > 0
    )
    return (
        CheckResult(name=f"{item.name}: supervisor_job", passed=matched_expectation, detail=detail),
        output_path if output_is_usable else None,
    )


def _check_contract(item: CorpusItem, target_path: Path) -> CheckResult:
    invariants = evaluate_contract(target_path, item.contract)
    all_passed = all(entry["passed"] for entry in invariants)
    passed = all_passed == item.expected_contract_pass
    failing = [entry for entry in invariants if not entry["passed"]]
    return CheckResult(
        name=f"{item.name}: validation_contract",
        passed=passed,
        detail=(
            f"expected_all_passed={item.expected_contract_pass!r} actual_all_passed={all_passed!r} "
            f"failing_invariants={failing!r}"
        ),
    )


def run_item(item: CorpusItem, run_dir: Path) -> list[CheckResult]:
    results = [_check_router_decision(item)]

    if item.macro_check is not None:
        results.append(_check_macro_policy(item))

    if item.contract is not None:
        target_path = Path(item.input_path)
        if item.exercise_supervisor:
            supervisor_check, output_path = _run_through_supervisor(item, run_dir)
            results.append(supervisor_check)
            if output_path is not None:
                target_path = output_path
            elif not supervisor_check.skipped:
                # The supervisor job actually ran and failed -- evaluating
                # the contract against the (possibly nonexistent/stale)
                # input instead of a real output would be misleading, so
                # skip the contract check rather than report a misleading
                # pass/fail against the wrong file.
                results.append(
                    CheckResult(
                        name=f"{item.name}: validation_contract",
                        passed=False,
                        detail="Skipped: the supervisor job did not succeed, no output to validate.",
                    )
                )
                return results
            else:
                # Opt-in not set: the supervisor step was skipped, not
                # failed. Report the contract check as skipped too, rather
                # than silently evaluating it against the unmodified input
                # and calling that equivalent.
                results.append(
                    CheckResult(
                        name=f"{item.name}: validation_contract",
                        passed=False,
                        skipped=True,
                        detail=(
                            "SKIPPED (not a failure): supervisor job was not run "
                            f"(set {excel_safety.RUN_ENV_VAR}=1 to run it)."
                        ),
                    )
                )
                return results

        results.append(_check_contract(item, target_path))

    return results


def main() -> int:
    run_dir = Path(tempfile.mkdtemp(prefix="xlsx-win-cert-corpus-"))
    corpus_dir = run_dir / "corpus"
    items = build_corpus(corpus_dir)

    all_results: list[CheckResult] = []

    # power_query_minimal is the one corpus item that needs real Excel to
    # *build*, not just to exercise -- see corpus.py's module docstring.
    # Gated here, not inside corpus.py, so build_corpus() itself stays
    # Excel-free and this is the single place that decides whether this
    # item exists for a given run.
    try:
        excel_safety.preflight_or_raise()
        pq_item = build_power_query_item(corpus_dir)
    except excel_safety.ExcelSafetyError as exc:
        print("\n=== power_query_minimal ===")
        print(f"  [SKIP] power_query_minimal: build: SKIPPED (not a failure): {exc}")
        all_results.append(
            CheckResult(
                name="power_query_minimal: build",
                passed=False,
                skipped=True,
                detail=f"SKIPPED (not a failure): {exc}",
            )
        )
    else:
        excel_safety.assert_no_excel_survives()
        items.append(pq_item)

    for item in items:
        print(f"\n=== {item.name} ===")
        print(item.description)
        item_results = run_item(item, run_dir)
        all_results.extend(item_results)
        for check in item_results:
            status = "SKIP" if check.skipped else ("PASS" if check.passed else "FAIL")
            print(f"  [{status}] {check.name}: {check.detail}")

    skipped_results = [r for r in all_results if r.skipped]
    real_results = [r for r in all_results if not r.skipped]
    failed_results = [r for r in real_results if not r.passed]

    print("\n=== Summary ===")
    print(f"Total checks: {len(all_results)}")
    print(f"Passed: {len(real_results) - len(failed_results)}")
    print(f"Failed: {len(failed_results)}")
    print(f"Skipped (opt-in not set): {len(skipped_results)}")
    print(f"Corpus + run artifacts left at: {run_dir}")

    if failed_results:
        print("\nFailing checks:")
        for r in failed_results:
            print(f"  - {r.name}: {r.detail}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

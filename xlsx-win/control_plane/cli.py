#!/usr/bin/env python3
"""xlsx-win v2 control-plane CLI.

`validate` schema-checks a manifest. `dry-run` schema-checks a manifest and
prints the state sequence it would traverse. Neither needs Excel installed,
and neither reads a workbook file: this module never imports pywin32 or
anything that touches COM. That is issue #36's job.

`route` (issue #35) inspects a workbook's OOXML package directly rather than
opening it, via `workbook_inventory.py` (zipfile + minimal XML parsing) --
no Excel needed, and it never imports openpyxl either.

`validate-contract` (issue #38) does read a workbook file -- with openpyxl,
never Excel/COM -- to evaluate a validation contract's declared invariants
against it. It still never imports pywin32 or drives Excel.

`run` (issue #71) is the one subcommand that touches Excel, indirectly: it
validates a job manifest exactly like `validate` (failing closed, before
ever resolving or invoking anything else, if the manifest is invalid), then
resolves and invokes the built `XlsxWinSupervisor.exe` (#36) as a
subprocess via `control_plane/supervisor_runner.py`, which is the only
place in this module's own import chain that can end up driving real Excel
COM automation -- and even that happens one process boundary away, inside
the supervisor/worker executables, never inside this Python process itself.
`run` does not call `file_router.choose_backend`: a job manifest's steps
are already inherently Excel-COM operations by construction, so there is no
routing decision left to make here -- `route` is the earlier, separate
decision a caller makes before ever building a job manifest.

`run` also performs pre-touch staging (issue #72, RFC 0002 decision 9): the
`open` step's `workbook_path` is staged into a local temp copy
(`staging.stage_copy`) before the supervisor is ever invoked, and the
supervisor runs against an in-memory-rewritten copy of the manifest that
points at that staged copy -- the caller's on-disk manifest file itself is
never mutated, and the manifest's real input path is never opened directly.
If the manifest also has a `save_as` step, that step's `output_path` is
likewise rewritten to a staged location, and `staging.publish` swaps the
staged output into the real target path only after the supervisor reports
`ok: true` -- a failed job leaves the original `save_as.output_path`
completely untouched. See `cmd_run`'s own docstring for the full sequence.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import sys
from pathlib import Path

# Runnable directly as a script (`python cli.py ...`) as well as as part of
# the control_plane package (`python -m control_plane.cli ...` with cwd set
# to xlsx-win). Direct execution has no package context, so relative
# imports would fail; fall back to inserting xlsx-win/ onto sys.path and
# importing control_plane absolutely. ("xlsx-win" contains a hyphen, so it can never be
# part of a dotted `-m` module path from the repo root.)
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from control_plane.dry_run import simulate_transitions
    from control_plane.errors import ContractError
    from control_plane.file_router import KNOWN_INTENTS, choose_backend
    from control_plane.invariant_evaluator import evaluate_contract
    from control_plane.schemas import validate_job
    from control_plane.staging import publish, stage_copy
    from control_plane.supervisor_runner import SupervisorLaunchError, run_supervisor
    from control_plane.workbook_inventory import inspect_workbook
else:
    from .dry_run import simulate_transitions
    from .errors import ContractError
    from .file_router import KNOWN_INTENTS, choose_backend
    from .invariant_evaluator import evaluate_contract
    from .schemas import validate_job
    from .staging import publish, stage_copy
    from .supervisor_runner import SupervisorLaunchError, run_supervisor
    from .workbook_inventory import inspect_workbook


# Wall-clock safety-net timeout (seconds) for the supervisor subprocess
# itself, separate from a job manifest's own per-phase deadlines (which the
# supervisor enforces internally -- see supervisor/README.md). Generous by
# design: it only needs to fire if the supervisor's own deadline
# enforcement somehow failed to.
_DEFAULT_HARD_TIMEOUT_SECONDS = 900.0


def _load_json_file(path: Path) -> dict:
    """Read and parse a JSON file, normalizing I/O and parse failures to ContractError.

    Used for job manifests, validation contracts, and any other on-disk
    JSON document this CLI reads -- the failure shape (SCHEMA_INVALID: not
    found / not valid JSON) is the same regardless of which kind of document
    it is.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContractError(
            "SCHEMA_INVALID", f"File not found: {path}", {"path": str(path)}
        ) from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractError(
            "SCHEMA_INVALID", f"File is not valid JSON: {exc}", {"path": str(path)}
        ) from exc


def _print_error(exc: ContractError) -> None:
    print(json.dumps({"valid": False, "error": exc.to_dict()}, indent=2))


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        job = _load_json_file(Path(args.manifest))
        validate_job(job)
    except ContractError as exc:
        _print_error(exc)
        return 1

    print(json.dumps({"valid": True}, indent=2))
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    try:
        job = _load_json_file(Path(args.manifest))
        validate_job(job)
        states = simulate_transitions(job)
    except ContractError as exc:
        _print_error(exc)
        return 1

    print(json.dumps({"valid": True, "states": states}, indent=2))
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    inventory = inspect_workbook(args.workbook)
    decision = choose_backend(args.intent, inventory)
    print(json.dumps(dataclasses.asdict(decision), indent=2))
    return 0


def cmd_validate_contract(args: argparse.Namespace) -> int:
    try:
        contract = _load_json_file(Path(args.contract))
        invariants = evaluate_contract(Path(args.workbook), contract)
    except ContractError as exc:
        _print_error(exc)
        return 1

    all_passed = all(item["passed"] for item in invariants)
    print(json.dumps({"invariants": invariants, "all_passed": all_passed}, indent=2))
    return 0 if all_passed else 2


def _stage_job_for_run(job: dict) -> tuple[dict, Path | None, list[tuple[str, str]]]:
    """Build an in-memory, staged copy of a validated job dict (issue #72,
    RFC 0002 decision 9).

    Never mutates `job` itself -- returns a deep copy. If the job has an
    `open` step (only the first one is staged; a manifest realistically has
    exactly one), that step's `workbook_path` is rewritten to point at a
    fresh local copy made by `staging.stage_copy`, so the manifest's real
    input path is never opened directly. Every `save_as` step's
    `output_path` is likewise rewritten to a path inside that same staging
    directory, so the real output target is never written to directly
    either.

    If the job has no `open` step, staging is a no-op: nothing is rewritten,
    the returned staging directory is `None`, and `save_as_targets` is
    empty -- there is no input path for staging to protect a job that never
    opens one from touching.

    Returns `(staged_job, staging_dir, save_as_targets)`, where
    `staging_dir` is the fresh local temp directory `stage_copy` created
    (`None` if staging did not engage) and `save_as_targets` is a list of
    `(staged_output_path, original_output_path)` string pairs -- one per
    `save_as` step -- for the caller to `staging.publish` after confirming
    the run actually succeeded.

    Raises ContractError (STAGING_INVALID) if `stage_copy` cannot stage the
    open step's source path (missing file, etc.) -- propagated to the
    caller rather than caught here, since this is a genuine failure to even
    begin the run, not a normal outcome.
    """
    staged_job = copy.deepcopy(job)

    open_step = next((s for s in staged_job.get("steps", []) if s.get("type") == "open"), None)
    if open_step is None:
        return staged_job, None, []

    staged_input_path = stage_copy(Path(open_step["workbook_path"]))
    staging_dir = staged_input_path.parent
    open_step["workbook_path"] = str(staged_input_path)

    save_as_targets: list[tuple[str, str]] = []
    for index, step in enumerate(staged_job["steps"]):
        if step.get("type") == "save_as":
            original_output_path = step["output_path"]
            # Prefix with the step's index so two save_as steps whose
            # output_path values share a basename (but live in different
            # directories) never collide on the same staged path -- see
            # issue #72 review finding (blocker): without this prefix,
            # staging.publish's os.replace (a move, not a copy) would let
            # the second step's staged write silently clobber the first
            # step's staged file, cross-contaminating one real target with
            # the other step's content and leaving the other publish() to
            # fail outright with STAGING_INVALID.
            staged_output_path = staging_dir / f"save_as_{index}_{Path(original_output_path).name}"
            step["output_path"] = str(staged_output_path)
            save_as_targets.append((str(staged_output_path), original_output_path))

    return staged_job, staging_dir, save_as_targets


def cmd_run(args: argparse.Namespace) -> int:
    """Validate a job manifest, then run it for real via the built supervisor.

    Sequence:

    1. Schema-validate the manifest exactly like `validate` does. Fails
       closed (returns before touching staging, the supervisor, or Excel at
       all) if this fails.
    2. Pre-touch staging (issue #72, RFC 0002 decision 9): stage the open
       step's `workbook_path` into a fresh local temp copy
       (`staging.stage_copy`) and build an *in-memory* copy of the parsed
       job dict with that step's `workbook_path` rewritten to the staged
       copy -- the caller's on-disk manifest file is never mutated, and the
       manifest's real input path is never opened directly. Any `save_as`
       step's `output_path` is likewise rewritten to a path inside that same
       staging directory, so the real save target is never written to
       directly either. A manifest with no `open` step (or no `save_as`
       step) degrades gracefully: staging only ever engages for the pieces
       of the job actually present. This staged manifest -- not the
       original on-disk file -- is what gets written out and handed to the
       supervisor.
    3. Resolves and invokes the built `XlsxWinSupervisor.exe` against the
       staged manifest (`control_plane/supervisor_runner.py`).
    4. Reads back `result.json`. Only if it reports `ok: true` **and** the
       job had one or more `save_as` steps, calls `staging.publish` for each
       one, atomically swapping that step's staged output into its
       original, real `output_path`. If the job failed (`ok` is `false` or
       missing), or the supervisor could not even be invoked, nothing is
       published and every original `save_as.output_path` is left
       completely untouched -- this is RFC 0002 decision 9's whole point.
    5. Prints the result document and exits with the supervisor's own exit
       code, unmodified (see supervisor/README.md's exit-code contract) --
       unless step 4's publish itself fails (a rare, last-ditch sanity-check
       failure in `staging.publish`, e.g. a zero-byte staged output), in
       which case that error is printed instead and this returns 1.
    """
    manifest_path = Path(args.manifest)

    try:
        job = _load_json_file(manifest_path)
        validate_job(job)
    except ContractError as exc:
        _print_error(exc)
        return 1

    events_path = (
        Path(args.events)
        if args.events
        else manifest_path.parent / f"{manifest_path.stem}.events.jsonl"
    )
    result_path = (
        Path(args.result)
        if args.result
        else manifest_path.parent / f"{manifest_path.stem}.result.json"
    )

    try:
        staged_job, staging_dir, save_as_targets = _stage_job_for_run(job)
    except ContractError as exc:
        _print_error(exc)
        return 1

    if staging_dir is None:
        # No `open` step: nothing was staged, so there is no reason to write
        # out a second copy of an unchanged manifest -- run the caller's
        # original on-disk file exactly as issue #71 did.
        job_path_to_run = manifest_path
    else:
        # stage_copy already gave us a fresh local temp directory for this
        # run's staged input; reuse it for the staged manifest too rather
        # than minting a second temp directory.
        job_path_to_run = staging_dir / "staged_job.json"
        job_path_to_run.write_text(json.dumps(staged_job), encoding="utf-8")

    try:
        run_result = run_supervisor(job_path_to_run, events_path, result_path, args.hard_timeout_seconds)
    except (FileNotFoundError, SupervisorLaunchError) as exc:
        _print_error(
            ContractError(
                "SUPERVISOR_INVOCATION_FAILED",
                str(exc),
                {"events_path": str(events_path), "result_path": str(result_path)},
            )
        )
        return 1

    if result_path.exists() and result_path.stat().st_size > 0:
        result_doc = json.loads(result_path.read_text(encoding="utf-8"))
    else:
        # The supervisor's own exit-code contract (see supervisor/README.md)
        # reserves 2 for argument/manifest-parse errors before any Excel
        # work started -- a case where it may never reach writing
        # result.json at all. Report what we know rather than crash trying
        # to read a file that doesn't exist.
        result_doc = {
            "error": (
                f"XlsxWinSupervisor exited (code {run_result.exit_code}) without writing a "
                f"result document at {result_path}. stdout={run_result.stdout!r} "
                f"stderr={run_result.stderr!r}"
            )
        }

    # Pre-touch staging's swap-back half (issue #72, RFC 0002 decision 9):
    # only publish a staged save_as output into its real target once the job
    # is confirmed to have actually succeeded. A failed job (or one whose
    # result document we couldn't even read) leaves every original
    # save_as.output_path completely untouched -- no partial/best-effort
    # publish.
    if save_as_targets and isinstance(result_doc, dict) and result_doc.get("ok") is True:
        for staged_output_path, original_output_path in save_as_targets:
            try:
                publish(Path(staged_output_path), Path(original_output_path))
            except ContractError as exc:
                _print_error(exc)
                return 1

    print(json.dumps(result_doc, indent=2))
    # Pass the supervisor's own exit code through verbatim -- it is not
    # reinterpreted or wrapped here. See supervisor/README.md for what each
    # code means; a caller must read result.json's final_state/ok fields to
    # learn the job's outcome, not this process's exit code alone.
    return run_result.exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xlsx-win-v2-control-plane",
        description="Validate and dry-run xlsx-win v2 job manifests. Never touches Excel.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Schema-check a manifest.")
    validate_parser.add_argument("manifest", help="Path to a job manifest JSON file.")
    validate_parser.set_defaults(handler=cmd_validate)

    dry_run_parser = subparsers.add_parser(
        "dry-run",
        help="Schema-check a manifest and print the state sequence it would traverse.",
    )
    dry_run_parser.add_argument("manifest", help="Path to a job manifest JSON file.")
    dry_run_parser.set_defaults(handler=cmd_dry_run)

    route_parser = subparsers.add_parser(
        "route",
        help="Inspect a workbook and print the deterministic RouterDecision as JSON.",
    )
    route_parser.add_argument("workbook", help="Path to the workbook to inspect and route.")
    route_parser.add_argument(
        "intent", choices=sorted(KNOWN_INTENTS), help="What the caller intends to do with it."
    )
    route_parser.set_defaults(handler=cmd_route)

    validate_contract_parser = subparsers.add_parser(
        "validate-contract",
        help=(
            "Evaluate a workbook validation contract's declared invariants against a "
            "saved workbook and print the invariant results as JSON. Reads cached "
            "values (openpyxl data_only=True), not live formulas."
        ),
    )
    validate_contract_parser.add_argument("workbook", help="Path to the .xlsx/.xlsm workbook.")
    validate_contract_parser.add_argument("contract", help="Path to a validation-contract JSON file.")
    validate_contract_parser.set_defaults(handler=cmd_validate_contract)

    run_parser = subparsers.add_parser(
        "run",
        help=(
            "Validate a job manifest, then invoke the built XlsxWinSupervisor.exe against it "
            "for real. The only subcommand that touches Excel (indirectly, one process "
            "boundary away)."
        ),
    )
    run_parser.add_argument("manifest", help="Path to a job manifest JSON file.")
    run_parser.add_argument(
        "--events",
        help=(
            "Path to write events.jsonl to. Defaults to <manifest-stem>.events.jsonl next to "
            "the manifest."
        ),
    )
    run_parser.add_argument(
        "--result",
        help=(
            "Path to write result.json to. Defaults to <manifest-stem>.result.json next to "
            "the manifest."
        ),
    )
    run_parser.add_argument(
        "--hard-timeout-seconds",
        type=float,
        default=_DEFAULT_HARD_TIMEOUT_SECONDS,
        help=(
            "Wall-clock safety-net timeout in seconds for the supervisor subprocess itself, "
            "separate from the job manifest's own phase deadlines. Default: %(default)s."
        ),
    )
    run_parser.set_defaults(handler=cmd_run)

    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

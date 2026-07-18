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
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

# Runnable directly as a script (`python cli.py ...`) as well as as part of
# the control_plane package (`python -m control_plane.cli ...` with cwd set
# to xlsx-win/v2). Direct execution has no package context, so relative
# imports would fail; fall back to inserting v2/ onto sys.path and importing
# control_plane absolutely. ("xlsx-win" contains a hyphen, so it can never be
# part of a dotted `-m` module path from the repo root.)
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from control_plane.dry_run import simulate_transitions
    from control_plane.errors import ContractError
    from control_plane.file_router import KNOWN_INTENTS, choose_backend
    from control_plane.invariant_evaluator import evaluate_contract
    from control_plane.schemas import validate_job
    from control_plane.supervisor_runner import SupervisorLaunchError, run_supervisor
    from control_plane.workbook_inventory import inspect_workbook
else:
    from .dry_run import simulate_transitions
    from .errors import ContractError
    from .file_router import KNOWN_INTENTS, choose_backend
    from .invariant_evaluator import evaluate_contract
    from .schemas import validate_job
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


def cmd_run(args: argparse.Namespace) -> int:
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
        run_result = run_supervisor(manifest_path, events_path, result_path, args.hard_timeout_seconds)
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

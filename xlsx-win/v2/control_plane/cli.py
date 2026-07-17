#!/usr/bin/env python3
"""xlsx-win v2 control-plane CLI.

`validate` schema-checks a manifest. `dry-run` schema-checks a manifest and
prints the state sequence it would traverse. Neither needs Excel installed,
and neither reads a workbook file: this module never imports pywin32 or
anything that touches COM. That is issue #36's job.

`validate-contract` (issue #38) does read a workbook file -- with openpyxl,
never Excel/COM -- to evaluate a validation contract's declared invariants
against it. It still never imports pywin32 or drives Excel.
"""

from __future__ import annotations

import argparse
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
    from control_plane.invariant_evaluator import evaluate_contract
    from control_plane.schemas import validate_job
else:
    from .dry_run import simulate_transitions
    from .errors import ContractError
    from .invariant_evaluator import evaluate_contract
    from .schemas import validate_job


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

    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

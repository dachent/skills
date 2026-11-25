#!/usr/bin/env python3
"""Candidate xlsx-win control_plane producer for the audit-ledger pivot contract.

Advance the external runtime by landing this module as
``control_plane/audit_ledger_pivot.py``; the financial cell map is supplied by
the job manifest, never recomputed here. Errors are intentionally detail-free
so patient values cannot cross the result boundary.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


def _write_result(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_audit_ledger_pivot(
    job_path: Path | str,
    result_path: Path | str,
) -> dict:
    """Populate a candidate workbook from the validated ledger/job contract."""
    result_path = Path(result_path)
    temporary_path = None
    output_path = None
    paths_validated = False
    try:
        manifest = json.loads(Path(job_path).read_text(encoding="utf-8"))
        paths = manifest["physical_paths"]
        ledger_path = Path(manifest["ledger_path"])
        template_path = Path(paths["template"])
        output_path = Path(paths["candidate"])
        temporary_path = output_path.with_name(output_path.name + ".tmp")
        result_temporary_path = result_path.with_name(result_path.name + ".tmp")
        resolved_paths = [
            str(path.resolve())
            for path in (
                Path(job_path), ledger_path, template_path, output_path, result_path,
                temporary_path, result_temporary_path,
            )
        ]
        if len(set(resolved_paths)) != len(resolved_paths):
            raise ValueError("input and output paths must be distinct")
        paths_validated = True
        if (
            manifest.get("operation") != "replace_audit_ledger_pivot"
            or manifest.get("schema_version") != "2.1"
            or manifest.get("check") != "audit_ledger_pivot_job"
        ):
            raise ValueError("unsupported audit-ledger pivot job")
        expected = manifest["expected"]
        geometry = expected["geometry"]
        contract = manifest["contract"]
        if (
            _sha256(ledger_path) != manifest["ledger_sha256"]
            or _sha256(template_path) != manifest["template_sha256"]
        ):
            raise ValueError("ledger or template identity differs from the job")
        row_count = geometry["row_count"]
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
            raise ValueError("invalid ledger row count")
        expected_headers = list(geometry["headers"])
        required_ref = f"A1:{get_column_letter(len(expected_headers))}{row_count + 1}"
        if geometry["table_ref"] != required_ref:
            raise ValueError("ledger table geometry does not match the job")

        with ledger_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or ())
            rows = list(reader)
        if headers != expected_headers or any(None in row for row in rows):
            raise ValueError("ledger geometry does not match the job")
        if any(row.get(header) is None for row in rows for header in headers):
            raise ValueError("ledger row is missing a required cell")
        if len(rows) != row_count:
            raise ValueError("ledger row count changed after job construction")

        workbook = load_workbook(template_path)
        try:
            for sheet_name in list(workbook.sheetnames):
                if (
                    sheet_name.startswith(contract["pivot_sheet_prefix"])
                    or sheet_name == contract["bindings_sheet"]
                ):
                    workbook.remove(workbook[sheet_name])
            data = workbook[contract["data_sheet"]]
            if data.max_row:
                data.delete_rows(1, data.max_row)
            data.append(headers)
            for row in rows:
                data.append([row.get(header, "") for header in headers])
            table_name = geometry["table_name"]
            table = data.tables.get(table_name)
            if table is None:
                table = Table(displayName=table_name, ref=geometry["table_ref"])
                table.tableStyleInfo = TableStyleInfo(
                    name="TableStyleMedium9", showRowStripes=True)
                data.add_table(table)
            else:
                table.ref = geometry["table_ref"]

            bindings = workbook.create_sheet(contract["bindings_sheet"])
            bindings.append(["source_table", table_name])
            bindings.append(["source_range", geometry["table_ref"]])
            bindings.append(["source_rows", str(geometry["row_count"])])
            bindings.append(["population_rows", str(expected["population"]["rows"])])
            bindings.append([
                "population_counted", str(expected["population"]["counted_patient_ids"])])

            pivot = workbook.create_sheet(contract["pivot_sheet"])
            pivot.append(["kind", "clinic", "week", "channel", "practice", "value"])
            for key, value in sorted(expected["cells"].items()):
                axes = json.loads(key)
                if not isinstance(axes, list) or len(axes) != 5:
                    raise ValueError("invalid pivot cell key")
                pivot.append([*axes, value])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            workbook.save(temporary_path)
            os.replace(temporary_path, output_path)
        finally:
            workbook.close()
        result = {
            "ok": True,
            "status": "PASS",
            "operation": "replace_audit_ledger_pivot",
            "schema_version": "2.1",
            "row_count": len(rows),
            "cell_count": len(expected["cells"]),
        }
        _write_result(result_path, result)
        return result
    except Exception as exc:  # no exception messages: ledger content must not leak
        if paths_validated:
            for path in (temporary_path, output_path, result_temporary_path):
                if path is not None:
                    try:
                        path.unlink()
                    except OSError:
                        pass
        result = {
            "ok": False,
            "status": "FAIL",
            "operation": "replace_audit_ledger_pivot",
            "schema_version": "2.1",
            "error": {"class": type(exc).__name__},
        }
        _write_result(result_path, result)
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run"])
    parser.add_argument("job")
    parser.add_argument("--events")
    parser.add_argument("--result", required=True)
    parser.add_argument("--hard-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--allow-experimental", action="store_true")
    args = parser.parse_args(argv)
    result = replace_audit_ledger_pivot(args.job, args.result)
    return 0 if result["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

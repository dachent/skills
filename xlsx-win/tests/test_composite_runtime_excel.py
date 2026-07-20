from __future__ import annotations

import csv
import gc
import json
import os
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from certification.excel_safety import assert_no_excel_survives, preflight_or_raise
from composite_expected_reference import build_expected_from_seed
from control_plane.composite_runtime import run_composite_job
from control_plane.ooxml_table_transaction import _find_sheet_part
from control_plane.ooxml_verifier import _matrix_hash, sha256_path
from control_plane.table_sidecar import inspect_sidecar


_RUN_EXCEL = os.environ.get("XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS") == "1"
_HEADERS = [
    "FileName",
    "Category",
    "Amount",
    "Value3",
    "CalcA",
    "Value5",
    "Value6",
    "Value7",
    "Value8",
    "Value9",
    "CalcB",
    "Value11",
    "Value12",
    "Value13",
    "Value14",
]
_CALCULATED = {4: "=RC[-2]*2", 10: "=RC[-8]+1"}


def _row(filename: str, category: str, amount: float) -> list[object | None]:
    return [
        filename,
        category,
        amount,
        amount + 10,
        None,
        amount + 20,
        amount + 30,
        amount + 40,
        amount + 50,
        amount + 60,
        None,
        amount + 70,
        amount + 80,
        amount + 90,
        amount + 100,
    ]


def _wait_for_fixture_excel(pid: int) -> None:
    import psutil

    try:
        process = psutil.Process(pid)
        try:
            process.wait(timeout=30)
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    except psutil.NoSuchProcess:
        pass


def _build_workbook(path: Path, rows: list[list[object | None]]) -> list[dict]:
    import pythoncom
    import win32com.client
    import win32process

    preflight_or_raise()
    pythoncom.CoInitialize()
    app = None
    workbook = None
    pid = 0
    reports: list[dict] = []
    try:
        app = win32com.client.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        pid = int(win32process.GetWindowThreadProcessId(int(app.Hwnd))[1])
        workbook = app.Workbooks.Add()
        data = workbook.Worksheets(1)
        data.Name = "Data"
        values = [_HEADERS, *rows]
        data.Range(data.Cells(3, 2), data.Cells(3 + len(rows), 16)).Value = tuple(
            tuple(item) for item in values
        )
        table = data.ListObjects.Add(1, data.Range(data.Cells(3, 2), data.Cells(3 + len(rows), 16)), None, 1)
        table.Name = "Data"
        for index, formula in _CALCULATED.items():
            table.ListColumns(index + 1).DataBodyRange.FormulaR1C1 = formula

        sort = table.Sort
        sort.SortFields.Clear()
        sort.SortFields.Add(
            Key=table.ListColumns("FileName").Range,
            SortOn=0,
            Order=2,
            DataOption=0,
        )
        sort.Header = 1
        sort.Apply()

        cache = workbook.PivotCaches().Create(1, "Data", 6)
        report_specs = [
            ("PivotCategoryAmount", "Category", "Amount", "Sum of Amount"),
            ("PivotFileAmount", "FileName", "Amount", "Sum of Amount"),
            ("PivotCategoryValue", "Category", "Value3", "Sum of Value3"),
        ]
        for sheet_name, row_field, value_field, caption in report_specs:
            sheet = workbook.Worksheets.Add()
            sheet.Name = sheet_name
            pivot_name = f"{sheet_name}Report"
            pivot = cache.CreatePivotTable(sheet.Range("A3"), pivot_name)
            pivot.PivotFields(row_field).Orientation = 1
            pivot.AddDataField(pivot.PivotFields(value_field), caption, -4157)
            pivot.RefreshTable()
            reports.append(
                {
                    "sheet": sheet_name,
                    "name": pivot_name,
                    "range": str(pivot.TableRange2.Address).replace("$", ""),
                }
            )

        app.CalculateFullRebuild()
        workbook.SaveAs(str(path), 51)
        workbook.Close(False)
        workbook = None
        app.Quit()
    finally:
        workbook = None
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        app = None
        gc.collect()
        gc.collect()
        pythoncom.CoUninitialize()
        if pid:
            _wait_for_fixture_excel(pid)
    return reports


def _write_oracle(expected: Path, reports: list[dict], oracle_path: Path) -> None:
    entries = []
    with zipfile.ZipFile(expected, "r") as package:
        workbook = etree.fromstring(package.read("xl/workbook.xml"))
        for report in reports:
            sheet_part = _find_sheet_part(package, workbook, report["sheet"])
            matrix_hash, rows, columns = _matrix_hash(package, sheet_part, report["range"])
            entries.append(report | {"rows": rows, "columns": columns, "matrix_sha256": matrix_hash})
    oracle_path.write_text(
        json.dumps({"schema_version": "1.0", "reports": entries}, indent=2),
        encoding="utf-8",
    )


def _write_source(tmp_path: Path) -> tuple[Path, Path, dict]:
    schema_path = tmp_path / "append.schema.json"
    source_path = tmp_path / "append.csv"
    columns = []
    for index, name in enumerate(_HEADERS):
        calculated = index in _CALCULATED
        is_text = name in {"FileName", "Category"}
        columns.append(
            {
                "id": index + 1,
                "name": name,
                "role": "calculated" if calculated else "writable",
                "logical_type": "text" if is_text else "number",
                "storage_type": "inline_string" if is_text else "number",
                "number_format": None,
            }
        )
    schema_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "encoding": "utf-8",
                "delimiter": ",",
                "quotechar": '"',
                "has_header": True,
                "date_system": "1900",
                "columns": columns,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with source_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(_HEADERS)
        writer.writerow(["gamma", "A", "3", "13", "", "23", "33", "43", "53", "63", "", "73", "83", "93", "103"])
    return source_path, schema_path, inspect_sidecar(source_path, schema_path).to_dict()


def _manifest(seed: Path, output: Path, source: Path, schema: Path, stats: dict, oracle: Path) -> dict:
    columns = []
    for index, name in enumerate(_HEADERS):
        columns.append(
            {
                "name": name,
                "role": "calculated" if index in _CALCULATED else "writable",
                "logical_type": "text" if name in {"FileName", "Category"} else "number",
            }
        )
    return {
        "schema_version": "2.1",
        "idempotency_key": "coordinator-real-excel-append",
        "steps": [
            {
                "type": "append_table_rows",
                "operation_version": "1.0",
                "workbook_path": str(seed),
                "workbook_sha256": sha256_path(seed),
                "output_path": str(output),
                "table": {
                    "sheet": "Data",
                    "name": "Data",
                    "existing_body_rows": 2,
                    "final_body_rows": 3,
                    "column_count": 15,
                    "writable_runs": 3,
                    "columns": columns,
                    "filters": "none",
                    "totals": False,
                    "saved_sort": {
                        "column": "FileName",
                        "direction": "descending",
                        "behavior": "preserve_descriptor_do_not_reapply",
                    },
                },
                "source": stats | {"path": str(source), "schema_path": str(schema)},
                "dependent_pivots": {
                    "mode": "linked_only",
                    "profile": "worksheet_simple_v1",
                    "cache_count": 1,
                    "report_count": 3,
                    "oracle_path": str(oracle),
                    "oracle_sha256": sha256_path(oracle),
                },
                "capability_profile": "excel64_table_pivot_append_saved_sort_v1",
            }
        ],
        "timeouts": {
            "preflight_seconds": 120,
            "write_seconds": 300,
            "calculation_seconds": 300,
            "pivot_seconds": 300,
            "save_seconds": 300,
            "reopen_seconds": 300,
            "validation_seconds": 300,
            "close_seconds": 120,
            "whole_job_seconds": 1800,
            "inactivity_seconds": 300,
            "shutdown_seconds": 30,
        },
    }


@pytest.mark.skipif(not _RUN_EXCEL, reason="real Excel integration requires explicit opt-in")
def test_coordinator_append_runs_streaming_native_verifier_and_publication(tmp_path) -> None:
    seed = tmp_path / "seed.xlsx"
    expected = tmp_path / "expected.xlsx"
    output = tmp_path / "output.xlsx"
    oracle = tmp_path / "oracle.json"
    events = tmp_path / "events.jsonl"
    result_path = tmp_path / "result.json"

    _build_workbook(seed, [_row("omega", "B", 1), _row("alpha", "A", 2)])
    reports = build_expected_from_seed(seed, expected, _row("gamma", "A", 3), _CALCULATED)
    _write_oracle(expected, reports, oracle)
    source, schema, stats = _write_source(tmp_path)
    manifest = _manifest(seed, output, source, schema, stats, oracle)
    seed_hash = sha256_path(seed)

    preflight_or_raise()
    try:
        result, exit_code = run_composite_job(
            manifest,
            events,
            result_path,
            requested_hard_timeout_seconds=1900,
            allow_experimental=True,
        )
    finally:
        assert_no_excel_survives(max_wait_seconds=60)

    assert exit_code == 0, json.dumps(result, indent=2)
    assert result["ok"] is True
    assert result["publication"]["status"] == "published"
    assert all(result["cleanup"].values())
    assert sha256_path(seed) == seed_hash
    assert sha256_path(output) == result["bindings"]["staged_output"]
    evidence_dir = result_path.with_suffix(result_path.suffix + ".evidence")
    evidence_index = json.loads((evidence_dir / "evidence-index.json").read_text(encoding="utf-8"))
    assert {
        "candidate-plan.json",
        "fresh-reopen-verification.json",
        "intermediate-package-manifest.json",
        "native-result.json",
        "supervisor-launch.json",
        "telemetry.jsonl",
        "worker-events.jsonl",
    } <= set(evidence_index["files"])

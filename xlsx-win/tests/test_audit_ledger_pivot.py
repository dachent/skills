import csv
import hashlib
import json
from pathlib import Path

from openpyxl import Workbook, load_workbook
import pytest

from control_plane.audit_ledger_pivot import replace_audit_ledger_pivot


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    template = tmp_path / "template.xlsx"
    workbook = Workbook()
    data = workbook.active
    data.title = "audit_ledger"
    data.append(["clinic", "patient_id"])
    workbook.save(template)
    ledger = tmp_path / "ledger.csv"
    with ledger.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["clinic", "patient_id"])
        writer.writerow(["IVFMD", "SYN-1"])
    job = tmp_path / "job.json"
    job.write_text(json.dumps({
        "operation": "replace_audit_ledger_pivot",
        "schema_version": "2.1",
        "check": "audit_ledger_pivot_job",
        "contract": {
            "data_sheet": "audit_ledger",
            "pivot_sheet": "summary_pivot_ByClinic",
            "pivot_sheet_prefix": "summary_pivot_",
            "bindings_sheet": "_pivot_bindings",
        },
        "ledger_path": str(ledger),
        "ledger_sha256": _sha256(ledger),
        "template_sha256": _sha256(template),
        "expected": {
            "geometry": {
                "headers": ["clinic", "patient_id"],
                "row_count": 1,
                "table_name": "audit_ledger_data",
                "table_ref": "A1:B2",
            },
            "population": {"rows": 1, "counted_patient_ids": 1},
            "cells": {
                json.dumps(["weekly", "IVFMD", "2026-11-07", "channel", "practice"]): 1,
            },
        },
        "physical_paths": {
            "template": str(template),
            "candidate": str(tmp_path / "candidate.xlsx"),
        },
    }), encoding="utf-8")
    return job, tmp_path / "result.json"


def test_producer_writes_pivot_cells_table_and_bindings(tmp_path):
    job, result_path = _fixture(tmp_path)

    result = replace_audit_ledger_pivot(job, result_path)

    assert result == {
        "ok": True,
        "status": "PASS",
        "operation": "replace_audit_ledger_pivot",
        "schema_version": "2.1",
        "row_count": 1,
        "cell_count": 1,
    }
    workbook = load_workbook(tmp_path / "candidate.xlsx")
    try:
        data = workbook["audit_ledger"]
        assert data.tables["audit_ledger_data"].ref == "A1:B2"
        pivot = workbook["summary_pivot_ByClinic"]
        assert list(pivot.values) == [
            ("kind", "clinic", "week", "channel", "practice", "value"),
            ("weekly", "IVFMD", "2026-11-07", "channel", "practice", 1),
        ]
        bindings = list(workbook["_pivot_bindings"].values)
        assert bindings == [
            ("source_table", "audit_ledger_data"),
            ("source_range", "A1:B2"),
            ("source_rows", "1"),
            ("population_rows", "1"),
            ("population_counted", "1"),
        ]
    finally:
        workbook.close()
    assert json.loads(result_path.read_text(encoding="utf-8"))["ok"] is True


def test_tampered_ledger_row_count_fails_without_candidate(tmp_path):
    job, result_path = _fixture(tmp_path)
    with (tmp_path / "ledger.csv").open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(["Boca", "SYN-2"])
    document = json.loads(job.read_text(encoding="utf-8"))
    document["ledger_sha256"] = _sha256(tmp_path / "ledger.csv")
    job.write_text(json.dumps(document), encoding="utf-8")

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert result["status"] == "FAIL"
    assert not (tmp_path / "candidate.xlsx").exists()
    assert json.loads(result_path.read_text(encoding="utf-8"))["ok"] is False


def test_invalid_pivot_key_fails_without_candidate(tmp_path):
    job, result_path = _fixture(tmp_path)
    document = json.loads(job.read_text(encoding="utf-8"))
    document["expected"]["cells"] = {json.dumps(["too", "short"]): 1}
    job.write_text(json.dumps(document), encoding="utf-8")

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not (tmp_path / "candidate.xlsx").exists()


def test_same_geometry_ledger_tampering_fails_without_candidate(tmp_path):
    job, result_path = _fixture(tmp_path)
    with (tmp_path / "ledger.csv").open("r+", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
        rows[1][1] = "SYN-TAMPERED"
        handle.seek(0)
        handle.truncate()
        csv.writer(handle).writerows(rows)

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not (tmp_path / "candidate.xlsx").exists()


def test_template_replacement_fails_without_candidate(tmp_path):
    job, result_path = _fixture(tmp_path)
    replacement = Workbook()
    replacement.active.title = "audit_ledger"
    replacement.active.append(["clinic", "patient_id"])
    replacement.active["A1"] = "changed-template"
    replacement.save(tmp_path / "template.xlsx")

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not (tmp_path / "candidate.xlsx").exists()


def test_truncated_row_missing_cell_fails_without_candidate(tmp_path):
    job, result_path = _fixture(tmp_path)
    with (tmp_path / "ledger.csv").open("r+", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
        rows[1] = [rows[1][0]]
        handle.seek(0)
        handle.truncate()
        csv.writer(handle).writerows(rows)
    document = json.loads(job.read_text(encoding="utf-8"))
    document["ledger_sha256"] = _sha256(tmp_path / "ledger.csv")
    job.write_text(json.dumps(document), encoding="utf-8")

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not (tmp_path / "candidate.xlsx").exists()


def test_incorrect_table_ref_fails_without_candidate(tmp_path):
    job, result_path = _fixture(tmp_path)
    document = json.loads(job.read_text(encoding="utf-8"))
    document["expected"]["geometry"]["table_ref"] = "A1:B3"
    job.write_text(json.dumps(document), encoding="utf-8")

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not (tmp_path / "candidate.xlsx").exists()


@pytest.mark.parametrize("collision", ["job", "ledger", "template", "result"])
def test_candidate_collision_fails_without_overwriting_input(tmp_path, collision):
    job, result_path = _fixture(tmp_path)
    document = json.loads(job.read_text(encoding="utf-8"))
    target = {
        "job": job,
        "ledger": tmp_path / "ledger.csv",
        "template": tmp_path / "template.xlsx",
        "result": result_path,
    }[collision]
    document["physical_paths"]["candidate"] = str(target)
    job.write_text(json.dumps(document), encoding="utf-8")
    before = {path: _sha256(path) for path in (job, tmp_path / "ledger.csv", tmp_path / "template.xlsx")}

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert {path: _sha256(path) for path in before} == before


def test_derived_temporary_path_collision_preserves_input(tmp_path):
    job, result_path = _fixture(tmp_path)
    ledger = tmp_path / "candidate.xlsx.tmp"
    ledger.write_bytes((tmp_path / "ledger.csv").read_bytes())
    document = json.loads(job.read_text(encoding="utf-8"))
    document["ledger_path"] = str(ledger)
    document["ledger_sha256"] = _sha256(ledger)
    job.write_text(json.dumps(document), encoding="utf-8")
    before = _sha256(ledger)

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert _sha256(ledger) == before


def test_preexisting_candidate_is_removed_on_refusal(tmp_path):
    job, result_path = _fixture(tmp_path)
    candidate = tmp_path / "candidate.xlsx"
    candidate.write_bytes(b"stale candidate")
    document = json.loads(job.read_text(encoding="utf-8"))
    document["expected"]["geometry"]["table_ref"] = "A1:B3"
    job.write_text(json.dumps(document), encoding="utf-8")

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not candidate.exists()


def test_save_failure_removes_partial_and_stale_candidates(tmp_path, monkeypatch):
    job, result_path = _fixture(tmp_path)
    candidate = tmp_path / "candidate.xlsx"
    candidate.write_bytes(b"stale candidate")

    def fail_save(_self, path):
        Path(path).write_bytes(b"partial workbook")
        raise OSError("simulated save failure")

    monkeypatch.setattr(Workbook, "save", fail_save)

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not candidate.exists()
    assert not (tmp_path / "candidate.xlsx.tmp").exists()


def test_result_schema_is_exact_and_contains_no_patient_sentinel(tmp_path):
    job, result_path = _fixture(tmp_path)
    with (tmp_path / "ledger.csv").open("r+", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
        rows[1][1] = "SYN-PATIENT-SENTINEL"
        handle.seek(0)
        handle.truncate()
        csv.writer(handle).writerows(rows)

    result = replace_audit_ledger_pivot(job, result_path)
    document = json.loads(result_path.read_text(encoding="utf-8"))

    assert result == document == {
        "ok": False,
        "status": "FAIL",
        "operation": "replace_audit_ledger_pivot",
        "schema_version": "2.1",
        "error": {"class": "ValueError"},
    }
    assert "SYN-PATIENT-SENTINEL" not in result_path.read_text(encoding="utf-8")


def test_invalid_job_shapes_fail_without_candidate(tmp_path):
    job, result_path = _fixture(tmp_path)
    candidate = tmp_path / "candidate.xlsx"
    candidate.write_bytes(b"stale candidate")
    document = json.loads(job.read_text(encoding="utf-8"))
    document["operation"] = "not_the_pivot"
    job.write_text(json.dumps(document), encoding="utf-8")

    result = replace_audit_ledger_pivot(job, result_path)

    assert result["ok"] is False
    assert not candidate.exists()

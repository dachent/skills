from __future__ import annotations

import json
from types import SimpleNamespace

from control_plane import composite_runtime
from control_plane.supervisor_runner import SupervisorLaunchError
from control_plane.worker_event_sink import WorkerEventSink
from test_capabilities import _production_append


def test_row_progress_sink_emits_actual_count_milestones(tmp_path) -> None:
    events_path = tmp_path / "events.jsonl"

    with WorkerEventSink(events_path, run_id="python-run", report_every=2) as sink:
        sink.start(3)
        sink.row_written(1, 3)
        sink.row_written(2, 3)
        sink.row_written(3, 3)

    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert [(event["rows_done"], event["rows_total"]) for event in events] == [(0, 3), (1, 3), (2, 3), (3, 3)]
    assert all(event["run_id"] == "python-run" for event in events)
    assert all(event["phase"] == "APPLYING_EDITS" for event in events)
    assert all(event["timestamp"].endswith("+00:00") for event in events)
    assert "excel_pid" not in events[-1]


def test_composite_runtime_streams_rows_then_hands_off_append_mode(tmp_path, monkeypatch) -> None:
    manifest = _production_append()
    operation = manifest["steps"][0]
    operation["workbook_path"] = str(tmp_path / "seed.xlsx")
    operation["workbook_sha256"] = "0" * 64
    operation["output_path"] = str(tmp_path / "output.xlsx")
    operation["source"]["row_count"] = 1
    operation["dependent_pivots"]["oracle_sha256"] = "0" * 64
    events_path = tmp_path / "events.jsonl"
    result_path = tmp_path / "result.json"
    captured = {}

    monkeypatch.setattr(composite_runtime, "load_sidecar_schema", lambda path: {"date_system": "1900"})
    monkeypatch.setattr(composite_runtime, "detect_environment", lambda date_system: {})
    monkeypatch.setattr(
        composite_runtime,
        "admit_manifest",
        lambda *args, **kwargs: {"profile": {"id": "test", "candidate": "test"}, "sha256": "a" * 64},
    )
    monkeypatch.setattr(composite_runtime, "_build_commit", lambda: "b" * 40)
    monkeypatch.setattr(composite_runtime, "sha256_path", lambda path: "0" * 64)
    monkeypatch.setattr(
        composite_runtime,
        "inspect_sidecar",
        lambda *args: SimpleNamespace(to_dict=lambda: {"row_count": 1}),
    )
    monkeypatch.setattr(composite_runtime, "verify_source_binding", lambda *args: None)

    def stage_copy(path):
        staging = tmp_path / "staging"
        staging.mkdir()
        return staging / "seed.xlsx"

    def rewrite(*args, row_progress=None):
        row_progress(1, 1)
        return {"changed_parts": []}

    def launch(job_path, events_path, result_path, hard_timeout, extra_env=None):
        captured["extra_env"] = extra_env
        with events_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"run_id": "native", "phase": "COMPOSITE_PREFLIGHT"}) + "\n")
        raise SupervisorLaunchError("stop after the event handoff")

    monkeypatch.setattr(composite_runtime, "stage_copy", stage_copy)
    monkeypatch.setattr(composite_runtime, "preflight_package", lambda *args: object())
    monkeypatch.setattr(composite_runtime, "rewrite_intermediate_package", rewrite)
    monkeypatch.setattr(composite_runtime, "run_supervisor", launch)

    result, exit_code = composite_runtime.run_composite_job(manifest, events_path, result_path, 30)

    assert exit_code == 1
    assert result["ok"] is False
    assert "extra_env" in captured, json.dumps(result, indent=2)
    assert captured["extra_env"] == {"XLSXWIN_APPEND_EVENTS": "1"}
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert [(event["rows_done"], event["rows_total"]) for event in events[:-1]] == [(0, 1), (1, 1)]
    assert events[-1]["run_id"] == "native"

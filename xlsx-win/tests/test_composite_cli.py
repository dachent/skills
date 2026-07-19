from __future__ import annotations

import argparse
import json

from control_plane import cli
from test_capabilities import _production_append


def test_capabilities_command_is_machine_readable(capsys) -> None:
    exit_code = cli.main(["capabilities", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert {item["id"] for item in payload["capabilities"]} == {
        "excel64_table_pivot_append_saved_sort_v1",
        "excel64_table_pivot_replace_v1",
    }
    assert all(item["status"] == "experimental" for item in payload["capabilities"])


def test_composite_run_fails_before_staging_or_supervisor(monkeypatch, tmp_path, capsys) -> None:
    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(json.dumps(_production_append()), encoding="utf-8")
    monkeypatch.setattr(cli, "_stage_job_for_run", lambda _job: (_ for _ in ()).throw(AssertionError("staged")))
    monkeypatch.setattr(cli, "run_supervisor", lambda *_args: (_ for _ in ()).throw(AssertionError("ran")))
    args = argparse.Namespace(
        manifest=str(manifest_path),
        events=None,
        result=None,
        hard_timeout_seconds=10.0,
    )

    exit_code = cli.cmd_run(args)
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["error"]["code"] == "COMPOSITE_RUNTIME_UNAVAILABLE"
    assert payload["error"]["details"]["mutation_started"] is False

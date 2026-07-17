"""Audit manifest tests (issue #38).

Covers: build_audit_manifest hashes input/output content, links a
validation contract's path/hash when one was provided, carries the
(redacted) invariant results, and refuses to build a manifest around a
missing input/output/contract file. Also covers the redaction pass: an
invariant message that looks like a connection string must not pass
through verbatim.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from control_plane.audit_manifest import build_audit_manifest
from control_plane.errors import ContractError


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_build_audit_manifest_hashes_input_and_output(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"input-bytes")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"output-bytes")

    manifest = build_audit_manifest(
        run_id="run-1",
        input_path=input_path,
        output_path=output_path,
        contract_path=None,
        invariant_results=[{"name": "required_sheet:Data", "passed": True}],
    )

    assert manifest["schema_version"] == "1.0"
    assert manifest["run_id"] == "run-1"
    assert manifest["input_sha256"] == _sha256(b"input-bytes")
    assert manifest["output_sha256"] == _sha256(b"output-bytes")
    assert manifest["input_path"] == str(input_path)
    assert manifest["output_path"] == str(output_path)
    assert "contract_path" not in manifest
    assert "contract_sha256" not in manifest
    assert manifest["invariant_results"] == [{"name": "required_sheet:Data", "passed": True}]
    assert "generated_at" in manifest


def test_build_audit_manifest_includes_contract_hash_when_provided(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps({"required_sheets": ["Data"]}))

    manifest = build_audit_manifest(
        run_id="run-2",
        input_path=input_path,
        output_path=output_path,
        contract_path=contract_path,
        invariant_results=[],
    )

    assert manifest["contract_path"] == str(contract_path)
    assert manifest["contract_sha256"] == _sha256(contract_path.read_bytes())


def test_build_audit_manifest_raises_when_input_is_missing(tmp_path) -> None:
    with pytest.raises(ContractError) as excinfo:
        build_audit_manifest(
            run_id="run-3",
            input_path=tmp_path / "does_not_exist.xlsx",
            output_path=tmp_path / "out.xlsx",
            contract_path=None,
            invariant_results=[],
        )

    assert excinfo.value.code == "AUDIT_SOURCE_MISSING"


def test_build_audit_manifest_raises_when_output_is_missing(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")

    with pytest.raises(ContractError) as excinfo:
        build_audit_manifest(
            run_id="run-3b",
            input_path=input_path,
            output_path=tmp_path / "does_not_exist.xlsx",
            contract_path=None,
            invariant_results=[],
        )

    assert excinfo.value.code == "AUDIT_SOURCE_MISSING"


def test_build_audit_manifest_raises_when_contract_path_given_but_missing(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")

    with pytest.raises(ContractError) as excinfo:
        build_audit_manifest(
            run_id="run-3c",
            input_path=input_path,
            output_path=output_path,
            contract_path=tmp_path / "does_not_exist.json",
            invariant_results=[],
        )

    assert excinfo.value.code == "AUDIT_SOURCE_MISSING"


def test_build_audit_manifest_redacts_connection_string_shaped_message(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")
    secret_message = (
        "Refresh failed: Provider=SQLOLEDB;Data Source=db01;User ID=svc;Password=hunter2;"
    )

    manifest = build_audit_manifest(
        run_id="run-4",
        input_path=input_path,
        output_path=output_path,
        contract_path=None,
        invariant_results=[
            {"name": "connection:SalesDB", "passed": False, "message": secret_message}
        ],
    )

    assert manifest["invariant_results"][0]["message"] == "[redacted]"
    assert "hunter2" not in json.dumps(manifest)


def test_build_audit_manifest_redacts_ado_net_style_connection_string(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")
    secret_message = (
        "Refresh failed: Server=myServerAddress;Database=myDataBase;"
        "User Id=myUsername;Password=myPassword;"
    )

    manifest = build_audit_manifest(
        run_id="run-4b",
        input_path=input_path,
        output_path=output_path,
        contract_path=None,
        invariant_results=[
            {"name": "connection:SalesDB", "passed": False, "message": secret_message}
        ],
    )

    assert manifest["invariant_results"][0]["message"] == "[redacted]"
    assert "myPassword" not in json.dumps(manifest)


def test_build_audit_manifest_redacts_odbc_style_connection_string(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")
    secret_message = (
        "Connection failed: Driver={SQL Server};Server=10.0.0.5;"
        "Uid=svc_user;Pwd=Sup3rSecret!;"
    )

    manifest = build_audit_manifest(
        run_id="run-4c",
        input_path=input_path,
        output_path=output_path,
        contract_path=None,
        invariant_results=[
            {"name": "connection:SalesDB", "passed": False, "message": secret_message}
        ],
    )

    assert manifest["invariant_results"][0]["message"] == "[redacted]"
    assert "Sup3rSecret!" not in json.dumps(manifest)


def test_build_audit_manifest_redacts_a_url_with_embedded_credentials(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")

    manifest = build_audit_manifest(
        run_id="run-5",
        input_path=input_path,
        output_path=output_path,
        contract_path=None,
        invariant_results=[
            {
                "name": "connection:Api",
                "passed": False,
                "message": "GET https://svcuser:s3cr3tpass@api.example.com/data failed",
            }
        ],
    )

    assert manifest["invariant_results"][0]["message"] == "[redacted]"


def test_build_audit_manifest_leaves_ordinary_messages_untouched(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")
    ordinary_message = "Expected at least 10 row(s), found 3."

    manifest = build_audit_manifest(
        run_id="run-6",
        input_path=input_path,
        output_path=output_path,
        contract_path=None,
        invariant_results=[
            {"name": "min_row_count:Data", "passed": False, "message": ordinary_message}
        ],
    )

    assert manifest["invariant_results"][0]["message"] == ordinary_message


def test_build_audit_manifest_validates_against_its_own_schema(tmp_path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_bytes(b"in")
    output_path = tmp_path / "output.xlsx"
    output_path.write_bytes(b"out")

    manifest = build_audit_manifest(
        run_id="run-7",
        input_path=input_path,
        output_path=output_path,
        contract_path=None,
        invariant_results=[],
    )

    # additionalProperties: false in the schema means build_audit_manifest
    # itself already proved this via validate_audit_manifest(); this just
    # pins the exact key set as a regression guard.
    assert set(manifest.keys()) == {
        "schema_version",
        "run_id",
        "generated_at",
        "input_path",
        "input_sha256",
        "output_path",
        "output_sha256",
        "invariant_results",
    }

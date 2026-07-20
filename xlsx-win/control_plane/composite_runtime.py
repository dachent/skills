"""End-to-end coordinator for the v2.1 composite Table transaction."""

from __future__ import annotations

import copy
import ctypes
import hashlib
import json
import locale
import os
import platform
import shutil
import subprocess
import uuid
import winreg
from pathlib import Path

from .capabilities import admit_manifest
from .composite_evidence import write_evidence_index
from .composite_safety import AtomicPublication, cleanup_from_native_result, write_json_atomic
from .errors import ContractError
from .ooxml_table_transaction import preflight_package, rewrite_intermediate_package
from .ooxml_verifier import sha256_path, verify_final_package
from .result_contract import (
    build_composite_result,
    compute_ok,
    publication_eligible,
    required_composite_invariants,
)
from .schemas import validate_result
from .staging import stage_copy
from .supervisor_runner import SupervisorLaunchError, run_supervisor
from .table_sidecar import inspect_sidecar, load_sidecar_schema, verify_source_binding


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_excel_build() -> tuple[str, str]:
    key_path = r"SOFTWARE\Microsoft\Office\ClickToRun\Configuration"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            return str(winreg.QueryValueEx(key, "VersionToReport")[0]), str(winreg.QueryValueEx(key, "Platform")[0])
    except OSError as exc:
        raise ContractError("CAPABILITY_PROFILE_INVALID", "Cannot read the installed Excel build/bitness.", {}) from exc


def _read_windows_locale() -> str:
    buffer = ctypes.create_unicode_buffer(85)
    length = ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
    if length <= 0 or not buffer.value:
        raise ContractError(
            "CAPABILITY_PROFILE_INVALID",
            "Cannot read the current Windows user locale name.",
            {},
        )
    return buffer.value


def _dotnet_runtime() -> str:
    completed = subprocess.run(
        ["dotnet", "--list-runtimes"], capture_output=True, text=True, check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    versions = [line.split()[1] for line in completed.stdout.splitlines() if line.startswith("Microsoft.NETCore.App ")]
    if not versions:
        raise ContractError("CAPABILITY_PROFILE_INVALID", "No Microsoft.NETCore.App runtime is installed.", {})
    return versions[-1]


def detect_environment(date_system: str) -> dict:
    excel_build, office_bitness = _read_excel_build()
    windows_version = platform.version()
    return {
        "windows_build": windows_version,
        "excel_build": excel_build,
        "office_bitness": office_bitness,
        "dotnet_runtime": _dotnet_runtime(),
        "locale": _read_windows_locale(),
        "date_system": date_system,
    }


def _build_commit() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    commit = completed.stdout.strip()
    if len(commit) != 40:
        raise ContractError("RESULT_PROOF_INVALID", "Runtime build commit is not a full Git object id.", {"value": commit})
    return commit


def _write_json(path: Path, value: object) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def _raise_for_native_outcome(native_result: dict, launch_exit_code: int) -> None:
    """Reject inconsistent native results and preserve trustworthy failures."""

    recomputed = compute_ok(native_result["steps"], native_result["invariants"])
    expected_exit_code = 0 if recomputed else 1
    if (
        native_result.get("ok") is not recomputed
        or (native_result.get("final_state") == "SUCCEEDED") is not recomputed
        or launch_exit_code != expected_exit_code
    ):
        raise ContractError(
            "RESULT_PROOF_INVALID",
            "Native supervisor result is internally inconsistent.",
            {"result": native_result, "launch_exit_code": launch_exit_code},
        )
    if recomputed:
        return

    for step in native_result["steps"]:
        error = step.get("error") if isinstance(step, dict) else None
        if step.get("status") != "failed" or not isinstance(error, dict):
            continue
        if error.get("code") == "OWNED_PROCESS_CLEANUP_REQUIRED":
            raise ContractError(
                error["code"],
                str(error.get("message", step.get("message", "Native supervisor failed."))),
                error.get("details", {}),
            )

    raise ContractError(
        "RESULT_PROOF_INVALID",
        "Native supervisor returned a trustworthy failure without a recognized structured error.",
        {"result": native_result},
    )


def _failure_result(
    manifest: dict,
    evidence_dir: Path,
    message: str,
    *,
    cleanup: dict | None = None,
    profile: dict | None = None,
    error: dict | None = None,
) -> dict:
    operation = manifest["steps"][0]
    failure_document = {"message": message, "operation": operation["type"]}
    if error is not None:
        failure_document["error"] = error
    failure_hash = _write_json(evidence_dir / "failure.json", failure_document)
    evidence_hash = write_evidence_index(evidence_dir, status="failed")
    invariants = [
        {"name": name, "version": "1.0", "passed": False, "evidence_sha256": failure_hash, "message": message}
        for name in sorted(required_composite_invariants(operation["type"]))
    ]
    zeros = "0" * 64
    source = operation["source"]
    return build_composite_result(
        run_id=f"composite-failed-{uuid.uuid4().hex}",
        idempotency_key=manifest["idempotency_key"],
        operation=operation["type"],
        final_state="FAILED",
        steps=[{"step_index": 0, "type": operation["type"], "status": "failed", "message": message}],
        invariants=invariants,
        bindings={
            "workbook": operation.get("workbook_sha256", zeros),
            "source": source.get("raw_sha256", zeros),
            "schema": source.get("schema_sha256", zeros),
            "plan": zeros,
            "staged_output": zeros,
            "verifier": zeros,
            "evidence": evidence_hash,
        },
        profile=profile or {"id": operation["capability_profile"], "sha256": zeros, "build_commit": "0" * 40},
        cleanup=cleanup or {
            "owned_processes_zero": False,
            "worker_exit_verified": False,
            "excel_exit_verified": False,
            "termination_verified": False,
        },
        publication={"status": "not_attempted", "atomic": False, "staged_sha256": zeros, "destination_sha256": zeros},
    )


def run_composite_job(
    manifest: dict,
    events_path: Path,
    result_path: Path,
    requested_hard_timeout_seconds: float,
    *,
    allow_experimental: bool = False,
) -> tuple[dict, int]:
    operation = manifest["steps"][0]
    output_destination = Path(operation["output_path"])
    evidence_dir = result_path.with_suffix(result_path.suffix + ".evidence")
    if evidence_dir.exists():
        raise ContractError("STAGING_INVALID", "Evidence directory already exists; refusing to mix runs.", {"path": str(evidence_dir)})
    evidence_dir.mkdir(parents=True)
    original_destination_hash = sha256_path(output_destination) if output_destination.is_file() else None
    profile_binding = None
    staging_dir = None
    cleanup = {
        "owned_processes_zero": False,
        "worker_exit_verified": False,
        "excel_exit_verified": False,
        "termination_verified": False,
    }
    try:
        sidecar_schema = load_sidecar_schema(operation["source"]["schema_path"])
        environment = detect_environment(sidecar_schema["date_system"])
        profile_binding = admit_manifest(
            manifest,
            environment=environment,
            required_status=None if allow_experimental else "beta",
        )
        profile_doc = {
            "id": profile_binding["profile"]["id"],
            "sha256": profile_binding["sha256"],
            "build_commit": _build_commit(),
        }

        seed_path = Path(operation["workbook_path"])
        seed_hash = sha256_path(seed_path)
        if seed_hash.lower() != operation["workbook_sha256"].lower():
            raise ContractError("SOURCE_BINDING_MISMATCH", "Seed workbook hash differs from the manifest.", {})
        pivot_spec = operation["dependent_pivots"]
        oracle_path = pivot_spec.get("oracle_path")
        oracle_sha256 = pivot_spec.get("oracle_sha256")
        if bool(oracle_path) != bool(oracle_sha256):
            raise ContractError("SOURCE_BINDING_MISMATCH", "Pivot oracle path/hash must be supplied together.", {})
        if oracle_path:
            observed_oracle_sha256 = sha256_path(oracle_path)
            if observed_oracle_sha256.lower() != oracle_sha256.lower():
                raise ContractError("SOURCE_BINDING_MISMATCH", "Pivot oracle hash differs from the manifest.", {})
            oracle_sha256 = observed_oracle_sha256.lower()
        stats = inspect_sidecar(operation["source"]["path"], operation["source"]["schema_path"])
        verify_source_binding(operation, stats)

        staged_seed = stage_copy(seed_path)
        staging_dir = staged_seed.parent
        intermediate = staging_dir / "intermediate.xlsx"
        native_output = staging_dir / "native-output.xlsx"
        original_preflight = preflight_package(staged_seed, operation, sidecar_schema)
        package_manifest = rewrite_intermediate_package(staged_seed, intermediate, operation, sidecar_schema, original_preflight)
        package_manifest_hash = _write_json(evidence_dir / "intermediate-package-manifest.json", package_manifest)

        plan = {
            "schema_version": "1.0",
            "candidate": profile_binding["profile"]["candidate"],
            "operation": operation["type"],
            "profile_sha256": profile_binding["sha256"],
            "seed_sha256": seed_hash,
            "source": stats.to_dict(),
            "oracle_sha256": oracle_sha256 or "0" * 64,
            "package_manifest_sha256": package_manifest_hash,
            "output_destination": str(output_destination),
        }
        plan_hash = _write_json(evidence_dir / "candidate-plan.json", plan)

        native_manifest = copy.deepcopy(manifest)
        native_operation = native_manifest["steps"][0]
        native_operation["workbook_path"] = str(intermediate)
        native_operation["output_path"] = str(native_output)
        native_manifest_path = staging_dir / "native-job.json"
        native_manifest_path.write_text(json.dumps(native_manifest), encoding="utf-8")
        derived_timeout = manifest["timeouts"]["whole_job_seconds"] + manifest["timeouts"]["shutdown_seconds"] + 30
        hard_timeout = max(float(requested_hard_timeout_seconds), float(derived_timeout))
        native_result_path = staging_dir / "native-result.json"
        try:
            launch = run_supervisor(native_manifest_path, events_path, native_result_path, hard_timeout)
        except (FileNotFoundError, SupervisorLaunchError) as exc:
            raise ContractError("SUPERVISOR_INVOCATION_FAILED", str(exc), {}) from exc
        _write_json(
            evidence_dir / "supervisor-launch.json",
            {
                "exit_code": launch.exit_code,
                "elapsed_seconds": launch.elapsed_seconds,
                "stdout": launch.stdout,
                "stderr": launch.stderr,
            },
        )
        if events_path.is_file():
            shutil.copy2(events_path, evidence_dir / "worker-events.jsonl")
        telemetry_source = Path(str(events_path) + ".telemetry.jsonl")
        if telemetry_source.is_file():
            shutil.copy2(telemetry_source, evidence_dir / "telemetry.jsonl")
        if not native_result_path.is_file():
            raise ContractError("RESULT_PROOF_INVALID", "Native supervisor wrote no result document.", {})
        native_result = json.loads(native_result_path.read_text(encoding="utf-8"))
        _write_json(evidence_dir / "native-result.json", native_result)
        cleanup = cleanup_from_native_result(native_result)
        validate_result(native_result)
        _raise_for_native_outcome(native_result, launch.exit_code)
        if not all(cleanup.values()):
            raise ContractError("RESULT_PROOF_INVALID", "Native supervisor did not attest complete owned-process cleanup.", {})
        worker_events = evidence_dir / "worker-events.jsonl"
        if not worker_events.is_file() or worker_events.stat().st_size == 0:
            raise ContractError("RESULT_PROOF_INVALID", "Worker events are missing.", {})
        telemetry_evidence = evidence_dir / "telemetry.jsonl"
        if not telemetry_evidence.is_file() or telemetry_evidence.stat().st_size == 0:
            raise ContractError("RESULT_PROOF_INVALID", "Supervisor telemetry is missing.", {})

        verification = verify_final_package(
            staged_seed, native_output, operation, sidecar_schema, original_preflight, seed_hash
        )
        verification_hash = _write_json(evidence_dir / "fresh-reopen-verification.json", verification)
        staged_output_hash = sha256_path(native_output)
        if staged_output_hash != verification["output_sha256"]:
            raise ContractError("RESULT_PROOF_INVALID", "Staged output changed after verification.", {})

        evidence_hash = write_evidence_index(
            evidence_dir,
            status="succeeded",
            metadata={
                "build_commit": profile_doc["build_commit"],
                "environment": environment,
                "profile": profile_binding["profile"],
            },
        )
        invariant_evidence = {
            name: verification_hash for name in required_composite_invariants(operation["type"])
        }
        for name in {"source_hash_bound", "schema_hash_bound"}:
            invariant_evidence[name] = plan_hash
        invariant_evidence["plan_hash_bound"] = plan_hash
        invariant_evidence["non_allowlisted_parts_unchanged"] = package_manifest_hash
        invariants = [
            {"name": name, "version": "1.0", "passed": True, "evidence_sha256": invariant_evidence[name]}
            for name in sorted(required_composite_invariants(operation["type"]))
        ]
        bindings = {
            "workbook": seed_hash,
            "source": stats.raw_sha256,
            "schema": stats.schema_sha256,
            "plan": plan_hash,
            "staged_output": staged_output_hash,
            "verifier": sha256_path(Path(__file__).with_name("ooxml_verifier.py")),
            "evidence": evidence_hash,
        }
        prepublication = build_composite_result(
            run_id=f"composite-{uuid.uuid4().hex}",
            idempotency_key=manifest["idempotency_key"],
            operation=operation["type"],
            final_state="SUCCEEDED",
            steps=[{"step_index": 0, "type": operation["type"], "status": "succeeded", "evidence_sha256": verification_hash}],
            invariants=invariants,
            bindings=bindings,
            profile=profile_doc,
            cleanup=cleanup,
            publication={"status": "not_attempted", "atomic": False, "staged_sha256": staged_output_hash, "destination_sha256": "0" * 64},
        )
        if not publication_eligible(prepublication):
            raise ContractError("RESULT_PROOF_INVALID", "Complete proof did not become publication-eligible.", {})
        current_destination_hash = sha256_path(output_destination) if output_destination.is_file() else None
        if current_destination_hash != original_destination_hash:
            raise ContractError("RESULT_PROOF_INVALID", "Destination changed during the transaction; publication refused.", {})
        with AtomicPublication(output_destination, original_destination_hash) as publication:
            destination_hash = publication.publish(native_output)
            if destination_hash != staged_output_hash:
                raise ContractError("RESULT_PROOF_INVALID", "Published destination hash differs from verified staged bytes.", {})
            final_result = build_composite_result(
                run_id=prepublication["run_id"],
                idempotency_key=manifest["idempotency_key"],
                operation=operation["type"],
                final_state="SUCCEEDED",
                steps=prepublication["steps"],
                invariants=invariants,
                bindings=bindings,
                profile=profile_doc,
                cleanup=cleanup,
                publication={"status": "published", "atomic": True, "staged_sha256": staged_output_hash, "destination_sha256": destination_hash},
            )
            if not final_result["ok"]:
                raise ContractError("RESULT_PROOF_INVALID", "Published result did not recompute to ok=true.", {})
            write_json_atomic(result_path, final_result)
            publication.commit()
        return final_result, 0
    except Exception as exc:
        if isinstance(exc, ContractError):
            error_document = exc.to_dict()
        else:
            error_document = {"code": exc.__class__.__name__, "message": str(exc), "details": {}}
        message = f"{error_document['code']}: {exc}"
        profile_doc = None
        if profile_binding is not None:
            try:
                profile_doc = {
                    "id": profile_binding["profile"]["id"],
                    "sha256": profile_binding["sha256"],
                    "build_commit": _build_commit(),
                }
            except Exception:
                profile_doc = None
        failed = _failure_result(manifest, evidence_dir, message, cleanup=cleanup, profile=profile_doc, error=error_document)
        write_json_atomic(result_path, failed)
        return failed, 1
    finally:
        if staging_dir is not None and staging_dir.is_dir():
            shutil.rmtree(staging_dir, ignore_errors=True)

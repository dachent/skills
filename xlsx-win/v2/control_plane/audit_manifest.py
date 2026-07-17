"""Build an audit manifest linking a job's input, output, and validation results.

Per RFC 0001's security model ("every output is traceable to input hash,
job manifest, runtime version, and validation contract") -- descoped for a
single-user desktop deployment (RFC 0002) to the fields this control plane
actually has on hand: a run id, the input/output files' content hashes, the
validation contract's path/hash if one was used, and the (redacted)
invariant results produced by control_plane.invariant_evaluator.

Redaction is a floor, not a guarantee: this module recognizes a handful of
obviously secret-shaped patterns (connection-string keywords, credentials
embedded in a URL, bearer tokens, a few well-known API-key prefixes) in an
invariant's `message` field and replaces the whole message with
"[redacted]". It does not attempt to be exhaustive about every possible
secret shape -- RFC 0001's full log/connection-string/credential redaction
policy is broader than this. What it must do, and does, is refuse to pass
through an obvious connection-string-shaped value verbatim.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from .errors import ContractError
from .schemas import validate_audit_manifest

SUPPORTED_AUDIT_SCHEMA_VERSION = "1.0"
_HASH_CHUNK_SIZE = 1024 * 1024

# Deliberately a small, explicit set rather than an exhaustive secret-scanner:
# connection-string keywords, credentials embedded in a URL, bearer tokens,
# and a few well-known vendor API-key prefixes.
_SECRET_PATTERNS = (
    re.compile(r"Provider\s*=", re.IGNORECASE),
    re.compile(r"Data Source\s*=", re.IGNORECASE),
    re.compile(r"://[^/\s:@]+:[^/\s@]+@"),  # scheme://user:pass@host
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|secret)\s*[=:]\s*\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{10,}\b"),
    re.compile(r"\b(?:sk-|ghp_|gho_|AKIA|xox[baprs]-)[A-Za-z0-9_-]{10,}\b"),
)

# Bare ADO.NET/SqlClient and ODBC connection strings (the most common shape
# for SQL Server / MySQL / PostgreSQL / generic ODBC) don't necessarily use
# "Provider=" or "Data Source=" -- e.g. "Server=...;User Id=...;Password=...;"
# or "Driver={SQL Server};Server=...;Uid=...;Pwd=...;". A bare credential
# keyword like "password=" is too weak a signal on its own (it can appear in
# ordinary prose), so this fires only when a credential keyword and a
# connection-host keyword both appear in the same message.
_CONNECTION_HOST_KEYWORDS = re.compile(
    r"\b(?:server|host|database|driver)\s*=", re.IGNORECASE
)
_CONNECTION_CREDENTIAL_KEYWORDS = re.compile(
    r"\b(?:user id|uid|pwd|password)\s*=\s*\S+", re.IGNORECASE
)


def _looks_like_secret(message: str) -> bool:
    if any(pattern.search(message) for pattern in _SECRET_PATTERNS):
        return True
    return bool(
        _CONNECTION_HOST_KEYWORDS.search(message)
        and _CONNECTION_CREDENTIAL_KEYWORDS.search(message)
    )


def _redact_invariant(invariant: dict) -> dict:
    redacted = dict(invariant)
    message = redacted.get("message")
    if isinstance(message, str) and _looks_like_secret(message):
        redacted["message"] = "[redacted]"
    return redacted


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ContractError(
            "AUDIT_SOURCE_MISSING",
            f"Cannot compute hash: file does not exist: {path}",
            {"path": str(path)},
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_audit_manifest(
    run_id: str,
    input_path,
    output_path,
    contract_path,
    invariant_results: list,
) -> dict:
    """Build an audit manifest dict, redacting secret-shaped invariant messages.

    Computes sha256 of `input_path` and `output_path`; raises ContractError
    (AUDIT_SOURCE_MISSING) if either does not exist. Includes `contract_path`
    and its sha256 only if `contract_path` is not None (also
    AUDIT_SOURCE_MISSING if a non-None contract_path doesn't exist).

    Always validates the built manifest against audit_manifest.schema.json
    before returning, the same way result_contract.build_result() always
    validates against result.schema.json -- there is no way to opt out.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    manifest = {
        "schema_version": SUPPORTED_AUDIT_SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "input_sha256": _sha256_file(input_path),
        "output_path": str(output_path),
        "output_sha256": _sha256_file(output_path),
        "invariant_results": [_redact_invariant(entry) for entry in invariant_results],
    }

    if contract_path is not None:
        contract_path = Path(contract_path)
        manifest["contract_path"] = str(contract_path)
        manifest["contract_sha256"] = _sha256_file(contract_path)

    validate_audit_manifest(manifest)
    return manifest

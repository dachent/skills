"""Private, content-addressed evidence indexing for composite transactions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .ooxml_verifier import sha256_path


def write_evidence_index(
    evidence_dir: Path,
    *,
    status: str,
    metadata: dict | None = None,
) -> str:
    files = {
        path.name: sha256_path(path)
        for path in sorted(evidence_dir.iterdir(), key=lambda candidate: candidate.name)
        if path.is_file() and path.name != "evidence-index.json"
    }
    index = {
        "schema_version": "1.0",
        "status": status,
        "files": files,
    }
    if metadata:
        index["metadata"] = metadata
    payload = json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    (evidence_dir / "evidence-index.json").write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

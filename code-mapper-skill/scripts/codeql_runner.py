from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

MIN_CODEQL_VERSION = (2, 16, 4)


class CodeQLError(RuntimeError):
    pass


def cache_root(repo: Path) -> Path:
    override = os.environ.get("CODE_MAPPER_CACHE")
    if override:
        base = Path(override)
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "code-mapper"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "code-mapper"
    key = hashlib.sha1(str(repo.resolve()).encode("utf-8")).hexdigest()[:16]
    return base / key


def source_fingerprint(repo: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(repo.rglob("*.py")):
        if any(part in {".git", ".venv", "venv", "node_modules", "site-packages", "__pycache__"} for part in path.parts):
            continue
        digest.update(path.relative_to(repo).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def resolve_codeql(override: str | None = None) -> str:
    candidate = override or os.environ.get("CODEQL_CLI") or shutil.which("codeql")
    if not candidate:
        raise CodeQLError("CodeQL is required for --deep but was not found")
    path = Path(candidate)
    if path.is_dir():
        for name in ("codeql.exe", "codeql"):
            executable = path / name
            if executable.exists():
                return str(executable)
    return str(path)


def codeql_version(codeql: str) -> str:
    try:
        result = subprocess.run([codeql, "version", "--format=json"], capture_output=True, text=True, check=True, timeout=10)
        payload = json.loads(result.stdout)
        version = str(payload.get("version") or payload.get("versionNumber") or "")
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
        raise CodeQLError(f"unable to read CodeQL version: {exc}") from exc
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise CodeQLError(f"unrecognized CodeQL version: {version!r}")
    if tuple(int(part) for part in match.groups()) < MIN_CODEQL_VERSION:
        raise CodeQLError(f"CodeQL {version} is too old; 2.16.4 or newer is required")
    return version


def search_path(codeql: str) -> Path | None:
    executable = Path(codeql).resolve()
    candidates = [executable.parent / "qlpacks", executable.parent.parent / "qlpacks"]
    env_path = os.environ.get("CODEQL_SEARCH_PATH")
    if env_path:
        candidates.insert(0, Path(env_path))
    return next((candidate for candidate in candidates if candidate.is_dir()), None)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def ensure_database(repo: Path, codeql: str, version: str, rebuild: bool = False) -> Path:
    root = cache_root(repo)
    database = root / "database"
    metadata_file = root / "database.json"
    fingerprint = source_fingerprint(repo)
    metadata = load_json(metadata_file)
    current = (
        database.is_dir()
        and metadata.get("repo") == str(repo.resolve())
        and metadata.get("fingerprint") == fingerprint
        and metadata.get("codeqlVersion") == version
    )
    if current and not rebuild:
        return database

    root.mkdir(parents=True, exist_ok=True)
    building = root / "database-building"
    shutil.rmtree(building, ignore_errors=True)
    command = [
        codeql, "database", "create",
        "--language=python",
        f"--source-root={repo.resolve()}",
        "--build-mode=none",
        "--overwrite",
        "--",
        str(building),
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(building, ignore_errors=True)
        raise CodeQLError("CodeQL database build timed out") from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        shutil.rmtree(building, ignore_errors=True)
        detail = getattr(exc, "stderr", "") or str(exc)
        raise CodeQLError(f"CodeQL database build failed: {detail.strip()}") from exc

    shutil.rmtree(database, ignore_errors=True)
    os.replace(building, database)
    write_json(metadata_file, {
        "repo": str(repo.resolve()),
        "fingerprint": fingerprint,
        "codeqlVersion": version,
        "buildMode": "none",
    })
    return database


def parse_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return []
    start = 1 if rows[0] and rows[0][0].lower() in {"kind", "sinkkind"} else 0
    result: list[dict[str, Any]] = []
    for row in rows[start:]:
        if len(row) < 6:
            continue
        result.append({
            "sinkKind": row[0],
            "flowKind": row[1],
            "source": row[2],
            "sink": row[3],
            "file": row[4].replace("\\", "/"),
            "line": int(row[5]) if row[5].isdigit() else row[5],
        })
    return result


def run_query(repo: Path, codeql: str, database: Path, query: Path) -> list[dict[str, Any]]:
    root = cache_root(repo)
    bqrs = root / "flows.bqrs"
    csv_file = root / "flows.csv"
    command = [codeql, "query", "run", f"--database={database}", f"--output={bqrs}"]
    ql_path = search_path(codeql)
    if ql_path:
        command.append(f"--search-path={ql_path}")
    command.extend(["--", str(query.resolve())])
    try:
        subprocess.run(command, capture_output=True, text=True, check=True, timeout=300)
        subprocess.run(
            [codeql, "bqrs", "decode", "--format=csv", "--entities=string", f"--output={csv_file}", "--", str(bqrs)],
            capture_output=True, text=True, check=True, timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise CodeQLError("CodeQL query timed out") from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise CodeQLError(f"CodeQL query failed: {detail.strip()}") from exc
    return parse_csv(csv_file)


def semantic_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        relationship = "VALUE_FLOWS_TO" if row["flowKind"] == "value" else "INFLUENCES"
        target = f"{row['sinkKind']}@{row['file']}:{row['line']}"
        key = (str(row["source"]), relationship, target)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "source": str(row["source"]),
            "relationship": relationship,
            "target": target,
            "targetType": "semantic-sink",
            "confidence": "semantic",
            "evidence": {
                "file": row["file"],
                "line": row["line"],
                "extractor": "codeql-local-flow" if relationship == "VALUE_FLOWS_TO" else "codeql-local-taint",
            },
        })
    return result


def enrich(repo: Path, graph: dict[str, Any], query: Path, *, codeql_override: str | None = None, rebuild: bool = False) -> dict[str, Any]:
    codeql = resolve_codeql(codeql_override)
    version = codeql_version(codeql)
    database = ensure_database(repo, codeql, version, rebuild=rebuild)
    rows = run_query(repo, codeql, database, query)
    graph = dict(graph)
    graph["edges"] = sorted(graph.get("edges", []) + semantic_edges(rows), key=lambda item: (
        item["source"], item["relationship"], item["target"], item["evidence"].get("file", ""), item["evidence"].get("line", 0),
    ))
    graph["stats"] = dict(graph.get("stats", {}))
    graph["stats"]["edges"] = len(graph["edges"])
    graph["deep"] = {"codeqlVersion": version, "database": str(database), "rows": len(rows)}
    return graph

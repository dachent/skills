"""Fast, local orchestration for artifact, contract, catalog, and lineage mapping.

The default scanner uses only the Python standard library. It never imports or
executes target code and writes only to the caller-provided cache directory.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from _contract_relationships import parse_contract_file
from _python_relationships import scan_python_file
from _relationship_common import _dedupe_edges

SCHEMA_VERSION = 1
PRODUCER = "https://github.com/dachent/skills/tree/main/code-mapper-skill"
OPENLINEAGE_SCHEMA = "https://openlineage.io/spec/2-0-2/OpenLineage.json"
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".tox", ".nox", ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", "site-packages", "dist", "build", "target", ".dep-map-cache",
}
CONTRACT_NAMES = {
    "openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml", "swagger.yml", "swagger.json",
    "asyncapi.yaml", "asyncapi.yml", "asyncapi.json", "catalog-info.yaml", "catalog-info.yml",
}
CONTRACT_SUFFIXES = (".graphql", ".gql", ".proto", ".avsc")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_files(root: Path, predicate) -> Iterable[Path]:
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.is_symlink():
                    stack.append(entry)
            elif predicate(entry):
                yield entry


def _python_files(package_dir: Path) -> list[Path]:
    return sorted(_iter_files(package_dir, lambda p: p.suffix.lower() == ".py"))


def _contract_files(repo_root: Path) -> list[Path]:
    def wanted(path: Path) -> bool:
        name = path.name.lower()
        if name in CONTRACT_NAMES or name.startswith("catalog-info."):
            return True
        if path.suffix.lower() in CONTRACT_SUFFIXES:
            return True
        if path.suffix.lower() == ".json":
            return any(token in name for token in ("schema", "openapi", "swagger", "asyncapi", "pact"))
        if path.suffix.lower() in {".yaml", ".yml"}:
            return any(token in name for token in ("openapi", "swagger", "asyncapi", "catalog"))
        return False
    return sorted(_iter_files(repo_root, wanted))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dataset_namespace(edge: dict[str, Any]) -> str:
    relation = edge["relationship"]
    target = edge["target"]
    if "TABLE" in relation:
        return "database"
    if target.startswith(("s3://", "gs://", "az://")):
        return target.split(":", 1)[0]
    if relation in {"LOADS_MODEL", "SAVES_MODEL"}:
        return "model"
    return "file"


def to_openlineage_job_events(edges: list[dict[str, Any]], event_time: str | None = None) -> list[dict[str, Any]]:
    event_time = event_time or _utc_now()
    grouped: dict[str, dict[str, list[dict[str, str]]]] = {}
    input_relations = {"READS_FILE", "READS_TABLE", "LOADS_MODEL"}
    output_relations = {"WRITES_FILE", "WRITES_TABLE", "SAVES_MODEL"}
    for edge in edges:
        relation = edge["relationship"]
        if relation not in input_relations | output_relations:
            continue
        bucket = grouped.setdefault(edge["source"], {"inputs": [], "outputs": []})
        dataset = {"namespace": _dataset_namespace(edge), "name": edge["target"]}
        key = "inputs" if relation in input_relations else "outputs"
        if dataset not in bucket[key]:
            bucket[key].append(dataset)
    events = []
    for job_name, datasets in sorted(grouped.items()):
        events.append({
            "eventTime": event_time,
            "producer": PRODUCER,
            "schemaURL": OPENLINEAGE_SCHEMA,
            "job": {"namespace": "code-mapper", "name": job_name},
            "inputs": sorted(datasets["inputs"], key=lambda d: (d["namespace"], d["name"])),
            "outputs": sorted(datasets["outputs"], key=lambda d: (d["namespace"], d["name"])),
        })
    return events


def scan_repository(repo_root: Path, package_dir: Path, package: str, cache_dir: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    package_dir = package_dir.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "relationship-cache.json"
    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
        if cache.get("schemaVersion") != SCHEMA_VERSION:
            cache = {"schemaVersion": SCHEMA_VERSION, "files": {}}
    except (OSError, json.JSONDecodeError):
        cache = {"schemaVersion": SCHEMA_VERSION, "files": {}}
    old_files = cache.get("files", {})

    candidates: list[tuple[Path, str]] = [(p, "python") for p in _python_files(package_dir)]
    seen = {p for p, _ in candidates}
    candidates.extend((p, "contract") for p in _contract_files(repo_root) if p not in seen)

    candidate_info = []
    metadata_unchanged = len(candidates) == len(old_files)
    pre_errors = []
    for path, kind in candidates:
        file_rel = _rel(path, repo_root)
        try:
            stat = path.stat()
        except OSError as exc:
            pre_errors.append({"file": file_rel, "error": str(exc)})
            metadata_unchanged = False
            continue
        candidate_info.append((path, kind, file_rel, stat))
        cached = old_files.get(file_rel)
        if not cached or cached.get("size") != stat.st_size or cached.get("mtimeNs") != stat.st_mtime_ns or cached.get("kind") != kind:
            metadata_unchanged = False

    aggregate = cache.get("aggregate")
    if metadata_unchanged and aggregate and not pre_errors:
        graph = dict(aggregate)
        graph["stats"] = dict(graph.get("stats", {}))
        graph["stats"].update({
            "candidateFiles": len(candidates), "parsedFiles": 0,
            "cacheHits": len(candidates), "edges": len(graph.get("edges", [])),
            "contracts": len(graph.get("contracts", [])),
        })
        graph["openLineageEvents"] = len(to_openlineage_job_events(graph.get("edges", []), graph.get("generatedAt")))
        relationships_file = cache_dir / "relationships.json"
        lineage_file = cache_dir / "openlineage-job-events.json"
        if not relationships_file.exists():
            relationships_file.write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")
        if not lineage_file.exists():
            lineage_file.write_text(json.dumps(to_openlineage_job_events(graph["edges"], graph["generatedAt"]), indent=2, sort_keys=True), encoding="utf-8")
        return graph

    new_files: dict[str, Any] = {}
    all_edges = []
    all_contracts = []
    errors = list(pre_errors)
    parsed_files = 0
    cache_hits = 0

    for path, kind, file_rel, stat in candidate_info:
        cached = old_files.get(file_rel)
        if cached and cached.get("size") == stat.st_size and cached.get("mtimeNs") == stat.st_mtime_ns and cached.get("kind") == kind:
            result = cached.get("result", {"edges": [], "contracts": [], "errors": []})
            digest = cached.get("sha256")
            cache_hits += 1
        else:
            try:
                data = path.read_bytes()
                digest = _sha256(data)
            except OSError as exc:
                errors.append({"file": file_rel, "error": str(exc)})
                continue
            if cached and cached.get("sha256") == digest and cached.get("kind") == kind:
                result = cached.get("result", {"edges": [], "contracts": [], "errors": []})
                cache_hits += 1
            else:
                result = scan_python_file(path, package_dir, package, repo_root, data) if kind == "python" else parse_contract_file(path, repo_root, data)
                parsed_files += 1
        new_files[file_rel] = {
            "kind": kind, "size": stat.st_size, "mtimeNs": stat.st_mtime_ns,
            "sha256": digest, "result": result,
        }
        all_edges.extend(result.get("edges", []))
        all_contracts.extend(result.get("contracts", []))
        errors.extend(result.get("errors", []))

    edges = _dedupe_edges(all_edges)
    contracts = sorted(all_contracts, key=lambda c: (c.get("kind", ""), c.get("name", ""), c.get("file", "")))
    graph = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": _utc_now(),
        "root": str(repo_root),
        "package": package,
        "edges": edges,
        "contracts": contracts,
        "errors": errors,
        "stats": {
            "candidateFiles": len(candidates), "parsedFiles": parsed_files,
            "cacheHits": cache_hits, "edges": len(edges), "contracts": len(contracts),
        },
    }
    events = to_openlineage_job_events(edges, graph["generatedAt"])
    graph["openLineageEvents"] = len(events)
    cache_payload = {"schemaVersion": SCHEMA_VERSION, "files": new_files, "aggregate": graph}
    cache_file.write_text(json.dumps(cache_payload, indent=2, sort_keys=True), encoding="utf-8")
    (cache_dir / "relationships.json").write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")
    (cache_dir / "openlineage-job-events.json").write_text(json.dumps(events, indent=2, sort_keys=True), encoding="utf-8")
    return graph


def render_relationships(module_dotted: str, graph: dict[str, Any]) -> str:
    edges = [e for e in graph.get("edges", []) if e.get("source") == module_dotted or str(e.get("source", "")).startswith(module_dotted + ".")]
    lines = [f"## Artifact and contract relationships for `{module_dotted}` ({len(edges)})", ""]
    if not edges:
        lines.append("_none found by the fast static scanners_")
    else:
        for edge in edges:
            ev = edge["evidence"]
            lines.append(f"- `{edge['relationship']}` → `{edge['target']}` (`{ev['file']}:{ev['line']}`, {edge['confidence']})")
    stats = graph.get("stats", {})
    lines += [
        "",
        "## Repository contracts and lineage",
        "",
        f"- Contract/catalog records: {stats.get('contracts', 0)}",
        f"- Relationship edges: {stats.get('edges', 0)}",
        f"- Scanner cache: {stats.get('cacheHits', 0)} hit(s), {stats.get('parsedFiles', 0)} parsed file(s)",
        f"- OpenLineage-compatible JobEvents: {graph.get('openLineageEvents', 0)}",
    ]
    if graph.get("errors"):
        lines.append(f"- Scanner warnings: {len(graph['errors'])}")
    return "\n".join(lines)

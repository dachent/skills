"""Canonical local code mapper: imports, references, artifacts, contracts, lineage, and CodeQL."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path
from typing import Any

import bootstrap_env
import resolve_target
from _codeql_cli import add_codeql_arguments, budget_overrides
from _codeql_pack import ensure_query_pack
from _codeql_runtime import enrich_with_codeql
from _graph import build, find_cycles
from _paths import target_cache_dir
from _references import find_symbol_references
from _relationships import scan_repository


def module_dotted_for_file(package: str, file_rel: str) -> str:
    parts = list(Path(file_rel).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join([package, *parts]) if parts else package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Map structural, artifact, contract, lineage, and semantic relationships.")
    parser.add_argument("target", help="local path or git URL to analyze")
    parser.add_argument("file", help="Python file relative to the package directory")
    parser.add_argument("--package", default=None, help="dotted package name; defaults to the package directory name")
    parser.add_argument("--subdir", default=None, help="package directory relative to the repository root")
    parser.add_argument("--function", default=None, help="function or class in the target file for Jedi reference extraction")
    add_codeql_arguments(parser)
    return parser


def _validate_target_file(package_dir: Path, file_rel: str) -> Path:
    file_path = (package_dir / file_rel).resolve()
    try:
        file_path.relative_to(package_dir)
    except ValueError as exc:
        raise ValueError(f"target file escapes package directory: {file_rel}") from exc
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    return file_path


def _structural_map(import_graph: Any, module: str, references: list[dict[str, Any]]) -> dict[str, Any]:
    cycles = [cycle for cycle in find_cycles(import_graph) if module in cycle]
    return {
        "module": module,
        "imports": {
            "upstream": sorted(import_graph.find_upstream_modules(module)),
            "downstream": sorted(import_graph.find_downstream_modules(module)),
            "cycles": cycles,
        },
        "references": references,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with contextlib.redirect_stdout(io.StringIO()):
        bootstrap_env.main()

    repo_root = resolve_target.resolve(args.target)
    package_dir = (repo_root / args.subdir).resolve() if args.subdir else repo_root.resolve()
    package = args.package or package_dir.name
    file_path = _validate_target_file(package_dir, args.file)
    module = module_dotted_for_file(package, args.file)

    import_graph = build(package_dir, package)
    references = (
        find_symbol_references(package_dir, file_path, module, args.function)
        if args.function
        else []
    )

    cache_dir = target_cache_dir(package_dir)
    graph = scan_repository(repo_root, package_dir, package, cache_dir)
    ensure_query_pack(cache_dir)
    graph, decision = enrich_with_codeql(
        repo_root=repo_root,
        cache_dir=cache_dir,
        graph=graph,
        mode=args.codeql,
        intent=args.codeql_intent,
        budget_overrides=budget_overrides(args),
    )

    graph["structural"] = _structural_map(import_graph, module, references)
    graph["stats"] = dict(graph.get("stats", {}))
    graph["stats"].update(
        {
            "importModules": len(import_graph.modules),
            "references": len(references),
            "semanticEdges": len(graph.get("semanticEdges", [])),
        }
    )
    graph["codeql"]["decisionSummary"] = {
        "action": decision.action,
        "reason": decision.reason,
    }

    output = cache_dir / "code-map.json"
    output.write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(graph, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

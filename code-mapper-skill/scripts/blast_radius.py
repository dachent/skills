"""Orchestrator: one merged markdown "what breaks if I edit this" report.

Combines the grimp import-graph layer (module-level blast radius, cycles) with the
jedi symbol layer (call-site references for a specific function/class), for a local
path or a git URL target.
"""
import argparse
import re
from datetime import datetime
from pathlib import Path

import jedi

import bootstrap_env
import find_references as fr
import resolve_target
from _graph import build, find_cycles
from _paths import JEDI_CACHE_DIR, target_cache_dir
from _relationships import render_relationships, scan_repository


def module_dotted_for_file(package_dir: Path, package: str, file_rel: str) -> str:
    rel = Path(file_rel)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([package, *parts]) if parts else package


def render_report(target, file_rel, module_dotted, upstream, downstream, cycles, refs_section) -> str:
    lines = [
        f"# Blast radius report: `{file_rel}` (`{module_dotted}`)",
        "",
        f"- Target: `{target}`",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"## Downstream (blast radius, transitive) - what imports `{module_dotted}`, directly or via a chain ({len(downstream)})",
        "",
    ]
    if not downstream:
        lines.append("_none_")
    else:
        lines.extend(f"- `{m}`" for m in sorted(downstream))
    lines += [
        "",
        f"## Upstream - what `{module_dotted}` imports ({len(upstream)})",
        "",
    ]
    if not upstream:
        lines.append("_none_")
    else:
        lines.extend(f"- `{m}`" for m in sorted(upstream))

    relevant_cycles = [c for c in cycles if module_dotted in c]
    lines += ["", f"## Cycles involving `{module_dotted}` ({len(relevant_cycles)})", ""]
    if not relevant_cycles:
        lines.append("_none_")
    else:
        for i, cyc in enumerate(relevant_cycles, 1):
            lines.append(f"{i}. " + " <-> ".join(f"`{m}`" for m in cyc))

    if refs_section is not None:
        lines += ["", refs_section]

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="local path or git URL to analyze")
    ap.add_argument("file", help="file path relative to the package directory, e.g. b.py or sub/mod.py")
    ap.add_argument("--package", default=None, help="dotted package name (default: package dir name)")
    ap.add_argument("--subdir", default=None, help="package dir relative to target, if target isn't the package dir itself")
    ap.add_argument("--function", default=None, help="function/class name (defined in `file`) to also find call sites for")
    ap.add_argument(
        "--skip-relationships",
        action="store_true",
        help="skip the default local artifact/contract/catalog scan",
    )
    args = ap.parse_args()

    bootstrap_env.main()

    resolved = resolve_target.resolve(args.target)
    package_dir = (resolved / args.subdir).resolve() if args.subdir else resolved
    package = args.package or package_dir.name

    graph = build(package_dir, package)
    module_dotted = module_dotted_for_file(package_dir, package, args.file)

    upstream = graph.find_upstream_modules(module_dotted)
    downstream = graph.find_downstream_modules(module_dotted)
    cycles = find_cycles(graph)

    refs_section = None
    if args.function:
        JEDI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        jedi.settings.cache_directory = str(JEDI_CACHE_DIR)
        file_path = package_dir / args.file
        line, col = fr.find_definition_position(file_path, args.function)
        project = jedi.Project(str(package_dir.parent))
        script = jedi.Script(path=str(file_path), project=project)
        refs = script.get_references(line=line, column=col)
        refs_section = fr.render_references(f"{module_dotted}.{args.function}", refs)

    cache_dir = target_cache_dir(package_dir)
    relationship_section = None
    if not args.skip_relationships:
        relationship_graph = scan_repository(resolved, package_dir, package, cache_dir)
        relationship_section = render_relationships(module_dotted, relationship_graph)

    report = render_report(resolved, args.file, module_dotted, upstream, downstream, cycles, refs_section)
    if relationship_section:
        report += "\n\n" + relationship_section

    out_dir = cache_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{args.file}-{args.function or ''}")
    out_file = out_dir / f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{slug}.md"
    out_file.write_text(report, encoding="utf-8")

    print(report)
    print(f"\n(saved to {out_file})")


if __name__ == "__main__":
    main()

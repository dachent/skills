"""Module-level import queries: upstream/downstream (blast radius), cycles, shortest chain."""
import argparse
from pathlib import Path

from _graph import build, find_cycles


def render_module_list(title: str, mods) -> str:
    lines = [f"### {title} ({len(mods)})", ""]
    if not mods:
        lines.append("_none_")
    else:
        lines.extend(f"- `{m}`" for m in sorted(mods))
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target_path", help="path to the package directory to analyze")
    ap.add_argument("--package", default=None, help="dotted package name (default: folder name)")
    ap.add_argument("--module", required=True, help="dotted module name to query, e.g. src.branch_residual")
    ap.add_argument("--direction", choices=["upstream", "downstream", "both"], default="both")
    ap.add_argument("--find-cycles", action="store_true")
    ap.add_argument("--shortest-chain", default=None, help="other dotted module name")
    args = ap.parse_args()

    target_path = Path(args.target_path).resolve()
    graph = build(target_path, args.package)

    out = [f"## Import-graph report for `{args.module}`", ""]

    if args.direction in ("upstream", "both"):
        upstream = graph.find_upstream_modules(args.module)
        out.append(render_module_list(f"Upstream - what `{args.module}` imports", upstream))

    if args.direction in ("downstream", "both"):
        downstream = graph.find_downstream_modules(args.module)
        out.append(render_module_list(
            f"Downstream (blast radius, transitive) - what imports `{args.module}`, directly or via a chain",
            downstream,
        ))

    if args.find_cycles:
        cycles = find_cycles(graph)
        out.append(f"### Cycles found: {len(cycles)}")
        for i, cyc in enumerate(cycles, 1):
            out.append(f"{i}. " + " <-> ".join(f"`{m}`" for m in cyc))
        out.append("")

    if args.shortest_chain:
        chain = graph.find_shortest_chain(args.module, args.shortest_chain)
        out.append(f"### Shortest chain `{args.module}` -> `{args.shortest_chain}`")
        out.append(" -> ".join(f"`{m}`" for m in chain) if chain else "_no path_")
        out.append("")

    print("\n".join(out))


if __name__ == "__main__":
    main()

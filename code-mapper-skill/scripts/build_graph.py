"""Build (and cache) the import graph for a target Python package. Read-only w.r.t. the target."""
import argparse
import json
from pathlib import Path

from _graph import build, graph_to_dict
from _paths import target_cache_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target_path", help="path to the package directory to analyze")
    ap.add_argument("--package", default=None, help="dotted package name (default: folder name)")
    args = ap.parse_args()

    target_path = Path(args.target_path).resolve()
    graph = build(target_path, args.package)
    data = graph_to_dict(graph)

    out_file = target_cache_dir(target_path) / "graph.json"
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"built graph: {len(data['modules'])} modules, {len(data['edges'])} edges -> {out_file}")


if __name__ == "__main__":
    main()

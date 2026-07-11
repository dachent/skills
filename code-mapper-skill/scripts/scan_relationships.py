"""Build the local artifact/contract/catalog relationship graph and lineage output."""
import argparse
from pathlib import Path

import resolve_target
from _paths import target_cache_dir
from _relationships import scan_repository


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="local path or git URL to analyze")
    ap.add_argument("--package", default=None, help="dotted package name (default: package directory name)")
    ap.add_argument("--subdir", default=None, help="package directory relative to target")
    args = ap.parse_args()

    resolved = resolve_target.resolve(args.target)
    package_dir = (resolved / args.subdir).resolve() if args.subdir else resolved
    package = args.package or package_dir.name
    cache_dir = target_cache_dir(package_dir)
    graph = scan_repository(resolved, package_dir, package, cache_dir)
    stats = graph["stats"]
    print(
        f"mapped {stats['edges']} relationship edges and {stats['contracts']} contract/catalog records "
        f"from {stats['candidateFiles']} files ({stats['cacheHits']} cache hits)"
    )
    print(f"relationships: {cache_dir / 'relationships.json'}")
    print(f"openlineage: {cache_dir / 'openlineage-job-events.json'}")


if __name__ == "__main__":
    main()

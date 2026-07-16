#!/usr/bin/env python3
"""Selective-CodeQL VALUE benchmark for code-mapper-skill (issue #56, cheap core).

Runs the mapper's CodeQL enrichment over small ground-truth fixtures and checks the
guarantees that actually matter for an agent trusting the evidence:

  1. true-positive       -- a genuine dynamic value flow into an artifact sink is found;
  2. false-positive trap -- a constant/literal sink emits NO edge (no fabricated provenance);
  3. cross-function      -- a multi-file pipeline still flags the sink at its local source
                            (RECORDED, not asserted as a full chain: the query is the
                            "local artifact flow" query -- intra-procedural by design, so the
                            provenance chain is not stitched back across the call boundary);
  4. off-by-default      -- mapping intent with no hard trigger performs no CodeQL work;
  5. degradation         -- mode=off returns the structural graph with zero CodeQL work.

Opt-in / slow (real CodeQL build+query per fixture). Not part of the default unittest run.
Needs the CodeQL CLI on PATH (or $CODEQL_CLI) and the codeql/python-all pack available.
Run: python scripts/benchmark_codeql_value.py [--json]
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path

from _codeql_pack import ensure_query_pack
from _codeql_runtime import enrich_with_codeql
from _relationships import scan_repository

_BUDGET = {"maxBuildSeconds": 300, "maxDatabaseMb": 1024, "maxQuerySeconds": 240,
           "projectedBuildSeconds": 1, "projectedDatabaseMb": 50}


def _robust_rmtree(path):
    # CodeQL DB files lag release on Windows; a plain rmtree races to WinError 145.
    def onerror(func, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE); func(p)
        except OSError:
            pass
    for _ in range(5):
        shutil.rmtree(path, onerror=onerror)
        if not os.path.exists(path):
            return
        time.sleep(0.3)


def _enrich(codeql, files, *, mode, intent):
    t = tempfile.mkdtemp()
    try:
        root = Path(t) / "repo"; pkg = root / "pkg"; pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        for name, src in files.items():
            (pkg / name).write_text(src, encoding="utf-8")
        cache = Path(t) / "cache"
        graph = scan_repository(root, pkg, "pkg", cache)
        ensure_query_pack(cache)
        overrides = _BUDGET if mode in ("build", "auto") else None
        enriched, decision = enrich_with_codeql(
            repo_root=root, cache_dir=cache, graph=graph, mode=mode, intent=intent,
            codeql_override=codeql, budget_overrides=overrides,
        )
        b = enriched["codeql"].get("build") or {}
        q = enriched["codeql"].get("query") or {}
        return {
            "action": decision.action,
            "edges": enriched.get("semanticEdges", []),
            "buildSeconds": b.get("buildSeconds"),
            "querySeconds": q.get("querySeconds"),
            "databaseMb": b.get("databaseMb"),
            "buildRan": bool(b),
        }
    finally:
        _robust_rmtree(t)


TP_DYNAMIC = {"io.py": "import pandas as pd\ndef load(root, tenant):\n path = root / f'{tenant}.csv'\n return pd.read_csv(path)\n"}
TN_CONSTANT = {"io.py": "import pandas as pd\ndef load():\n return pd.read_csv('static_reference.csv')\n"}
XFN_MULTIFILE = {
    "a.py": "from pkg import b\ndef run(root, tenant):\n path = root / f'{tenant}.csv'\n return b.read_it(path)\n",
    "b.py": "import pandas as pd\ndef read_it(path):\n return pd.read_csv(path)\n",
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    as_json = "--json" in argv
    codeql = os.environ.get("CODEQL_CLI") or shutil.which("codeql")
    if not codeql:
        print("SKIP: CodeQL CLI not found on PATH or $CODEQL_CLI")
        return 0

    results = {}
    results["tp_dynamic"] = _enrich(codeql, TP_DYNAMIC, mode="build", intent="value-flow")
    results["tn_constant"] = _enrich(codeql, TN_CONSTANT, mode="build", intent="value-flow")
    results["xfn_multifile"] = _enrich(codeql, XFN_MULTIFILE, mode="build", intent="value-flow")
    results["off_by_default"] = _enrich(codeql, TP_DYNAMIC, mode="auto", intent="mapping")
    results["degradation_off"] = _enrich(codeql, TP_DYNAMIC, mode="off", intent="value-flow")

    checks = [
        ("true positive found", len(results["tp_dynamic"]["edges"]) >= 1),
        ("false-positive trap emits no edge", len(results["tn_constant"]["edges"]) == 0),
        ("cross-function flags the sink", len(results["xfn_multifile"]["edges"]) >= 1),
        ("off-by-default performs no build", results["off_by_default"]["action"] == "skip"
            and not results["off_by_default"]["buildRan"]),
        ("mode=off degrades to structural, no edges", not results["degradation_off"]["buildRan"]
            and len(results["degradation_off"]["edges"]) == 0),
    ]
    summary = {
        "truePathsFound": len(results["tp_dynamic"]["edges"]),
        "falsePathsOnTrap": len(results["tn_constant"]["edges"]),
        "crossFunctionEdges": len(results["xfn_multifile"]["edges"]),
        "crossFunctionNote": "edge emitted at the sink's local source; chain not traced across the call (intra-procedural query)",
        "checks": {name: ok for name, ok in checks},
    }

    if as_json:
        print(json.dumps({"results": results, "summary": summary}, indent=2, default=str))
    else:
        for name, r in results.items():
            print(f"{name:16} action={r['action']:14} edges={len(r['edges'])} "
                  f"buildS={r['buildSeconds']} queryS={r['querySeconds']}")
        print()
        for name, ok in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("\nBENCHMARK GATE FAILED: " + "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

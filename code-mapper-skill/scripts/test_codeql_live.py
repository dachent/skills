from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from _codeql_pack import ensure_query_pack
from _codeql_runtime import enrich_with_codeql
from _relationships import scan_repository

DIAGNOSTIC = Path(__file__).resolve().parent / "codeql-live-diagnostic.json"


def _robust_rmtree(path: str) -> None:
    # CodeQL leaves database files whose deletion can lag on Windows.
    def onerror(func, target, _exc):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    for _ in range(5):
        shutil.rmtree(path, onerror=onerror)
        if not os.path.exists(path):
            return
        time.sleep(0.3)


class LiveTest(unittest.TestCase):
    def test_real_codeql(self):
        codeql = os.environ.get("CODEQL_CLI") or shutil.which("codeql")
        if not codeql:
            self.skipTest("CodeQL CLI is not installed")
        if os.environ.get("CODE_MAPPER_ALLOW_CODEQL_SETUP") != "1":
            self.skipTest("explicit CODE_MAPPER_ALLOW_CODEQL_SETUP=1 is required")

        enriched = {"codeql": {"diagnostic": "not started"}}
        decision = None
        temp = tempfile.mkdtemp()
        try:
            root = Path(temp) / "repo"
            package = root / "pkg"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "io.py").write_text(
                "import pandas as pd\ndef load(root,tenant):\n path=root/f'{tenant}.csv'\n return pd.read_csv(path)\n",
                encoding="utf-8",
            )
            cache = Path(temp) / "cache"
            graph = scan_repository(root, package, "pkg", cache)
            query_pack = ensure_query_pack(cache)
            subprocess.run([codeql, "pack", "install", str(query_pack.parent)], check=True, timeout=180)
            enriched, decision = enrich_with_codeql(
                repo_root=root,
                cache_dir=cache,
                graph=graph,
                mode="build",
                intent="value-flow",
                codeql_override=codeql,
                budget_overrides={
                    "maxBuildSeconds": 180,
                    "maxDatabaseMb": 1024,
                    "maxQuerySeconds": 120,
                    "projectedBuildSeconds": 1,
                    "projectedDatabaseMb": 50,
                },
                allow_writes=True,
            )
            self.assertEqual(decision.action, "build-and-run")
            self.assertTrue(enriched["codeql"]["build"]["ok"], enriched["codeql"]["build"])
            self.assertTrue(enriched["codeql"]["query"]["ok"], enriched["codeql"]["query"])
            self.assertTrue(enriched["semanticEdges"])
        finally:
            payload = {
                "decision": decision.to_dict() if decision else None,
                "codeql": enriched.get("codeql"),
                "semanticEdges": enriched.get("semanticEdges", []),
            }
            DIAGNOSTIC.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            _robust_rmtree(temp)


if __name__ == "__main__":
    unittest.main(verbosity=2)

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from codeql_runner import enrich
from mapper_core import scan_repository


class LiveCodeQLTest(unittest.TestCase):
    def test_real_codeql(self):
        codeql = os.environ.get("CODEQL_CLI") or shutil.which("codeql")
        if not codeql:
            self.skipTest("CodeQL is not installed")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            package = root / "pkg"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "io.py").write_text(
                "import pandas as pd\ndef load(root, tenant):\n path = root / f'{tenant}.csv'\n return pd.read_csv(path)\n",
                encoding="utf-8",
            )
            os.environ["CODE_MAPPER_CACHE"] = str(Path(temp) / "cache")
            graph = enrich(root, scan_repository(root), Path(__file__).resolve().parents[1] / "codeql" / "local_flows.ql", codeql_override=codeql)
            self.assertGreater(graph["deep"]["rows"], 0)
            self.assertTrue(any(item["relationship"] in {"VALUE_FLOWS_TO", "INFLUENCES"} for item in graph["edges"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

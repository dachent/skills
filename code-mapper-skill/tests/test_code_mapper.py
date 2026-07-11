from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from codeql_runner import CodeQLError, codeql_version, ensure_database, semantic_edges
from mapper_core import scan_repository


def digest(root: Path) -> str:
    value = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        value.update(path.relative_to(root).as_posix().encode())
        value.update(path.read_bytes())
    return value.hexdigest()


def fixture(root: Path, modules: int = 0) -> Path:
    package = root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "io.py").write_text(
        """import os
import pandas as pd
import requests
from pathlib import Path

def load(source):
    configured = os.getenv('SOURCE_FILE')
    frame = pd.read_csv(source)
    frame.to_parquet('build/items.parquet')
    Path('build/run.log').write_text('done')
    requests.post('https://example.test/items')
    cursor.execute('SELECT * FROM raw.orders JOIN raw.customers c ON 1=1')
    frame.to_sql('analytics.items')
    return configured
""",
        encoding="utf-8",
    )
    (package / "consumer.py").write_text("from .io import load\n\ndef run():\n    return load('input.csv')\n", encoding="utf-8")
    for index in range(modules):
        (package / f"module_{index}.py").write_text(f"from .io import load\nresult = load('input-{index}.csv')\n", encoding="utf-8")
    (root / "openapi.yaml").write_text("openapi: 3.0.0\npaths:\n  /items:\n    get:\n      responses: {}\n", encoding="utf-8")
    return root


class StaticMapTests(unittest.TestCase):
    def test_map_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo")
            before = digest(root)
            graph = scan_repository(root)
            self.assertEqual(before, digest(root))
            relationships = {(item["relationship"], item["target"]) for item in graph["edges"]}
            expected = {
                ("IMPORTS", "pandas"),
                ("CALLS", "pandas.read_csv"),
                ("READS_FILE", "${source}"),
                ("WRITES_FILE", "build/items.parquet"),
                ("WRITES_FILE", "build/run.log"),
                ("READS_CONFIG", "SOURCE_FILE"),
                ("CONSUMES_ENDPOINT", "POST https://example.test/items"),
                ("READS_TABLE", "raw.orders"),
                ("READS_TABLE", "raw.customers"),
                ("WRITES_TABLE", "analytics.items"),
                ("DEFINES_ENDPOINT", "GET /items"),
            }
            self.assertTrue(expected.issubset(relationships), expected - relationships)

    def test_cli_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo")
            result = subprocess.run([sys.executable, str(SCRIPTS / "code_mapper.py"), str(root)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schemaVersion"], 2)
            self.assertGreater(payload["stats"]["edges"], 0)

    def test_large_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo", modules=600)
            graph = scan_repository(root)
            self.assertEqual(graph["stats"]["pythonFiles"], 603)


class CodeQLTests(unittest.TestCase):
    def test_old_version_rejected(self):
        completed = subprocess.CompletedProcess([], 0, stdout='{"version":"2.15.0"}', stderr="")
        with patch("subprocess.run", return_value=completed):
            with self.assertRaises(CodeQLError):
                codeql_version("codeql")

    def test_database_build_and_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo")
            cache = Path(temp) / "cache"
            with patch("codeql_runner.cache_root", return_value=cache):
                def fake_run(command, **kwargs):
                    if command[1:3] == ["database", "create"]:
                        Path(command[-1]).mkdir(parents=True)
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                with patch("subprocess.run", side_effect=fake_run) as run:
                    first = ensure_database(root, "codeql", "2.20.0")
                    second = ensure_database(root, "codeql", "2.20.0")
                    self.assertEqual(first, second)
                    builds = [call for call in run.call_args_list if call.args[0][1:3] == ["database", "create"]]
                    self.assertEqual(len(builds), 1)
                    self.assertIn("--build-mode=none", builds[0].args[0])

    def test_semantic_edges(self):
        rows = [{"sinkKind": "pandas-read-csv", "flowKind": "taint", "source": "source", "sink": "read_csv", "file": "pkg/io.py", "line": 4}]
        edges = semantic_edges(rows)
        self.assertEqual(edges[0]["relationship"], "INFLUENCES")
        self.assertEqual(edges[0]["target"], "pandas-read-csv@pkg/io.py:4")


class AdditionalBehaviorTests(unittest.TestCase):
    def test_output_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo")
            output = Path(temp) / "graph.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "code_mapper.py"), str(root), "--output", str(output)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()), output.resolve())
            self.assertGreater(json.loads(output.read_text(encoding="utf-8"))["stats"]["edges"], 0)

    def test_deep_without_codeql_fails_visibly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo")
            env = dict(**__import__("os").environ)
            env["PATH"] = ""
            env.pop("CODEQL_CLI", None)
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "code_mapper.py"), str(root), "--deep"],
                capture_output=True, text=True, timeout=30, env=env,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("CodeQL is required", result.stderr)

    def test_syntax_error_is_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo")
            (root / "pkg" / "broken.py").write_text("def broken(:\n", encoding="utf-8")
            graph = scan_repository(root)
            self.assertEqual(graph["stats"]["errors"], 1)
            self.assertEqual(graph["errors"][0]["file"], "pkg/broken.py")

    def test_python_change_rebuilds_but_document_change_does_not(self):
        with tempfile.TemporaryDirectory() as temp:
            root = fixture(Path(temp) / "repo")
            cache = Path(temp) / "cache"
            with patch("codeql_runner.cache_root", return_value=cache):
                def fake_run(command, **kwargs):
                    if command[1:3] == ["database", "create"]:
                        Path(command[-1]).mkdir(parents=True)
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
                with patch("subprocess.run", side_effect=fake_run) as run:
                    ensure_database(root, "codeql", "2.20.0")
                    (root / "README.md").write_text("docs", encoding="utf-8")
                    ensure_database(root, "codeql", "2.20.0")
                    (root / "pkg" / "io.py").write_text("x = 1\n", encoding="utf-8")
                    ensure_database(root, "codeql", "2.20.0")
                    builds = [call for call in run.call_args_list if call.args[0][1:3] == ["database", "create"]]
                    self.assertEqual(len(builds), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

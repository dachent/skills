"""Local smoke test for the fast relationship scanner and existing blast-radius CLI."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from _relationships import OPENLINEAGE_SCHEMA, scan_repository

HERE = Path(__file__).resolve().parent


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def make_fixture(root: Path, extra_modules: int = 0) -> tuple[Path, Path]:
    package = root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from .io import build\n", encoding="utf-8")
    (package / "io.py").write_text(
        """import os
import pandas as pd
import requests
from pathlib import Path

@app.get('/items')
def build(input_path):
    source = os.getenv('SOURCE_FILE')
    frame = pd.read_csv(input_path)
    frame.to_parquet('build/items.parquet')
    Path('build/run.log').write_text('done')
    requests.post('https://example.test/items')
    cursor.execute('SELECT * FROM raw.orders JOIN raw.customers c ON 1=1')
    frame.to_sql('analytics.items')
    return source
""",
        encoding="utf-8",
    )
    (package / "consumer.py").write_text("from .io import build\n\ndef run():\n    return build('input.csv')\n", encoding="utf-8")
    for index in range(extra_modules):
        (package / f"module_{index}.py").write_text(
            f"from .io import build\n\ndef call_{index}():\n    return build('input-{index}.csv')\n",
            encoding="utf-8",
        )
    (root / "openapi.yaml").write_text(
        """openapi: 3.0.0
info:
  title: Fixture
  version: 1.0.0
paths:
  /items:
    get:
      responses: {}
components:
  schemas:
    Item:
      type: object
""",
        encoding="utf-8",
    )
    (root / "events.asyncapi.json").write_text(
        json.dumps({"asyncapi": "3.0.0", "channels": {"item.created": {"publish": {}}, "item.read": {"subscribe": {}}}}),
        encoding="utf-8",
    )
    (root / "schema.graphql").write_text("type Item { id: ID! }\ninput ItemInput { id: ID! }\n", encoding="utf-8")
    (root / "service.proto").write_text("syntax = \"proto3\";\nmessage Item {}\nservice Items { rpc Get (Item) returns (Item); }\n", encoding="utf-8")
    (root / "catalog-info.yaml").write_text(
        """apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: item-service
spec:
  owner: team-items
  system: item-platform
  providesApis:
    - item-api
  consumesApis: [payments-api]
  dependsOn:
    - resource:default/items-db
---
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: item-api
spec:
  type: openapi
  owner: team-items
  definition: |
    $text: ./openapi.yaml
""",
        encoding="utf-8",
    )
    return root, package


class RelationshipSmokeTest(unittest.TestCase):
    def test_scan_cache_contracts_and_openlineage(self):
        with tempfile.TemporaryDirectory() as temp:
            root, package = make_fixture(Path(temp) / "repo")
            cache = Path(temp) / "cache"
            before = tree_digest(root)
            graph = scan_repository(root, package, "pkg", cache)
            after = tree_digest(root)
            self.assertEqual(before, after, "scanner modified the target repository")

            relationships = {(e["relationship"], e["target"]) for e in graph["edges"]}
            expected = {
                ("READS_FILE", "${input_path}"),
                ("WRITES_FILE", "build/items.parquet"),
                ("WRITES_FILE", "build/run.log"),
                ("READS_CONFIG", "SOURCE_FILE"),
                ("CONSUMES_ENDPOINT", "POST https://example.test/items"),
                ("READS_TABLE", "raw.orders"),
                ("READS_TABLE", "raw.customers"),
                ("WRITES_TABLE", "analytics.items"),
                ("IMPLEMENTS_ENDPOINT", "GET /items"),
                ("DEFINES_ENDPOINT", "GET /items"),
                ("DEFINES_SCHEMA", "Item"),
                ("PROVIDES_API", "item-api"),
                ("CONSUMES_API", "payments-api"),
                ("REFERENCES_CONTRACT", "./openapi.yaml"),
            }
            self.assertTrue(expected.issubset(relationships), expected - relationships)
            self.assertGreaterEqual(graph["stats"]["contracts"], 6)
            self.assertGreater(graph["stats"]["parsedFiles"], 0)

            events = json.loads((cache / "openlineage-job-events.json").read_text(encoding="utf-8"))
            self.assertTrue(events)
            for event in events:
                self.assertEqual(event["schemaURL"], OPENLINEAGE_SCHEMA)
                self.assertIn("job", event)
                self.assertNotIn("run", event)

            warm = scan_repository(root, package, "pkg", cache)
            self.assertEqual(warm["stats"]["parsedFiles"], 0)
            self.assertEqual(warm["stats"]["cacheHits"], warm["stats"]["candidateFiles"])

    def test_existing_cli_contract_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = make_fixture(Path(temp) / "repo")
            before = tree_digest(root)
            command = [
                sys.executable, str(HERE / "blast_radius.py"), str(root), "io.py",
                "--subdir", "pkg", "--package", "pkg", "--function", "build",
            ]
            result = subprocess.run(command, cwd=HERE.parent, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("# Blast radius report", result.stdout)
            self.assertIn("## Downstream", result.stdout)
            self.assertIn("## Upstream", result.stdout)
            self.assertIn("## References", result.stdout)
            self.assertIn("## Artifact and contract relationships", result.stdout)
            self.assertEqual(before, tree_digest(root), "CLI modified the target repository")

    def test_warm_scanner_stays_fast(self):
        with tempfile.TemporaryDirectory() as temp:
            root, package = make_fixture(Path(temp) / "repo", extra_modules=120)
            cache = Path(temp) / "cache"
            scan_repository(root, package, "pkg", cache)
            started = time.perf_counter()
            warm = scan_repository(root, package, "pkg", cache)
            elapsed = time.perf_counter() - started
            self.assertEqual(warm["stats"]["parsedFiles"], 0)
            self.assertLess(elapsed, 0.5, f"warm scanner took {elapsed:.3f}s")

    def test_codeql_is_explicit_and_optional(self):
        command = [sys.executable, str(HERE / "codeql_local_flow.py"), "--help"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("existing local Python CodeQL database", result.stdout)
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "db"
            database.mkdir()
            env = dict(**__import__("os").environ)
            env["PATH"] = ""
            missing = subprocess.run(
                [sys.executable, str(HERE / "codeql_local_flow.py"), str(database)],
                capture_output=True, text=True, timeout=10, env=env,
            )
            self.assertEqual(missing.returncode, 2)
            self.assertIn("not installed", missing.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

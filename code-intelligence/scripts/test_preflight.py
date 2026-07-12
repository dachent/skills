#!/usr/bin/env python3
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from preflight import inspect


class PreflightTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        (root / "a.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "a.py"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
        return root

    def test_missing_graph(self):
        result = inspect(self.make_repo())
        self.assertEqual(result["graphify"]["state"], "missing")
        self.assertFalse(result["policy"]["parsedGraphJson"])

    def test_semantic_flag_wins(self):
        root = self.make_repo()
        out = root / "graphify-out"
        out.mkdir()
        (out / "graph.json").write_text(json.dumps({"nodes": []}), encoding="utf-8")
        (out / "needs_update").write_text("1", encoding="utf-8")
        result = inspect(root)
        self.assertEqual(result["graphify"]["state"], "semantic_stale")

    def test_matching_report_commit_is_fresh(self):
        root = self.make_repo()
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        out = root / "graphify-out"
        out.mkdir()
        (out / "graph.json").write_text(json.dumps({"nodes": []}), encoding="utf-8")
        (out / "GRAPH_REPORT.md").write_text(f"- Built from commit: `{head}`\n", encoding="utf-8")
        result = inspect(root)
        self.assertEqual(result["graphify"]["state"], "fresh")

    def test_dirty_repo_is_code_stale(self):
        root = self.make_repo()
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        out = root / "graphify-out"
        out.mkdir()
        (out / "graph.json").write_text(json.dumps({"nodes": []}), encoding="utf-8")
        (out / "GRAPH_REPORT.md").write_text(f"- Built from commit: `{head}`\n", encoding="utf-8")
        (root / "a.py").write_text("x = 2\n", encoding="utf-8")
        result = inspect(root)
        self.assertEqual(result["graphify"]["state"], "code_stale")


if __name__ == "__main__":
    unittest.main()

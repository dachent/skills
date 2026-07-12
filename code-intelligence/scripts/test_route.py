#!/usr/bin/env python3
import unittest

from route import decide_route


class RouteTests(unittest.TestCase):
    def test_exact_python_uses_mapper_without_graph(self):
        result = decide_route(
            language="python",
            target_file="pkg/service.py",
            symbol="run",
            graph_state="fresh",
            providers=["code-mapper", "graphify"],
        )
        self.assertEqual(result.primary, "code-mapper")
        self.assertFalse(result.must_load_graph)

    def test_broad_fresh_graph_prefers_codebase_memory_when_available(self):
        result = decide_route(
            language="typescript",
            graph_state="fresh",
            providers=["graphify", "codebase-memory"],
        )
        self.assertEqual(result.primary, "codebase-memory")
        self.assertTrue(result.must_load_graph)

    def test_small_repo_uses_direct_source(self):
        result = decide_route(repo_size="small", providers=["graphify"])
        self.assertEqual(result.primary, "direct-source")

    def test_security_prefers_codeql(self):
        result = decide_route(security_flow=True, providers=["codeql", "semgrep"])
        self.assertEqual(result.primary, "codeql")
        self.assertEqual(result.secondary, ["semgrep"])

    def test_durable_map_routes_to_repo_map(self):
        result = decide_route(durable_map=True)
        self.assertEqual(result.primary, "repo-map-codex")

    def test_stale_graph_falls_back(self):
        result = decide_route(
            language="python",
            graph_state="code_stale",
            providers=["graphify", "code-mapper"],
        )
        self.assertEqual(result.primary, "direct-source")
        self.assertIn("code-mapper", result.secondary)
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()

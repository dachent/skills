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

    def test_exact_non_python_uses_direct_source(self):
        result = decide_route(
            language="typescript",
            target_file="src/service.ts",
            providers=["graphify"],
        )
        self.assertEqual(result.primary, "direct-source")
        self.assertFalse(result.must_load_graph)

    def test_broad_fresh_graph_uses_graphify(self):
        result = decide_route(
            language="typescript",
            graph_state="fresh",
            providers=["graphify"],
        )
        self.assertEqual(result.primary, "graphify")
        self.assertTrue(result.must_load_graph)

    def test_fresh_graph_without_graphify_falls_back(self):
        result = decide_route(graph_state="fresh", providers=[])
        self.assertEqual(result.primary, "direct-source")
        self.assertFalse(result.must_load_graph)

    def test_small_repo_uses_direct_source(self):
        result = decide_route(repo_size="small", providers=["graphify"])
        self.assertEqual(result.primary, "direct-source")

    def test_python_security_uses_mapper_and_codeql(self):
        result = decide_route(
            language="python",
            security_flow=True,
            providers=["code-mapper", "codeql"],
        )
        self.assertEqual(result.primary, "code-mapper")
        self.assertFalse(result.warnings)

    def test_python_security_warns_without_codeql(self):
        result = decide_route(
            language="python",
            security_flow=True,
            providers=["code-mapper"],
        )
        self.assertEqual(result.primary, "code-mapper")
        self.assertTrue(result.warnings)

    def test_unsupported_security_flow_uses_direct_source(self):
        result = decide_route(language="rust", security_flow=True, providers=["graphify"])
        self.assertEqual(result.primary, "direct-source")
        self.assertTrue(result.warnings)

    def test_durable_map_is_not_a_provider_route(self):
        result = decide_route(durable_map=True)
        self.assertEqual(result.primary, "direct-source")
        self.assertTrue(result.warnings)

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

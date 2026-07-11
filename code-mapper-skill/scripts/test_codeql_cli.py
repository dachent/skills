import unittest

import blast_radius


class CliTest(unittest.TestCase):
    def test_defaults(self):
        args = blast_radius.build_parser().parse_args(["repo", "x.py"])
        self.assertEqual(args.codeql, "existing")
        self.assertEqual(args.codeql_intent, "mapping")

    def test_codeql_options(self):
        args = blast_radius.build_parser().parse_args(
            [
                "repo",
                "x.py",
                "--codeql",
                "build",
                "--codeql-intent",
                "value-flow",
                "--codeql-max-build-seconds",
                "12",
                "--codeql-max-db-mb",
                "500",
                "--codeql-max-query-seconds",
                "7",
            ]
        )
        self.assertEqual(args.codeql, "build")
        self.assertEqual(args.codeql_intent, "value-flow")
        self.assertEqual(args.codeql_max_build_seconds, 12.0)
        self.assertEqual(args.codeql_max_db_mb, 500.0)
        self.assertEqual(args.codeql_max_query_seconds, 7.0)

    def test_removed_legacy_flag_is_rejected(self):
        with self.assertRaises(SystemExit):
            blast_radius.build_parser().parse_args(["repo", "x.py", "--skip-relationships"])

    def test_invalid_mode(self):
        with self.assertRaises(SystemExit):
            blast_radius.build_parser().parse_args(["repo", "x.py", "--codeql", "bad"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

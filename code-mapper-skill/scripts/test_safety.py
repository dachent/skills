from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _paths
import bootstrap_env
import resolve_target


class SafetyTest(unittest.TestCase):
    def test_work_root_is_required(self):
        previous = _paths._WORK_ROOT
        _paths._WORK_ROOT = None
        try:
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(ValueError):
                    _paths.configure_work_root()
        finally:
            _paths._WORK_ROOT = previous

    def test_target_cache_stays_under_explicit_work_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            target.mkdir()
            work = root / "session" / ".codex-bootstrap" / "code-mapper"
            _paths.configure_work_root(work)
            cache = _paths.target_cache_dir(target)
            self.assertTrue(_paths.is_within_work_root(cache))
            self.assertFalse(any(target.iterdir()))

    def test_git_url_is_refused_without_subprocess(self):
        with patch("subprocess.run") as run:
            with self.assertRaises(ValueError):
                resolve_target.resolve("https://example.test/private.git")
            run.assert_not_called()

    def test_windows_io_path_uses_extended_length_spelling(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ("long-segment-" * 12)
            path.mkdir()
            value = _paths.io_path(path)
            if os.name == "nt":
                self.assertTrue(value.startswith("\\\\?\\"))
            else:
                self.assertEqual(value, str(path.resolve()))

    def test_dependency_preflight_never_calls_pip(self):
        valid = {
            name: {"available": True, "version": required, "required": required, "matches": True}
            for name, required in bootstrap_env.REQUIRED.items()
        }
        with patch.object(bootstrap_env, "dependency_status", return_value=valid), patch("subprocess.run") as run:
            bootstrap_env.assert_dependencies()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

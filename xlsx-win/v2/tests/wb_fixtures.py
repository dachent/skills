"""Shared helper for building openpyxl workbook fixtures in tests.

Not a test module (no test_ prefix) -- pytest won't collect it. tests/ has
no __init__.py, so pytest adds this directory to sys.path when collecting
any test_*.py here, letting them `import wb_fixtures` directly.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook


def save_workbook(path, populate) -> Path:
    """Create a Workbook, hand it to populate(wb) to mutate, then save it to `path`.

    Returns `path` (as a Path) for convenient chaining.
    """
    path = Path(path)
    wb = Workbook()
    populate(wb)
    wb.save(path)
    return path

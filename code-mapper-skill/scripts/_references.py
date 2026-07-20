"""Jedi-backed symbol reference extraction for the canonical mapper."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import jedi

import _paths

_DEF_RE_TEMPLATE = r"^\s*(?:async\s+def|def|class)\s+({name})\b"


def find_definition_position(file_path: Path, symbol_name: str) -> tuple[int, int]:
    pattern = re.compile(_DEF_RE_TEMPLATE.format(name=re.escape(symbol_name)))
    for lineno, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        match = pattern.match(line)
        if match:
            return lineno, match.start(1)
    raise ValueError(f"definition of {symbol_name!r} not found in {file_path}")


def find_symbol_references(
    package_dir: Path,
    file_path: Path,
    module_dotted: str,
    symbol_name: str,
) -> list[dict[str, Any]]:
    cache_dir = Path(_paths.io_path(_paths.require_work_root() / "jedi"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    jedi.settings.cache_directory = str(cache_dir)
    line, column = find_definition_position(file_path, symbol_name)
    project = jedi.Project(str(package_dir.parent))
    script = jedi.Script(path=str(file_path), project=project)
    records: list[dict[str, Any]] = []
    for reference in script.get_references(line=line, column=column):
        if reference.is_definition() or reference.module_path is None:
            continue
        path = Path(reference.module_path)
        try:
            relative = path.relative_to(package_dir.parent).as_posix()
        except ValueError:
            relative = path.as_posix()
        records.append(
            {
                "symbol": f"{module_dotted}.{symbol_name}",
                "file": relative,
                "line": reference.line,
                "column": reference.column,
                "name": reference.name,
                "type": reference.type,
            }
        )
    return sorted(records, key=lambda item: (item["file"], item["line"], item["column"]))

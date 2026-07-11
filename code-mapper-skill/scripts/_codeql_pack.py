"""Create the minimal local QL pack required for generated Python queries."""
from pathlib import Path

QLPACK = """name: code-mapper/generated-local-flow
version: 0.0.0
dependencies:
  codeql/python-all: "*"
"""

def ensure_query_pack(cache_dir):
    directory=Path(cache_dir)/"codeql"
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/"qlpack.yml"
    if not path.exists() or path.read_text(encoding="utf-8")!=QLPACK:
        path.write_text(QLPACK,encoding="utf-8")
    return path

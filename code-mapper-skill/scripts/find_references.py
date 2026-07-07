"""Symbol-level analysis: find every call site / reference of a function or class."""
import argparse
import re
from pathlib import Path

import jedi

from _paths import JEDI_CACHE_DIR

JEDI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
jedi.settings.cache_directory = str(JEDI_CACHE_DIR)

_DEF_RE_TEMPLATE = r"^\s*(?:def|class)\s+({name})\b"


def module_to_file(target_path: Path, package: str, module_dotted: str) -> Path:
    if module_dotted == package:
        return target_path / "__init__.py"
    assert module_dotted.startswith(package + "."), f"{module_dotted!r} not under package {package!r}"
    rel_parts = module_dotted[len(package) + 1:].split(".")
    base = target_path
    for part in rel_parts[:-1]:
        base = base / part
    candidate = base / (rel_parts[-1] + ".py")
    if candidate.exists():
        return candidate
    candidate_pkg = base / rel_parts[-1] / "__init__.py"
    if candidate_pkg.exists():
        return candidate_pkg
    raise FileNotFoundError(f"no source file found for module {module_dotted!r} (tried {candidate})")


def find_definition_position(file_path: Path, symbol_name: str):
    pattern = re.compile(_DEF_RE_TEMPLATE.format(name=re.escape(symbol_name)))
    for lineno, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        m = pattern.match(line)
        if m:
            return lineno, m.start(1)
    raise ValueError(f"definition of {symbol_name!r} not found in {file_path}")


def render_references(symbol: str, refs) -> str:
    call_sites = sorted(
        (Path(r.module_path).name, r.line, r.column)
        for r in refs
        if not r.is_definition() and r.module_path is not None
    )
    lines = [f"## References to `{symbol}` ({len(call_sites)})", ""]
    if not call_sites:
        lines.append("_none found (jedi is static — dynamic/getattr-based dispatch won't show up here)_")
    else:
        for fname, line, col in call_sites:
            lines.append(f"- `{fname}:{line}` (col {col})")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target_path", help="path to the package directory to analyze")
    ap.add_argument("--package", default=None, help="dotted package name (default: folder name)")
    ap.add_argument("--symbol", required=True, help="dotted symbol, e.g. toy_pkg.b.helper")
    args = ap.parse_args()

    target_path = Path(args.target_path).resolve()
    package = args.package or target_path.name

    *module_parts, symbol_name = args.symbol.split(".")
    module_dotted = ".".join(module_parts)

    file_path = module_to_file(target_path, package, module_dotted)
    line, col = find_definition_position(file_path, symbol_name)

    project = jedi.Project(str(target_path.parent))
    script = jedi.Script(path=str(file_path), project=project)
    refs = script.get_references(line=line, column=col)

    print(render_references(args.symbol, refs))


if __name__ == "__main__":
    main()

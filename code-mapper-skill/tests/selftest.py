"""Plain-assert smoke test against tests/fixtures/toy_pkg. Run: python tests/selftest.py

Fixture ground truth (by construction):
  a -> b, e -> b        (b has no internal imports; a and e call b.helper())
  c -> d, d -> c         (deliberate 2-cycle, unrelated to the helper/caller test)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import _references as refs  # noqa: E402
import blast_radius as br  # noqa: E402
import resolve_target as rt  # noqa: E402
from _graph import build, find_cycles  # noqa: E402

TOY_PKG_DIR = Path(__file__).resolve().parent / "fixtures" / "toy_pkg"


def test_graph_downstream_upstream():
    graph = build(TOY_PKG_DIR, "toy_pkg")
    assert graph.find_downstream_modules("toy_pkg.b") == {"toy_pkg.a", "toy_pkg.e"}
    assert graph.find_upstream_modules("toy_pkg.b") == set()
    assert graph.find_upstream_modules("toy_pkg.c") == {"toy_pkg.d"}
    assert graph.find_downstream_modules("toy_pkg.c") == {"toy_pkg.d"}


def test_cycle_detection():
    graph = build(TOY_PKG_DIR, "toy_pkg")
    cycles = find_cycles(graph)
    assert cycles == [["toy_pkg.c", "toy_pkg.d"]], cycles


def test_find_references():
    # find_definition_position: `def helper():` -> helper starts at col 4 (0-indexed).
    file_path = TOY_PKG_DIR / "b.py"
    line, col = refs.find_definition_position(file_path, "helper")
    assert (line, col) == (1, 4), (line, col)

    # find_symbol_references is the real entry point blast_radius.py drives; it
    # sets the jedi cache dir itself and returns call-site records (definition excluded).
    records = refs.find_symbol_references(TOY_PKG_DIR, file_path, "toy_pkg.b", "helper")
    call_sites = sorted((r["file"], r["line"]) for r in records)
    assert call_sites == [("toy_pkg/a.py", 5), ("toy_pkg/e.py", 5)], call_sites
    assert all(r["symbol"] == "toy_pkg.b.helper" for r in records), records


def test_resolve_target_local_passthrough():
    resolved = rt.resolve(str(TOY_PKG_DIR))
    assert resolved == TOY_PKG_DIR.resolve()

    try:
        rt.resolve("nonexistent-local-path-xyz")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError for a bogus local path")


def test_looks_like_git_url():
    assert rt.looks_like_git_url("https://github.com/org/repo")
    assert rt.looks_like_git_url("git@gitlab.com:org/repo.git")
    assert not rt.looks_like_git_url(str(TOY_PKG_DIR))
    assert not rt.looks_like_git_url("relative/local/path")


def test_module_dotted_for_file():
    assert br.module_dotted_for_file("toy_pkg", "b.py") == "toy_pkg.b"
    assert br.module_dotted_for_file("toy_pkg", "__init__.py") == "toy_pkg"


def main():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"ok: {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    main()

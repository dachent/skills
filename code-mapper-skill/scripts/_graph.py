"""Shared grimp helpers: build an import graph, serialize it, find cycles."""
import sys
from pathlib import Path

import grimp

import _paths


def build(target_path, package=None):
    target_path = Path(target_path).resolve()
    package = package or target_path.name
    parent = str(target_path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    cache_dir = Path(_paths.io_path(_paths.require_work_root() / "grimp"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return grimp.build_graph(package, cache_dir=str(cache_dir))


def graph_to_dict(graph) -> dict:
    modules = sorted(graph.modules)
    edges = [
        {"importer": m, "imported": imp}
        for m in modules
        for imp in sorted(graph.find_modules_directly_imported_by(m))
    ]
    return {"modules": modules, "edges": edges}


def find_cycles(graph) -> list:
    """Tarjan's SCC over the direct-import adjacency. Returns SCCs with >1 module."""
    modules = list(graph.modules)
    adj = {m: graph.find_modules_directly_imported_by(m) for m in modules}

    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = {}
    result = []

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in adj.get(v, ()):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == v:
                    break
            if len(component) > 1:
                result.append(sorted(component))

    for v in modules:
        if v not in index:
            strongconnect(v)

    return result

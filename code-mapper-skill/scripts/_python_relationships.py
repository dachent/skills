"""Python AST relationship extraction; never imports or executes target code."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from _relationship_common import (
    HTTP_CLIENT_PREFIXES, HTTP_METHODS, METHOD_READS, METHOD_WRITES,
    PATH_METHOD_WRITES, READ_CALLS, WRITE_CALLS, _arg, _dedupe_edges,
    _dotted, _edge, _literal, _rel, _sql_edges,
)


class PythonRelationshipVisitor(ast.NodeVisitor):
    def __init__(self, module: str, file_rel: str):
        self.module = module
        self.file_rel = file_rel
        self.scope: list[str] = []
        self.aliases: dict[str, str] = {}
        self.edges: list[dict[str, Any]] = []

    @property
    def source(self) -> str:
        return ".".join([self.module, *self.scope]) if self.scope else self.module

    @property
    def symbol(self) -> str:
        return self.source

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.aliases[alias.asname or alias.name.split(".")[0]] = alias.name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.aliases[alias.asname or alias.name] = f"{module}.{alias.name}".strip(".")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = {_dotted(base, self.aliases) for base in node.bases}
        if any(base and (base.endswith("BaseModel") or base.endswith("TypedDict")) for base in bases):
            self.edges.append(_edge(self.source, "DEFINES_SCHEMA", f"python:{self.module}.{node.name}",
                                    file=self.file_rel, line=node.lineno, symbol=f"{self.module}.{node.name}",
                                    target_type="contract"))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Subscript(self, node: ast.Subscript) -> None:
        owner = _dotted(node.value, self.aliases)
        if owner in {"os.environ", "environ"}:
            value, confidence = _literal(node.slice, self.aliases)
            if value:
                self.edges.append(_edge(self.source, "READS_CONFIG", value, file=self.file_rel,
                                        line=node.lineno, symbol=self.symbol, confidence=confidence,
                                        target_type="config"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _dotted(node.func, self.aliases) or ""
        method = name.rsplit(".", 1)[-1]

        if name in {"open", "builtins.open", "io.open"}:
            target, confidence = _literal(_arg(node, 0, "file"), self.aliases)
            mode, _ = _literal(_arg(node, 1, "mode"), self.aliases)
            if target:
                relation = "WRITES_FILE" if mode and any(flag in mode for flag in "wax+") else "READS_FILE"
                self.edges.append(_edge(self.source, relation, target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))

        if name in READ_CALLS:
            index, kind = READ_CALLS[name]
            target, confidence = _literal(_arg(node, index), self.aliases)
            if target:
                relation = "LOADS_MODEL" if kind == "model" else "READS_FILE"
                self.edges.append(_edge(self.source, relation, target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))
        if name in WRITE_CALLS:
            index, kind = WRITE_CALLS[name]
            target, confidence = _literal(_arg(node, index), self.aliases)
            if target:
                relation = "SAVES_MODEL" if kind == "model" else "WRITES_FILE"
                self.edges.append(_edge(self.source, relation, target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))
        if method in METHOD_READS:
            target, confidence = _literal(node.func.value if isinstance(node.func, ast.Attribute) else None, self.aliases)
            if target:
                self.edges.append(_edge(self.source, "READS_FILE", target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))
        if method in PATH_METHOD_WRITES:
            target, confidence = _literal(node.func.value if isinstance(node.func, ast.Attribute) else None, self.aliases)
            if target:
                self.edges.append(_edge(self.source, "WRITES_FILE", target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))
        if method in METHOD_WRITES:
            index, _ = METHOD_WRITES[method]
            target_node = _arg(node, index)
            target, confidence = _literal(target_node, self.aliases)
            if target:
                self.edges.append(_edge(self.source, "WRITES_FILE", target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))
        if method == "open" and isinstance(node.func, ast.Attribute):
            target, confidence = _literal(node.func.value, self.aliases)
            mode, _ = _literal(_arg(node, 0, "mode"), self.aliases)
            if target:
                relation = "WRITES_FILE" if mode and any(flag in mode for flag in "wax+") else "READS_FILE"
                self.edges.append(_edge(self.source, relation, target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))

        if name in {"pandas.read_sql", "pandas.read_sql_query"}:
            sql, confidence = _literal(_arg(node, 0, "sql"), self.aliases)
            if sql and confidence == "exact":
                self.edges.extend(_sql_edges(sql, self.source, self.file_rel, node.lineno, self.symbol))
        if method == "to_sql":
            table, confidence = _literal(_arg(node, 0, "name"), self.aliases)
            if table:
                self.edges.append(_edge(self.source, "WRITES_TABLE", table, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="dataset"))

        if name in {"os.getenv", "os.environ.get"}:
            target, confidence = _literal(_arg(node, 0), self.aliases)
            if target:
                self.edges.append(_edge(self.source, "READS_CONFIG", target, file=self.file_rel, line=node.lineno,
                                        symbol=self.symbol, confidence=confidence, target_type="config"))

        if any(name.startswith(prefix) for prefix in HTTP_CLIENT_PREFIXES) and method.lower() in HTTP_METHODS:
            target, confidence = _literal(_arg(node, 0, "url"), self.aliases)
            if target:
                self.edges.append(_edge(self.source, "CONSUMES_ENDPOINT", f"{method.upper()} {target}",
                                        file=self.file_rel, line=node.lineno, symbol=self.symbol,
                                        confidence=confidence, target_type="contract"))

        if method in {"execute", "executemany"}:
            sql, confidence = _literal(_arg(node, 0), self.aliases)
            if sql and confidence == "exact":
                self.edges.extend(_sql_edges(sql, self.source, self.file_rel, node.lineno, self.symbol))

        if method in {"publish", "produce", "send"}:
            target, confidence = _literal(_arg(node, 0, "topic"), self.aliases)
            if target:
                self.edges.append(_edge(self.source, "PRODUCES_EVENT", target, file=self.file_rel,
                                        line=node.lineno, symbol=self.symbol, confidence=confidence,
                                        target_type="contract"))
        if method in {"subscribe", "consume"}:
            target, confidence = _literal(_arg(node, 0, "topic"), self.aliases)
            if target:
                self.edges.append(_edge(self.source, "CONSUMES_EVENT", target, file=self.file_rel,
                                        line=node.lineno, symbol=self.symbol, confidence=confidence,
                                        target_type="contract"))
        self.generic_visit(node)

    def _route_from_decorator(self, decorator: ast.AST) -> tuple[str, str, int] | None:
        if not isinstance(decorator, ast.Call):
            return None
        name = _dotted(decorator.func, self.aliases) or ""
        method = name.rsplit(".", 1)[-1].lower()
        if method not in HTTP_METHODS and method != "route":
            return None
        path, confidence = _literal(_arg(decorator, 0, "path"), self.aliases)
        if not path:
            return None
        http_method = method.upper()
        if method == "route":
            for kw in decorator.keywords:
                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)) and kw.value.elts:
                    candidate, _ = _literal(kw.value.elts[0], self.aliases)
                    if candidate:
                        http_method = candidate.upper()
        return f"{http_method} {path}", confidence, decorator.lineno

    def _visit_route_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            route = self._route_from_decorator(decorator)
            if route:
                target, confidence, line = route
                source = f"{self.module}.{'.'.join([*self.scope, node.name])}" if self.scope else f"{self.module}.{node.name}"
                self.edges.append(_edge(source, "IMPLEMENTS_ENDPOINT", target, file=self.file_rel,
                                        line=line, symbol=source, confidence=confidence, target_type="contract"))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
        self._visit_route_function(node)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef


def _module_for_file(path: Path, package_dir: Path, package: str) -> str:
    rel = path.relative_to(package_dir).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join([package, *parts]) if parts else package


def scan_python_file(path: Path, package_dir: Path, package: str, repo_root: Path, data: bytes | None = None) -> dict[str, Any]:
    file_rel = _rel(path, repo_root)
    module = _module_for_file(path, package_dir, package)
    try:
        source = (data if data is not None else path.read_bytes()).decode("utf-8-sig")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        return {"edges": [], "contracts": [], "errors": [{"file": file_rel, "error": str(exc)}]}
    visitor = PythonRelationshipVisitor(module, file_rel)
    visitor.visit(tree)
    return {"edges": _dedupe_edges(visitor.edges), "contracts": [], "errors": []}

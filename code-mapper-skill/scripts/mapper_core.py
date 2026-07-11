from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 2
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".tox", ".nox", ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", "site-packages", "dist", "build", "target",
}
CONTRACT_NAMES = {
    "openapi.yaml", "openapi.yml", "openapi.json", "swagger.yaml",
    "swagger.yml", "swagger.json", "asyncapi.yaml", "asyncapi.yml",
    "asyncapi.json", "catalog-info.yaml", "catalog-info.yml",
}
CONTRACT_SUFFIXES = {".graphql", ".gql", ".proto", ".avsc"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
READ_CALLS = {
    "pandas.read_csv", "pandas.read_parquet", "pandas.read_excel", "pandas.read_json",
    "polars.read_csv", "polars.read_parquet", "joblib.load", "torch.load",
}
WRITE_METHODS = {"to_csv", "to_parquet", "to_excel", "to_json", "to_sql"}
SQL_READ_RE = re.compile(r"\b(?:from|join)\s+([A-Za-z_][\w.$-]*)", re.IGNORECASE)
SQL_WRITE_RE = re.compile(
    r"\b(?:insert\s+into|update|delete\s+from|create\s+table|merge\s+into)\s+([A-Za-z_][\w.$-]*)",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def iter_files(root: Path) -> Iterable[Path]:
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.is_symlink():
                    stack.append(entry)
            elif entry.is_file():
                yield entry


def module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or root.name


def dotted(node: ast.AST | None, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = dotted(node.value, aliases)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def literal(node: ast.AST | None, aliases: dict[str, str]) -> tuple[str | None, str]:
    if node is None:
        return None, "unknown"
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float)):
        return str(node.value), "exact"
    if isinstance(node, ast.Name):
        return "${" + node.id + "}", "inferred"
    if isinstance(node, ast.Attribute):
        name = dotted(node, aliases)
        return ("${" + name + "}" if name else None), "inferred"
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                text, _ = literal(value.value, aliases)
                parts.append(text or "${expr}")
        return "".join(parts), "inferred"
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
        left, lc = literal(node.left, aliases)
        right, rc = literal(node.right, aliases)
        if left is not None and right is not None:
            sep = "/" if isinstance(node.op, ast.Div) else ""
            return left.rstrip("/") + sep + right.lstrip("/"), "exact" if lc == rc == "exact" else "inferred"
    if isinstance(node, ast.Call):
        name = dotted(node.func, aliases)
        if name in {"Path", "pathlib.Path"} and node.args:
            return literal(node.args[0], aliases)
        if name in {"os.path.join", "posixpath.join", "ntpath.join"}:
            values = [literal(item, aliases) for item in node.args]
            if values and all(value is not None for value, _ in values):
                return "/".join(str(value).strip("/") for value, _ in values), (
                    "exact" if all(conf == "exact" for _, conf in values) else "inferred"
                )
    return None, "unknown"


def arg(call: ast.Call, index: int, keyword: str | None = None) -> ast.AST | None:
    if len(call.args) > index:
        return call.args[index]
    if keyword:
        for item in call.keywords:
            if item.arg == keyword:
                return item.value
    return None


def edge(source: str, relationship: str, target: str, file: str, line: int, *, confidence: str = "exact", extractor: str = "python-ast", target_type: str = "symbol") -> dict[str, Any]:
    return {
        "source": source,
        "relationship": relationship,
        "target": target,
        "targetType": target_type,
        "confidence": confidence,
        "evidence": {"file": file, "line": line, "extractor": extractor},
    }


def dedupe_edges(edges: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in edges:
        evidence = item.get("evidence", {})
        key = (item.get("source"), item.get("relationship"), item.get("target"), evidence.get("file"), evidence.get("line"))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return sorted(result, key=lambda item: (
        item["source"], item["relationship"], item["target"],
        item["evidence"].get("file", ""), item["evidence"].get("line", 0),
    ))


class PythonScanner(ast.NodeVisitor):
    def __init__(self, module: str, file_rel: str):
        self.module = module
        self.file_rel = file_rel
        self.aliases: dict[str, str] = {}
        self.scope: list[str] = []
        self.edges: list[dict[str, Any]] = []

    @property
    def source(self) -> str:
        return ".".join([self.module, *self.scope]) if self.scope else self.module

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.aliases[alias.asname or alias.name.split(".")[0]] = alias.name
            self.edges.append(edge(self.source, "IMPORTS", alias.name, self.file_rel, node.lineno, target_type="module"))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        base = "." * node.level + (node.module or "")
        for alias in node.names:
            target = f"{base}.{alias.name}".strip(".")
            self.aliases[alias.asname or alias.name] = target
            self.edges.append(edge(self.source, "IMPORTS", target, self.file_rel, node.lineno, target_type="module"))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        symbol = f"{self.source}.{node.name}"
        self.edges.append(edge(self.module, "DEFINES", symbol, self.file_rel, node.lineno))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        symbol = f"{self.source}.{node.name}"
        self.edges.append(edge(self.module, "DEFINES", symbol, self.file_rel, node.lineno))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = dotted(node.func, self.aliases) or ""
        method = name.rsplit(".", 1)[-1]
        if name:
            self.edges.append(edge(self.source, "CALLS", name, self.file_rel, node.lineno))

        if name in {"open", "builtins.open", "io.open"}:
            target, confidence = literal(arg(node, 0, "file"), self.aliases)
            mode, _ = literal(arg(node, 1, "mode"), self.aliases)
            if target:
                relationship = "WRITES_FILE" if mode and any(flag in mode for flag in "wax+") else "READS_FILE"
                self.edges.append(edge(self.source, relationship, target, self.file_rel, node.lineno, confidence=confidence, target_type="dataset"))

        if name in READ_CALLS:
            target, confidence = literal(arg(node, 0), self.aliases)
            if target:
                relationship = "LOADS_MODEL" if name in {"joblib.load", "torch.load"} else "READS_FILE"
                self.edges.append(edge(self.source, relationship, target, self.file_rel, node.lineno, confidence=confidence, target_type="dataset"))

        if method in WRITE_METHODS:
            target, confidence = literal(arg(node, 0, "name"), self.aliases)
            if target:
                relationship = "WRITES_TABLE" if method == "to_sql" else "WRITES_FILE"
                self.edges.append(edge(self.source, relationship, target, self.file_rel, node.lineno, confidence=confidence, target_type="dataset"))

        if method in {"read_text", "read_bytes", "write_text", "write_bytes", "open"} and isinstance(node.func, ast.Attribute):
            target, confidence = literal(node.func.value, self.aliases)
            if target:
                relationship = "READS_FILE" if method.startswith("read") else "WRITES_FILE"
                if method == "open":
                    mode, _ = literal(arg(node, 0, "mode"), self.aliases)
                    relationship = "WRITES_FILE" if mode and any(flag in mode for flag in "wax+") else "READS_FILE"
                self.edges.append(edge(self.source, relationship, target, self.file_rel, node.lineno, confidence=confidence, target_type="dataset"))

        if name in {"os.getenv", "os.environ.get"}:
            target, confidence = literal(arg(node, 0), self.aliases)
            if target:
                self.edges.append(edge(self.source, "READS_CONFIG", target, self.file_rel, node.lineno, confidence=confidence, target_type="config"))

        if name.startswith(("requests.", "httpx.")) and method.lower() in HTTP_METHODS:
            target, confidence = literal(arg(node, 0, "url"), self.aliases)
            if target:
                self.edges.append(edge(self.source, "CONSUMES_ENDPOINT", f"{method.upper()} {target}", self.file_rel, node.lineno, confidence=confidence, target_type="contract"))

        if method in {"execute", "executemany"}:
            sql, confidence = literal(arg(node, 0), self.aliases)
            if sql and confidence == "exact":
                for table in SQL_READ_RE.findall(sql):
                    self.edges.append(edge(self.source, "READS_TABLE", table, self.file_rel, node.lineno, target_type="dataset"))
                for table in SQL_WRITE_RE.findall(sql):
                    self.edges.append(edge(self.source, "WRITES_TABLE", table, self.file_rel, node.lineno, target_type="dataset"))

        if method in {"publish", "produce", "send"}:
            target, confidence = literal(arg(node, 0, "topic"), self.aliases)
            if target:
                self.edges.append(edge(self.source, "PRODUCES_EVENT", target, self.file_rel, node.lineno, confidence=confidence, target_type="event"))

        if method in {"subscribe", "consume"}:
            target, confidence = literal(arg(node, 0, "topic"), self.aliases)
            if target:
                self.edges.append(edge(self.source, "CONSUMES_EVENT", target, self.file_rel, node.lineno, confidence=confidence, target_type="event"))

        if name in {"subprocess.run", "subprocess.call", "subprocess.Popen"}:
            target, confidence = literal(arg(node, 0), self.aliases)
            if target:
                self.edges.append(edge(self.source, "EXECUTES_PROCESS", target, self.file_rel, node.lineno, confidence=confidence, target_type="process"))

        self.generic_visit(node)


def scan_python(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    relative = path.relative_to(root).as_posix()
    module = module_name(path, root)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        return [], [{"file": relative, "error": str(exc)}]
    scanner = PythonScanner(module, relative)
    scanner.visit(tree)
    return scanner.edges, []


def parse_contract(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    relative = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return [], [], [{"file": relative, "error": str(exc)}]
    source = f"contract:{relative}"
    edges: list[dict[str, Any]] = []
    contracts: list[dict[str, Any]] = []
    suffix = path.suffix.lower()

    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return [], [], [{"file": relative, "error": str(exc)}]
        if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
            contracts.append({"kind": "openapi", "name": relative, "file": relative})
            for route, operations in (data.get("paths") or {}).items():
                if isinstance(operations, dict):
                    for method in operations:
                        if method.lower() in HTTP_METHODS:
                            edges.append(edge(source, "DEFINES_ENDPOINT", f"{method.upper()} {route}", relative, 1, extractor="contract-json", target_type="contract"))
        elif isinstance(data, dict) and "asyncapi" in data:
            contracts.append({"kind": "asyncapi", "name": relative, "file": relative})
            for channel, config in (data.get("channels") or {}).items():
                if isinstance(config, dict):
                    if "publish" in config:
                        edges.append(edge(source, "DEFINES_PUBLISH", channel, relative, 1, extractor="contract-json", target_type="event"))
                    if "subscribe" in config:
                        edges.append(edge(source, "DEFINES_SUBSCRIPTION", channel, relative, 1, extractor="contract-json", target_type="event"))
    elif suffix in {".yaml", ".yml"}:
        if re.search(r"(?m)^\s*(openapi|swagger):", text):
            contracts.append({"kind": "openapi", "name": relative, "file": relative})
            current_path: str | None = None
            for line_number, raw in enumerate(text.splitlines(), 1):
                stripped = raw.strip()
                if stripped.startswith("/") and stripped.endswith(":"):
                    current_path = stripped[:-1]
                elif current_path and stripped[:-1].lower() in HTTP_METHODS and stripped.endswith(":"):
                    edges.append(edge(source, "DEFINES_ENDPOINT", f"{stripped[:-1].upper()} {current_path}", relative, line_number, extractor="contract-yaml", target_type="contract"))
        if "backstage.io/" in text and "metadata:" in text:
            matches = re.findall(r"(?m)^\s*name:\s*['\"]?([^'\"\s]+)", text)
            for item in matches[:1]:
                contracts.append({"kind": "backstage", "name": item, "file": relative})
    elif suffix in {".graphql", ".gql"}:
        contracts.append({"kind": "graphql", "name": relative, "file": relative})
        for kind, item in re.findall(r"(?m)^\s*(type|input|interface|enum|scalar|union)\s+([A-Za-z_]\w*)", text):
            edges.append(edge(source, "DEFINES_SCHEMA", f"{kind}:{item}", relative, 1, extractor="graphql", target_type="contract"))
    elif suffix == ".proto":
        contracts.append({"kind": "protobuf", "name": relative, "file": relative})
        for kind, item in re.findall(r"(?m)^\s*(message|enum|service)\s+([A-Za-z_]\w*)", text):
            relationship = "DEFINES_SERVICE" if kind == "service" else "DEFINES_SCHEMA"
            edges.append(edge(source, relationship, item, relative, 1, extractor="protobuf", target_type="contract"))
    elif suffix == ".avsc":
        contracts.append({"kind": "avro", "name": relative, "file": relative})
    return edges, contracts, []


def is_contract(path: Path) -> bool:
    name = path.name.lower()
    if name in CONTRACT_NAMES or path.suffix.lower() in CONTRACT_SUFFIXES:
        return True
    if path.suffix.lower() == ".json":
        return any(token in name for token in ("schema", "openapi", "swagger", "asyncapi", "pact"))
    return False


def scan_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"repository is not a directory: {root}")
    edges: list[dict[str, Any]] = []
    contracts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    python_files = 0
    for path in sorted(iter_files(root)):
        if path.suffix.lower() == ".py":
            python_files += 1
            new_edges, new_errors = scan_python(path, root)
            edges.extend(new_edges)
            errors.extend(new_errors)
        elif is_contract(path):
            new_edges, new_contracts, new_errors = parse_contract(path, root)
            edges.extend(new_edges)
            contracts.extend(new_contracts)
            errors.extend(new_errors)
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": utc_now(),
        "root": str(root),
        "stats": {"pythonFiles": python_files, "edges": 0, "contracts": len(contracts), "errors": len(errors)},
        "edges": dedupe_edges(edges),
        "contracts": sorted(contracts, key=lambda item: (item["kind"], item["name"], item["file"])),
        "errors": errors,
    }
    result["stats"]["edges"] = len(result["edges"])
    return result

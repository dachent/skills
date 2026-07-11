"""Static parsers for API/schema contracts and Backstage catalog metadata."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _relationship_common import HTTP_METHODS, _dedupe_edges, _edge, _rel


def _yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


def _yaml_inline_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [_yaml_scalar(item) for item in value[1:-1].split(",") if item.strip()]
    return [_yaml_scalar(value)] if value else []


def _backstage_documents(text: str) -> list[dict[str, Any]]:
    documents = []
    for raw_doc in re.split(r"(?m)^---\s*$", text):
        if "backstage.io/" not in raw_doc:
            continue
        doc: dict[str, Any] = {"spec": {}}
        section = None
        list_key = None
        for raw in raw_doc.splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            stripped = raw.strip()
            if indent == 0 and ":" in stripped:
                key, value = stripped.split(":", 1)
                section = key
                list_key = None
                if value.strip():
                    doc[key] = _yaml_scalar(value)
                continue
            if section == "metadata" and indent >= 2 and stripped.startswith("name:"):
                doc["name"] = _yaml_scalar(stripped.split(":", 1)[1])
            if section == "spec" and indent >= 2:
                if list_key == "definition" and "$text:" in stripped:
                    doc["spec"]["definition"] = stripped.split("$text:", 1)[1].strip()
                    continue
                if stripped.startswith("- ") and list_key:
                    doc["spec"].setdefault(list_key, []).append(_yaml_scalar(stripped[2:]))
                    continue
                if ":" in stripped:
                    key, value = stripped.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key in {"providesApis", "consumesApis", "dependsOn", "dependencyOf"}:
                        doc["spec"][key] = _yaml_inline_list(value)
                        list_key = key if not value else None
                    elif key in {"owner", "system", "domain", "type", "definition"}:
                        doc["spec"][key] = _yaml_scalar(value)
                        list_key = "definition" if key == "definition" and value in {"|", ">"} else None
        if doc.get("kind") and doc.get("name"):
            documents.append(doc)
    return documents


def parse_backstage(path: Path, text: str, repo_root: Path) -> dict[str, Any]:
    file_rel = _rel(path, repo_root)
    edges = []
    contracts = []
    for doc in _backstage_documents(text):
        kind = str(doc["kind"])
        name = str(doc["name"])
        source = f"backstage:{kind.lower()}:{name}"
        spec = doc.get("spec", {})
        contracts.append({"kind": f"backstage-{kind.lower()}", "name": name, "file": file_rel})
        for key, relation in (("providesApis", "PROVIDES_API"), ("consumesApis", "CONSUMES_API"),
                              ("dependsOn", "DEPENDS_ON"), ("dependencyOf", "DEPENDENCY_OF")):
            for target in spec.get(key, []) or []:
                edges.append(_edge(source, relation, target, file=file_rel, extractor="backstage-yaml",
                                   target_type="contract" if "Api" in key else "resource"))
        if spec.get("owner"):
            edges.append(_edge(source, "OWNED_BY", spec["owner"], file=file_rel,
                               extractor="backstage-yaml", target_type="owner"))
        for key in ("system", "domain"):
            if spec.get(key):
                edges.append(_edge(source, "PART_OF", spec[key], file=file_rel,
                                   extractor="backstage-yaml", target_type=key))
        if kind.lower() == "api":
            edges.append(_edge(source, "DEFINES_CONTRACT", name, file=file_rel,
                               extractor="backstage-yaml", target_type="contract"))
        definition = spec.get("definition")
        if definition and definition not in {"|", ">"}:
            match = re.search(r"\$text:\s*(\S+)", definition)
            target = match.group(1) if match else definition
            edges.append(_edge(source, "REFERENCES_CONTRACT", target, file=file_rel,
                               extractor="backstage-yaml", target_type="contract"))
    return {"edges": _dedupe_edges(edges), "contracts": contracts, "errors": []}


def _openapi_from_mapping(data: dict[str, Any], file_rel: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    edges = []
    contracts = []
    source = f"contract:{file_rel}"
    for path, operations in (data.get("paths") or {}).items():
        if isinstance(operations, dict):
            for method in operations:
                if method.lower() in HTTP_METHODS:
                    edges.append(_edge(source, "DEFINES_ENDPOINT", f"{method.upper()} {path}",
                                       file=file_rel, extractor="contract-json", target_type="contract"))
    schemas = ((data.get("components") or {}).get("schemas") or {})
    if isinstance(schemas, dict):
        for name in schemas:
            edges.append(_edge(source, "DEFINES_SCHEMA", name, file=file_rel,
                               extractor="contract-json", target_type="contract"))
    contracts.append({"kind": "openapi", "name": file_rel, "file": file_rel})
    return edges, contracts


def _asyncapi_from_mapping(data: dict[str, Any], file_rel: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    edges = []
    source = f"contract:{file_rel}"
    for channel, config in (data.get("channels") or {}).items():
        if isinstance(config, dict):
            if "publish" in config:
                edges.append(_edge(source, "DEFINES_PUBLISH", channel, file=file_rel,
                                   extractor="contract-json", target_type="contract"))
            if "subscribe" in config:
                edges.append(_edge(source, "DEFINES_SUBSCRIPTION", channel, file=file_rel,
                                   extractor="contract-json", target_type="contract"))
    return edges, [{"kind": "asyncapi", "name": file_rel, "file": file_rel}]


def _parse_contract_yaml(text: str, file_rel: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = text.splitlines()
    edges = []
    contracts = []
    source = f"contract:{file_rel}"
    if re.search(r"(?m)^\s*(openapi|swagger):", text):
        contracts.append({"kind": "openapi", "name": file_rel, "file": file_rel})
        paths_indent = None
        current_path = None
        schemas_indent = None
        for lineno, raw in enumerate(lines, 1):
            stripped = raw.strip()
            indent = len(raw) - len(raw.lstrip(" "))
            if stripped == "paths:":
                paths_indent = indent
                current_path = None
                continue
            if paths_indent is not None:
                if stripped and indent <= paths_indent:
                    paths_indent = None
                    current_path = None
                elif indent == paths_indent + 2 and stripped.startswith("/") and stripped.endswith(":"):
                    current_path = stripped[:-1]
                elif current_path and indent == paths_indent + 4 and stripped.endswith(":") and stripped[:-1].lower() in HTTP_METHODS:
                    method = stripped[:-1].upper()
                    edges.append(_edge(source, "DEFINES_ENDPOINT", f"{method} {current_path}", file=file_rel,
                                       line=lineno, extractor="contract-yaml", target_type="contract"))
            if stripped == "schemas:":
                schemas_indent = indent
                continue
            if schemas_indent is not None:
                if stripped and indent <= schemas_indent:
                    schemas_indent = None
                elif stripped.endswith(":") and indent == schemas_indent + 2:
                    name = stripped[:-1]
                    edges.append(_edge(source, "DEFINES_SCHEMA", name, file=file_rel,
                                       line=lineno, extractor="contract-yaml", target_type="contract"))
    if re.search(r"(?m)^\s*asyncapi:", text):
        contracts.append({"kind": "asyncapi", "name": file_rel, "file": file_rel})
        channels_indent = None
        current_channel = None
        for lineno, raw in enumerate(lines, 1):
            stripped = raw.strip()
            indent = len(raw) - len(raw.lstrip(" "))
            if stripped == "channels:":
                channels_indent = indent
                continue
            if channels_indent is not None:
                if stripped and indent <= channels_indent:
                    channels_indent = None
                elif stripped.endswith(":") and indent == channels_indent + 2:
                    current_channel = stripped[:-1]
                elif current_channel and stripped in {"publish:", "subscribe:"}:
                    relation = "DEFINES_PUBLISH" if stripped.startswith("publish") else "DEFINES_SUBSCRIPTION"
                    edges.append(_edge(source, relation, current_channel, file=file_rel, line=lineno,
                                       extractor="contract-yaml", target_type="contract"))
    return edges, contracts


def parse_contract_file(path: Path, repo_root: Path, data: bytes | None = None) -> dict[str, Any]:
    file_rel = _rel(path, repo_root)
    try:
        text = (data if data is not None else path.read_bytes()).decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return {"edges": [], "contracts": [], "errors": [{"file": file_rel, "error": str(exc)}]}
    name = path.name.lower()
    if name.startswith("catalog-info.") or "backstage.io/" in text:
        return parse_backstage(path, text, repo_root)
    edges: list[dict[str, Any]] = []
    contracts: list[dict[str, Any]] = []
    source = f"contract:{file_rel}"
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(text)
            if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
                new_edges, new_contracts = _openapi_from_mapping(data, file_rel)
                edges.extend(new_edges)
                contracts.extend(new_contracts)
            elif isinstance(data, dict) and "asyncapi" in data:
                new_edges, new_contracts = _asyncapi_from_mapping(data, file_rel)
                edges.extend(new_edges)
                contracts.extend(new_contracts)
            elif isinstance(data, dict) and ("$schema" in data or "properties" in data):
                title = str(data.get("title") or path.stem)
                edges.append(_edge(source, "DEFINES_SCHEMA", title, file=file_rel,
                                   extractor="contract-json", target_type="contract"))
                contracts.append({"kind": "json-schema", "name": title, "file": file_rel})
            elif isinstance(data, dict) and ("interactions" in data or "provider" in data or "consumer" in data):
                provider = data.get("provider", {}).get("name", "provider") if isinstance(data.get("provider"), dict) else "provider"
                consumer = data.get("consumer", {}).get("name", "consumer") if isinstance(data.get("consumer"), dict) else "consumer"
                edges.append(_edge(f"pact:{consumer}", "VALIDATES_CONTRACT", f"pact:{provider}", file=file_rel,
                                   extractor="contract-json", target_type="contract"))
                contracts.append({"kind": "pact", "name": f"{consumer}->{provider}", "file": file_rel})
        except json.JSONDecodeError as exc:
            return {"edges": [], "contracts": [], "errors": [{"file": file_rel, "error": str(exc)}]}
    elif suffix in {".yaml", ".yml"}:
        edges, contracts = _parse_contract_yaml(text, file_rel)
    elif suffix in {".graphql", ".gql"}:
        for kind, item in re.findall(r"(?m)^\s*(type|input|interface|enum|scalar|union)\s+([A-Za-z_]\w*)", text):
            edges.append(_edge(source, "DEFINES_SCHEMA", f"{kind}:{item}", file=file_rel,
                               extractor="graphql", target_type="contract"))
        contracts.append({"kind": "graphql", "name": file_rel, "file": file_rel})
    elif suffix == ".proto":
        for kind, item in re.findall(r"(?m)^\s*(message|enum|service)\s+([A-Za-z_]\w*)", text):
            relation = "DEFINES_SERVICE" if kind == "service" else "DEFINES_SCHEMA"
            edges.append(_edge(source, relation, item, file=file_rel, extractor="protobuf", target_type="contract"))
        for rpc in re.findall(r"\brpc\s+([A-Za-z_]\w*)", text):
            edges.append(_edge(source, "DEFINES_RPC", rpc, file=file_rel, extractor="protobuf", target_type="contract"))
        contracts.append({"kind": "protobuf", "name": file_rel, "file": file_rel})
    elif suffix == ".avsc":
        try:
            data = json.loads(text)
            title = str(data.get("name") or path.stem) if isinstance(data, dict) else path.stem
            edges.append(_edge(source, "DEFINES_SCHEMA", title, file=file_rel,
                               extractor="avro", target_type="contract"))
            contracts.append({"kind": "avro", "name": title, "file": file_rel})
        except json.JSONDecodeError as exc:
            return {"edges": [], "contracts": [], "errors": [{"file": file_rel, "error": str(exc)}]}
    return {"edges": _dedupe_edges(edges), "contracts": contracts, "errors": []}

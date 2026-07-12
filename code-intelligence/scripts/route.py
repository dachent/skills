#!/usr/bin/env python3
"""Deterministic routing helper for the code-intelligence skill."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from typing import Iterable


@dataclass
class RouteDecision:
    primary: str
    secondary: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    must_load_graph: bool = False
    requires_source_verification: bool = True


def _available(name: str, providers: set[str]) -> bool:
    return name in providers


def decide_route(
    *,
    question: str = "",
    language: str | None = None,
    target_file: str | None = None,
    symbol: str | None = None,
    repo_size: str = "unknown",
    graph_state: str = "missing",
    providers: Iterable[str] = (),
    security_flow: bool = False,
    artifact_lineage: bool = False,
    durable_map: bool = False,
) -> RouteDecision:
    del question
    available = set(providers)
    lang = (language or "").lower()
    is_python = lang in {"", "python", "py"}
    known_target = bool(target_file or symbol)

    if durable_map:
        return RouteDecision(
            primary="repo-map-codex",
            reasons=["request explicitly requires a durable planning map and evidence catalog"],
        )

    if security_flow:
        if is_python and _available("code-mapper", available):
            warnings = []
            if not _available("codeql", available):
                warnings.append(
                    "CodeQL is unavailable; code-mapper can provide structural evidence but not selective semantic-flow enrichment"
                )
            return RouteDecision(
                primary="code-mapper",
                reasons=["Python security/value-flow work uses the mapper's documented selective CodeQL path"],
                warnings=warnings,
            )
        return RouteDecision(
            primary="direct-source",
            reasons=["no implemented deep-flow route applies to this language or environment"],
            warnings=["verify manually or use a separately approved security-analysis workflow"],
        )

    if artifact_lineage and is_python and _available("code-mapper", available):
        return RouteDecision(
            primary="code-mapper",
            reasons=["Python artifact, contract, API, catalog, or lineage analysis is a mapper specialization"],
        )

    if known_target:
        if is_python and _available("code-mapper", available):
            return RouteDecision(
                primary="code-mapper",
                reasons=["exact Python target is already known; discovery indexing is unnecessary"],
                must_load_graph=False,
            )
        return RouteDecision(
            primary="direct-source",
            reasons=["target is already known and no specialized implemented route is required"],
        )

    if repo_size == "small":
        return RouteDecision(
            primary="direct-source",
            reasons=["small repository does not justify persistent-index overhead by default"],
        )

    if graph_state == "fresh" and _available("graphify", available):
        secondary = ["code-mapper"] if is_python and _available("code-mapper", available) else []
        return RouteDecision(
            primary="graphify",
            secondary=secondary,
            reasons=["broad or unknown-target question can use an existing fresh Graphify graph"],
            must_load_graph=True,
        )

    warning = (
        f"Graphify state is {graph_state}"
        if graph_state in {"code_stale", "semantic_stale", "unknown", "corrupt"}
        else "no usable Graphify graph is available"
    )
    return RouteDecision(
        primary="direct-source",
        secondary=["code-mapper"] if is_python and _available("code-mapper", available) else [],
        reasons=["use current source to discover candidates before specialized analysis"],
        warnings=[warning],
        must_load_graph=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default="")
    parser.add_argument("--language")
    parser.add_argument("--target-file")
    parser.add_argument("--symbol")
    parser.add_argument("--repo-size", choices=("small", "medium", "large", "unknown"), default="unknown")
    parser.add_argument(
        "--graph-state",
        choices=("fresh", "code_stale", "semantic_stale", "unknown", "missing", "corrupt"),
        default="missing",
    )
    parser.add_argument("--providers", default="", help="comma-separated provider names")
    parser.add_argument("--security-flow", action="store_true")
    parser.add_argument("--artifact-lineage", action="store_true")
    parser.add_argument("--durable-map", action="store_true")
    args = parser.parse_args()
    decision = decide_route(
        question=args.question,
        language=args.language,
        target_file=args.target_file,
        symbol=args.symbol,
        repo_size=args.repo_size,
        graph_state=args.graph_state,
        providers=[p.strip() for p in args.providers.split(",") if p.strip()],
        security_flow=args.security_flow,
        artifact_lineage=args.artifact_lineage,
        durable_map=args.durable_map,
    )
    print(json.dumps(asdict(decision), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

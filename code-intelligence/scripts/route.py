#!/usr/bin/env python3
"""Deterministic routing helper for the code-intelligence skill.

Importable policy only -- no CLI. Claude applies this decision tree in-context
by reading references/routing-policy.md; `decide_route` is the executable
reference implementation that test_route.py pins. It was never meant to be
spawned as a subprocess (that cost ~130ms of interpreter+import startup per
call for zero routing benefit), so no `main`/argparse entry point exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
            primary="direct-source",
            reasons=["durable planning is outside the Claude Code provider router"],
            warnings=["use the harness-native planning workflow; no repo-map provider is routed"],
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

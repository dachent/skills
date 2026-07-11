"""Pure decision policy for optional local CodeQL enrichment."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Mapping

CODEQL_MODES = ("off", "existing", "auto", "build")
CODEQL_INTENTS = ("mapping", "value-flow", "security", "deep")
SKIP = "skip"
USE_CACHED_RESULTS = "use-cached-results"
RUN_EXISTING_DATABASE = "run-existing-database"
BUILD_AND_RUN = "build-and-run"
REQUIRE_EXPLICIT_REQUEST = "require-explicit-request"


@dataclass(frozen=True)
class CodeQLDecision:
    action: str
    reason: str
    semantic_score: int
    build_score: int
    hard_trigger: bool
    budget_fits: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _count(mapping: Mapping[str, Any], key: str) -> int:
    try:
        return max(0, int(mapping.get(key, 0)))
    except (TypeError, ValueError):
        return 0


def semantic_need_score(metrics: Mapping[str, Any], intent: str = "mapping") -> int:
    score = (
        5 * min(_count(metrics, "unresolvedSinkArguments"), 10)
        + 4 * min(_count(metrics, "transformedSinkArguments"), 10)
        + 3 * min(_count(metrics, "parameterToSinkCandidates"), 10)
        + 3 * min(_count(metrics, "ambiguousReadWriteModes"), 5)
        + 2 * min(_count(metrics, "dynamicSqlCandidates"), 10)
        + 2 * min(_count(metrics, "unresolvedConfigSources"), 5)
        + min(_count(metrics, "highBranchingTargetFunctions"), 10)
    )
    return score + {"mapping": 0, "value-flow": 8, "security": 12, "deep": 10}.get(intent, 0)


def has_hard_semantic_trigger(metrics: Mapping[str, Any], intent: str = "mapping") -> bool:
    return intent in {"value-flow", "security", "deep"} or _count(metrics, "highValueUnresolvedSinks") > 0


def codeql_build_score(metrics, history, repository, budgets, intent="mapping"):
    score = {"mapping": 0, "value-flow": 6, "security": 8, "deep": 8}.get(intent, 0)
    if _count(metrics, "parameterizedHighValueSinks"):
        score += 4 + min(_count(metrics, "parameterizedHighValueSinks"), 3)
    score += 5 * min(_count(metrics, "highValueUnresolvedSinks"), 3)
    score += 4 * min(_count(history, "codeqlWorthyRuns"), 3)
    score += 3 * min(max(_count(history, "analysisRuns") - 1, 0), 3)
    if repository.get("hasCodeQLConfiguration"):
        score += 2
    if repository.get("temporary"):
        score -= 5
    try:
        invalidation_rate = float(history.get("databaseInvalidationRate", 0.0))
    except (TypeError, ValueError):
        invalidation_rate = 0.0
    if invalidation_rate >= 0.5:
        score -= 4
    if _count(history, "consecutiveFailures"):
        score -= 4
    if float(budgets.get("projectedBuildSeconds", 0) or 0) > float(budgets.get("maxBuildSeconds", 60) or 60):
        score -= 3
    if float(budgets.get("projectedDatabaseMb", 0) or 0) > float(budgets.get("maxDatabaseMb", 1024) or 1024):
        score -= 2
    return score


def build_budget_fits(budgets):
    return (
        float(budgets.get("projectedBuildSeconds", 0) or 0) <= float(budgets.get("maxBuildSeconds", 60) or 60)
        and float(budgets.get("projectedDatabaseMb", 0) or 0) <= float(budgets.get("maxDatabaseMb", 1024) or 1024)
    )


def select_codeql_action(*, mode, intent, metrics, environment, history, repository, budgets) -> CodeQLDecision:
    if mode not in CODEQL_MODES:
        raise ValueError(f"unsupported CodeQL mode: {mode}")
    if intent not in CODEQL_INTENTS:
        raise ValueError(f"unsupported CodeQL intent: {intent}")

    semantic_score = semantic_need_score(metrics, intent)
    hard_trigger = has_hard_semantic_trigger(metrics, intent)
    need = hard_trigger or semantic_score >= int(budgets.get("semanticThreshold", 8))
    build_score = codeql_build_score(metrics, history, repository, budgets, intent)
    budget_fits = build_budget_fits(budgets)

    def decision(action, reason):
        return CodeQLDecision(action, reason, semantic_score, build_score, hard_trigger, budget_fits)

    if mode == "off":
        return decision(SKIP, "CodeQL mode is off")
    if not need and mode != "build":
        return decision(SKIP, f"semantic uncertainty score {semantic_score} is below threshold")
    if environment.get("cachedResultsCurrent"):
        return decision(USE_CACHED_RESULTS, "current cached CodeQL results satisfy the request")
    if not environment.get("codeqlInstalled"):
        return decision(SKIP, "CodeQL CLI is not installed; installation is never automatic")
    if environment.get("previousTimeout") and mode != "build":
        return decision(SKIP, "CodeQL timed out for this source/query fingerprint")
    if environment.get("currentDatabaseExists"):
        return decision(RUN_EXISTING_DATABASE, "a current local CodeQL database is available")
    if not environment.get("buildSupported", True):
        return decision(SKIP, "installed CodeQL version cannot safely create a Python build-mode-none database")
    if mode == "existing":
        return decision(SKIP, "no current CodeQL database exists and existing mode never builds")
    if mode == "build":
        if budget_fits:
            return decision(BUILD_AND_RUN, "explicit build mode requested")
        return decision(REQUIRE_EXPLICIT_REQUEST, "projected CodeQL build exceeds configured budget")

    reuse_justified = (
        intent in {"value-flow", "security", "deep"}
        or repository.get("hasCodeQLConfiguration")
        or _count(history, "codeqlWorthyRuns") >= 2
    )
    automatic_threshold = int(budgets.get("automaticBuildThreshold", 15))
    review_threshold = int(budgets.get("reviewBuildThreshold", 8))
    if intent in {"value-flow", "security", "deep"} and budget_fits:
        return decision(BUILD_AND_RUN, "explicit semantic-analysis intent justifies indexing within budget")
    if build_score >= automatic_threshold and reuse_justified and budget_fits:
        return decision(BUILD_AND_RUN, "semantic demand, reuse, and build budgets justify automatic indexing")
    if build_score >= review_threshold:
        return decision(REQUIRE_EXPLICIT_REQUEST, "CodeQL could add value, but automatic database creation is not sufficiently justified")
    return decision(SKIP, f"database build score {build_score} is below threshold")

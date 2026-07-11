"""Pure decision policy for optional local CodeQL enrichment."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Mapping

CODEQL_MODES=("off","existing","auto","build")
CODEQL_INTENTS=("mapping","value-flow","security","deep")
SKIP="skip"; USE_CACHED_RESULTS="use-cached-results"; RUN_EXISTING_DATABASE="run-existing-database"; BUILD_AND_RUN="build-and-run"; REQUIRE_EXPLICIT_REQUEST="require-explicit-request"

@dataclass(frozen=True)
class CodeQLDecision:
    action:str; reason:str; semantic_score:int; build_score:int; hard_trigger:bool; budget_fits:bool
    def to_dict(self)->dict[str,Any]:return asdict(self)

def _count(m:Mapping[str,Any],key:str)->int:
    try:return max(0,int(m.get(key,0)))
    except (TypeError,ValueError):return 0

def semantic_need_score(metrics:Mapping[str,Any],intent:str="mapping")->int:
    score=(5*min(_count(metrics,"unresolvedSinkArguments"),10)+4*min(_count(metrics,"transformedSinkArguments"),10)+3*min(_count(metrics,"parameterToSinkCandidates"),10)+3*min(_count(metrics,"ambiguousReadWriteModes"),5)+2*min(_count(metrics,"dynamicSqlCandidates"),10)+2*min(_count(metrics,"unresolvedConfigSources"),5)+min(_count(metrics,"highBranchingTargetFunctions"),10))
    return score+{"mapping":0,"value-flow":8,"security":12,"deep":10}.get(intent,0)

def has_hard_semantic_trigger(metrics:Mapping[str,Any],intent:str="mapping")->bool:
    return intent in {"value-flow","security","deep"} or _count(metrics,"highValueUnresolvedSinks")>0

def codeql_build_score(metrics,history,repository,budgets,intent="mapping"):
    score={"mapping":0,"value-flow":6,"security":8,"deep":8}.get(intent,0)
    if _count(metrics,"parameterizedHighValueSinks"):score+=4+min(_count(metrics,"parameterizedHighValueSinks"),3)
    score+=5*min(_count(metrics,"highValueUnresolvedSinks"),3)
    score+=4*min(_count(history,"codeqlWorthyRuns"),3)
    score+=3*min(max(_count(history,"analysisRuns")-1,0),3)
    if repository.get("hasCodeQLConfiguration"):score+=2
    if repository.get("temporary"):score-=5
    try:rate=float(history.get("databaseInvalidationRate",0.0))
    except (TypeError,ValueError):rate=0.0
    if rate>=0.5:score-=4
    if _count(history,"consecutiveFailures"):score-=4
    if float(budgets.get("projectedBuildSeconds",0) or 0)>float(budgets.get("maxBuildSeconds",60) or 60):score-=3
    if float(budgets.get("projectedDatabaseMb",0) or 0)>float(budgets.get("maxDatabaseMb",1024) or 1024):score-=2
    return score

def build_budget_fits(budgets):
    return float(budgets.get("projectedBuildSeconds",0) or 0)<=float(budgets.get("maxBuildSeconds",60) or 60) and float(budgets.get("projectedDatabaseMb",0) or 0)<=float(budgets.get("maxDatabaseMb",1024) or 1024)

def select_codeql_action(*,mode,intent,metrics,environment,history,repository,budgets)->CodeQLDecision:
    if mode not in CODEQL_MODES:raise ValueError(f"unsupported CodeQL mode: {mode}")
    if intent not in CODEQL_INTENTS:raise ValueError(f"unsupported CodeQL intent: {intent}")
    semantic=semantic_need_score(metrics,intent);hard=has_hard_semantic_trigger(metrics,intent);need=hard or semantic>=int(budgets.get("semanticThreshold",8));build_score=codeql_build_score(metrics,history,repository,budgets,intent);fits=build_budget_fits(budgets)
    def d(action,reason):return CodeQLDecision(action,reason,semantic,build_score,hard,fits)
    if mode=="off":return d(SKIP,"CodeQL mode is off")
    if not need and mode!="build":return d(SKIP,f"semantic uncertainty score {semantic} is below threshold")
    if environment.get("cachedResultsCurrent"):return d(USE_CACHED_RESULTS,"current cached CodeQL results satisfy the request")
    if not environment.get("codeqlInstalled"):return d(SKIP,"CodeQL CLI is not installed; installation is never automatic")
    if environment.get("previousTimeout") and mode!="build":return d(SKIP,"CodeQL timed out for this source/query fingerprint")
    if environment.get("currentDatabaseExists"):return d(RUN_EXISTING_DATABASE,"a current local CodeQL database is available")
    if not environment.get("buildSupported",True):return d(SKIP,"installed CodeQL version cannot safely create a Python build-mode-none database")
    if mode=="existing":return d(SKIP,"no current CodeQL database exists and existing mode never builds")
    if mode=="build":return d(BUILD_AND_RUN,"explicit build mode requested") if fits else d(REQUIRE_EXPLICIT_REQUEST,"projected CodeQL build exceeds configured budget")
    reuse=intent in {"value-flow","security","deep"} or repository.get("hasCodeQLConfiguration") or _count(history,"codeqlWorthyRuns")>=2
    automatic=int(budgets.get("automaticBuildThreshold",15));review=int(budgets.get("reviewBuildThreshold",8))
    if intent in {"value-flow","security","deep"} and fits:return d(BUILD_AND_RUN,"explicit semantic-analysis intent justifies indexing within budget")
    if build_score>=automatic and reuse and fits:return d(BUILD_AND_RUN,"semantic demand, reuse, and build budgets justify automatic indexing")
    if build_score>=review:return d(REQUIRE_EXPLICIT_REQUEST,"CodeQL could add value, but automatic database creation is not sufficiently justified")
    return d(SKIP,f"database build score {build_score} is below threshold")

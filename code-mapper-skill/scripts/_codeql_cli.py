"""Shared argparse surface for optional CodeQL enrichment."""
from argparse import ArgumentParser,Namespace
from _codeql_policy import CODEQL_INTENTS,CODEQL_MODES
def add_codeql_arguments(parser:ArgumentParser)->None:
 parser.add_argument("--codeql",choices=CODEQL_MODES,default="existing",help="off, use existing data, conservative auto-build, or explicit build")
 parser.add_argument("--codeql-intent",choices=CODEQL_INTENTS,default="mapping")
 parser.add_argument("--codeql-max-build-seconds",type=float,default=None)
 parser.add_argument("--codeql-max-db-mb",type=float,default=None)
 parser.add_argument("--codeql-max-query-seconds",type=float,default=None)
 parser.add_argument("--allow-codeql-write",action="store_true",help="explicitly permit CodeQL database, query, and cache writes under --work-root")
def budget_overrides(args:Namespace):return {"maxBuildSeconds":args.codeql_max_build_seconds,"maxDatabaseMb":args.codeql_max_db_mb,"maxQuerySeconds":args.codeql_max_query_seconds}

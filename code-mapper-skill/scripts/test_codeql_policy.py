import unittest
from _codeql_policy import *

BASE_METRICS={"unresolvedSinkArguments":1,"transformedSinkArguments":1,"parameterToSinkCandidates":1,"highValueUnresolvedSinks":1,"parameterizedHighValueSinks":1}
BASE_ENV={"cachedResultsCurrent":False,"codeqlInstalled":True,"currentDatabaseExists":False,"previousTimeout":False,"buildSupported":True}
BASE_HISTORY={}
BASE_REPO={"hasCodeQLConfiguration":False,"temporary":False}
BASE_BUDGETS={"semanticThreshold":8,"automaticBuildThreshold":15,"reviewBuildThreshold":8,"projectedBuildSeconds":10,"maxBuildSeconds":60,"projectedDatabaseMb":100,"maxDatabaseMb":1024}

def decide(**overrides):
 args={"mode":"auto","intent":"mapping","metrics":dict(BASE_METRICS),"environment":dict(BASE_ENV),"history":dict(BASE_HISTORY),"repository":dict(BASE_REPO),"budgets":dict(BASE_BUDGETS)}
 args.update(overrides);return select_codeql_action(**args)

class CodeQLPolicyTest(unittest.TestCase):
 def test_off_absolute(self):self.assertEqual(decide(mode="off").action,SKIP)
 def test_low_need_skips(self):self.assertEqual(decide(metrics={}).action,SKIP)
 def test_cached_results_win(self):
  env=dict(BASE_ENV,cachedResultsCurrent=True,codeqlInstalled=False);self.assertEqual(decide(environment=env).action,USE_CACHED_RESULTS)
 def test_existing_database_runs(self):
  env=dict(BASE_ENV,currentDatabaseExists=True);self.assertEqual(decide(mode="existing",environment=env).action,RUN_EXISTING_DATABASE)
 def test_existing_never_builds(self):self.assertEqual(decide(mode="existing").action,SKIP)
 def test_missing_cli_skips(self):self.assertEqual(decide(environment=dict(BASE_ENV,codeqlInstalled=False)).action,SKIP)
 def test_old_cli_skips_build(self):self.assertEqual(decide(mode="build",environment=dict(BASE_ENV,buildSupported=False)).action,SKIP)
 def test_timeout_suppresses_auto(self):self.assertEqual(decide(environment=dict(BASE_ENV,previousTimeout=True)).action,SKIP)
 def test_explicit_build_within_budget(self):self.assertEqual(decide(mode="build").action,BUILD_AND_RUN)
 def test_explicit_build_over_budget(self):
  b=dict(BASE_BUDGETS,projectedBuildSeconds=61);self.assertEqual(decide(mode="build",budgets=b).action,REQUIRE_EXPLICIT_REQUEST)
 def test_explicit_value_flow_auto_builds(self):self.assertEqual(decide(intent="value-flow").action,BUILD_AND_RUN)
 def test_size_alone_never_builds(self):self.assertEqual(decide(metrics={"pythonFiles":5000,"pythonBytes":500_000_000}).action,SKIP)
 def test_repeated_need_can_auto_build(self):
  h={"codeqlWorthyRuns":3,"analysisRuns":4};self.assertEqual(decide(history=h).action,BUILD_AND_RUN)
 def test_temporary_repo_penalized(self):
  score=codeql_build_score(BASE_METRICS,{},dict(BASE_REPO,temporary=True),BASE_BUDGETS);normal=codeql_build_score(BASE_METRICS,{},BASE_REPO,BASE_BUDGETS);self.assertLess(score,normal)
 def test_failures_penalized(self):
  score=codeql_build_score(BASE_METRICS,{"consecutiveFailures":1},BASE_REPO,BASE_BUDGETS);normal=codeql_build_score(BASE_METRICS,{},BASE_REPO,BASE_BUDGETS);self.assertLess(score,normal)
 def test_invalid_mode_intent(self):
  with self.assertRaises(ValueError):decide(mode="bad")
  with self.assertRaises(ValueError):decide(intent="bad")
if __name__=="__main__":unittest.main(verbosity=2)

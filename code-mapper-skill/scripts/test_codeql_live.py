import json,os,shutil,stat,tempfile,time,unittest
from pathlib import Path
from _codeql_pack import ensure_query_pack
from _codeql_runtime import enrich_with_codeql
from _relationships import scan_repository
DIAGNOSTIC=Path(__file__).resolve().parent/"codeql-live-diagnostic.json"
def _robust_rmtree(path):
 # CodeQL leaves database files whose deletion lags on Windows, so a plain rmtree races
 # to WinError 145 ("directory not empty"). Clear read-only bits and retry a few times.
 def onerror(func,p,exc):
  try:os.chmod(p,stat.S_IWRITE);func(p)
  except OSError:pass
 for _ in range(5):
  shutil.rmtree(path,onerror=onerror)
  if not os.path.exists(path):return
  time.sleep(0.3)
class LiveTest(unittest.TestCase):
 def test_real_codeql(self):
  codeql=os.environ.get("CODEQL_CLI") or shutil.which("codeql")
  if not codeql:self.skipTest("CodeQL CLI is not installed")
  enriched={"codeql":{"diagnostic":"not started"}};decision=None;t=tempfile.mkdtemp()
  try:
   root=Path(t)/"repo";pkg=root/"pkg";pkg.mkdir(parents=True);(pkg/"__init__.py").write_text("");(pkg/"io.py").write_text("import pandas as pd\ndef load(root,tenant):\n path=root/f'{tenant}.csv'\n return pd.read_csv(path)\n");cache=Path(t)/"cache";graph=scan_repository(root,pkg,"pkg",cache);ensure_query_pack(cache);enriched,decision=enrich_with_codeql(repo_root=root,cache_dir=cache,graph=graph,mode="build",intent="value-flow",codeql_override=codeql,budget_overrides={"maxBuildSeconds":180,"maxDatabaseMb":1024,"maxQuerySeconds":120,"projectedBuildSeconds":1,"projectedDatabaseMb":50});self.assertEqual(decision.action,"build-and-run");self.assertTrue(enriched["codeql"]["build"]["ok"],enriched["codeql"]["build"]);self.assertTrue(enriched["codeql"]["query"]["ok"],enriched["codeql"]["query"]);self.assertTrue(enriched["semanticEdges"])
  finally:
   payload={"decision":decision.to_dict() if decision else None,"codeql":enriched.get("codeql"),"semanticEdges":enriched.get("semanticEdges",[])};DIAGNOSTIC.write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8");_robust_rmtree(t)
if __name__=="__main__":unittest.main(verbosity=2)

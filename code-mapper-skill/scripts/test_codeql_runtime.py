from __future__ import annotations
import hashlib,json,subprocess,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from _codeql_policy import *
from _codeql_runtime import enrich_with_codeql,generate_targeted_query,supports_safe_python_build
from _relationships import scan_repository

def digest(root):
 h=hashlib.sha256()
 for p in sorted(x for x in root.rglob("*") if x.is_file()):h.update(p.relative_to(root).as_posix().encode());h.update(p.read_bytes())
 return h.hexdigest()
def fixture(root,literal=False):
 pkg=root/"pkg";pkg.mkdir(parents=True);(pkg/"__init__.py").write_text("",encoding="utf-8");arg="'input.csv'" if literal else "root / f'{tenant}.csv'";(pkg/"io.py").write_text("from pathlib import Path\nimport pandas as pd\ndef load(root, tenant):\n    return pd.read_csv("+arg+")\n",encoding="utf-8");return root,pkg
class FakeRunner:
 def __init__(self):self.calls=[];self.mode="ok";self.version="2.20.0"
 def __call__(self,args,**kwargs):
  args=[str(x) for x in args];self.calls.append(args)
  if args[1:2]==["version"]:return subprocess.CompletedProcess(args,0,json.dumps({"version":self.version}),"")
  if args[1:3]==["database","create"]:
   if self.mode=="build-fail":raise subprocess.CalledProcessError(3,args,stderr="build failed")
   if self.mode=="build-timeout":raise subprocess.TimeoutExpired(args,kwargs.get("timeout",0))
   db=Path(args[-1]);db.mkdir(parents=True,exist_ok=True);(db/"marker").write_text("ok");return subprocess.CompletedProcess(args,0,"","")
  if args[1:3]==["query","run"]:
   if self.mode=="query-fail":raise subprocess.CalledProcessError(4,args,stderr="query failed")
   if self.mode=="query-timeout":raise subprocess.TimeoutExpired(args,kwargs.get("timeout",0))
   out=Path(next(x for x in args if x.startswith("--output=")).split("=",1)[1]);out.write_text("bqrs");return subprocess.CompletedProcess(args,0,"","")
  if args[1:3]==["bqrs","decode"]:
   out=Path(next(x for x in args if x.startswith("--output=")).split("=",1)[1]);out.write_text("sinkKind,flowKind,source,sink,file,line\nREADS_FILE,value,parameter root,read_csv,pkg/io.py,4\nREADS_FILE,taint,parameter tenant,read_csv,pkg/io.py,4\n");return subprocess.CompletedProcess(args,0,"","")
  raise AssertionError(args)
 def contains(self,*parts):return any(all(p in call for p in parts) for call in self.calls)
class RuntimeTest(unittest.TestCase):
 def setUp(self):self.runner=FakeRunner();self.p=patch("_codeql_runtime.subprocess.run",side_effect=self.runner);self.p.start();self.addCleanup(self.p.stop)
 def setup_repo(self,temp,literal=False):
  root,pkg=fixture(Path(temp)/"repo",literal);cache=Path(temp)/"cache";graph=scan_repository(root,pkg,"pkg",cache);return root,pkg,cache,graph
 def enrich(self,root,cache,graph,mode="existing",intent="mapping",budgets=None,override="fake-codeql"):
  return enrich_with_codeql(repo_root=root,cache_dir=cache,graph=graph,mode=mode,intent=intent,budget_overrides=budgets,codeql_override=override)
 def test_metrics_and_fingerprint(self):
  with tempfile.TemporaryDirectory() as t:
   _,_,_,g=self.setup_repo(t);m=g["analysisMetrics"];self.assertGreater(m["unresolvedSinkArguments"],0);self.assertGreater(m["transformedSinkArguments"],0);self.assertGreater(m["parameterToSinkCandidates"],0);self.assertTrue(m["selectedSinks"]);self.assertTrue(g["sourceFingerprint"])
 def test_exact_literal_no_trigger(self):
  with tempfile.TemporaryDirectory() as t:
   r,_,c,g=self.setup_repo(t,True);_,d=self.enrich(r,c,g);self.assertEqual(d.action,SKIP);self.assertEqual(self.runner.calls,[])
 def test_targeted_query_has_value_taint_and_location(self):
  q=generate_targeted_query({"selectedSinks":[{"file":"pkg/io.py","line":4,"argumentIndex":0,"relationship":"READS_FILE"}]});self.assertIn('getRelativePath() = "pkg/io.py"',q);self.assertIn("source.flowsTo(argument)",q);self.assertIn("TaintTracking::localTaint",q)
 def test_default_existing_no_probe(self):
  with tempfile.TemporaryDirectory() as t:
   r,_,c,g=self.setup_repo(t);e,d=self.enrich(r,c,g);self.assertEqual(d.action,SKIP);self.assertEqual(self.runner.calls,[]);self.assertEqual(e["semanticEdges"],[])
 def test_safe_version_gate(self):
  self.assertFalse(supports_safe_python_build("2.16.3"));self.assertTrue(supports_safe_python_build("release 2.16.4"));self.assertFalse(supports_safe_python_build("unknown"))
 def test_old_version_never_builds(self):
  with tempfile.TemporaryDirectory() as t:
   r,_,c,g=self.setup_repo(t);self.runner.version="2.16.3";e,d=self.enrich(r,c,g,"build","value-flow");self.assertEqual(d.action,SKIP);self.assertFalse(self.runner.contains("database","create"));self.assertEqual(e["semanticEdges"],[])
 def test_build_read_only_and_outside_target(self):
  with tempfile.TemporaryDirectory() as t:
   r,_,c,g=self.setup_repo(t);before=digest(r);e,d=self.enrich(r,c,g,"build","value-flow");self.assertEqual(d.action,BUILD_AND_RUN);self.assertTrue((c/"codeql"/"database"/"marker").exists());self.assertEqual(before,digest(r));self.assertEqual(len(e["semanticEdges"]),2)
 def test_build_and_decode_commands_safe(self):
  with tempfile.TemporaryDirectory() as t:
   r,_,c,g=self.setup_repo(t);self.enrich(r,c,g,"build","value-flow");build=next(x for x in self.runner.calls if x[1:3]==["database","create"]);decode=next(x for x in self.runner.calls if x[1:3]==["bqrs","decode"]);self.assertIn("--build-mode=none",build);self.assertEqual(build[-2],"--");self.assertIn("--entities=string",decode);self.assertEqual(decode[-2],"--")
 def test_result_cache_avoids_subprocess(self):
  with tempfile.TemporaryDirectory() as t:
   r,_,c,g=self.setup_repo(t);self.enrich(r,c,g,"build","value-flow");n=len(self.runner.calls);e,d=self.enrich(r,c,g,"existing","value-flow");self.assertEqual(d.action,USE_CACHED_RESULTS);self.assertEqual(n,len(self.runner.calls));self.assertTrue(e["codeql"]["cached"])
 def test_source_change_invalidates_but_docs_do_not(self):
  with tempfile.TemporaryDirectory() as t:
   r,p,c,g=self.setup_repo(t);self.enrich(r,c,g,"build","value-flow");(r/"README.md").write_text("docs");same=scan_repository(r,p,"pkg",c);self.runner.calls.clear();_,d=self.enrich(r,c,same,"existing","value-flow");self.assertEqual(d.action,USE_CACHED_RESULTS);time.sleep(.002);(p/"io.py").write_text((p/"io.py").read_text()+"\n# change\n");changed=scan_repository(r,p,"pkg",c);self.runner.calls.clear();_,d=self.enrich(r,c,changed,"build","value-flow");self.assertEqual(d.action,BUILD_AND_RUN);self.assertTrue(self.runner.contains("database","create"))
 def test_failures_preserve_base_map(self):
  for failure in ("build-fail","query-fail"):
   with self.subTest(failure=failure),tempfile.TemporaryDirectory() as t:
    r,_,c,g=self.setup_repo(t);self.runner.mode=failure;e,_=self.enrich(r,c,g,"build","value-flow");self.assertTrue(g["edges"]);self.assertEqual(e["semanticEdges"],[]);self.assertFalse((c/"codeql"/"database-building").exists())
   self.runner=FakeRunner();self.p.stop();self.p=patch("_codeql_runtime.subprocess.run",side_effect=self.runner);self.p.start()
 def test_timeout_suppresses_retry(self):
  with tempfile.TemporaryDirectory() as t:
   r,_,c,g=self.setup_repo(t);self.runner.mode="query-timeout";e,_=self.enrich(r,c,g,"build","value-flow",{"maxQuerySeconds":.1});self.assertTrue(e["codeql"]["query"]["timeout"]);self.runner.mode="ok";self.runner.calls.clear();_,d=self.enrich(r,c,g,"existing","value-flow",{"maxQuerySeconds":.1});self.assertEqual(d.action,SKIP);self.assertFalse(self.runner.contains("query","run"))
if __name__=="__main__":unittest.main(verbosity=2)

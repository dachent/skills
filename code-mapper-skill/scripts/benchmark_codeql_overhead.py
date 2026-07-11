"""Measure semantic-trigger and default-policy overhead without requiring CodeQL."""
import argparse,json,shutil,statistics,tempfile,time
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import _python_relationships
from _codeql_runtime import enrich_with_codeql
from _relationships import scan_repository
def fixture(root,modules,sink_every):
 pkg=root/"pkg";pkg.mkdir(parents=True);(pkg/"__init__.py").write_text("")
 for i in range(modules):
  body="import pandas as pd\ndef load(root,tenant):\n return pd.read_csv(root/f'{tenant}.csv')\n" if sink_every and i%sink_every==0 else f"VALUE={i}\ndef get():return VALUE\n";(pkg/f"m{i}.py").write_text(body)
 return root,pkg
@contextmanager
def baseline_patch():
 with patch.object(_python_relationships.PythonRelationshipVisitor,"_record_signal",lambda *a,**k:None),patch.object(_python_relationships,"_function_complexity",lambda n:1):yield
def sample(fn,runs):
 out=[]
 for _ in range(runs):start=time.perf_counter();fn();out.append(time.perf_counter()-start)
 return out
def summary(v):
 o=sorted(v);return {"medianMs":statistics.median(v)*1000,"p95Ms":o[min(len(o)-1,round(.95*(len(o)-1)))]*1000}
def case(modules,sink_every,runs):
 with tempfile.TemporaryDirectory() as t:
  root,pkg=fixture(Path(t)/"repo",modules,sink_every);base=Path(t)/"base";enh=Path(t)/"enh"
  def cb():shutil.rmtree(base,ignore_errors=True);ctx=baseline_patch();ctx.__enter__();scan_repository(root,pkg,"pkg",base);ctx.__exit__(None,None,None)
  def ce():shutil.rmtree(enh,ignore_errors=True);scan_repository(root,pkg,"pkg",enh)
  with baseline_patch():scan_repository(root,pkg,"pkg",base)
  scan_repository(root,pkg,"pkg",enh)
  def wb():
   with baseline_patch():scan_repository(root,pkg,"pkg",base)
  def we():scan_repository(root,pkg,"pkg",enh)
  graph=scan_repository(root,pkg,"pkg",enh);policy=Path(t)/"policy"
  def dp():enrich_with_codeql(repo_root=root,cache_dir=policy,graph=graph,mode="existing",intent="mapping")
  r={"modules":modules,"sinkEvery":sink_every,"coldBaseline":summary(sample(cb,runs)),"coldEnhanced":summary(sample(ce,runs)),"warmBaseline":summary(sample(wb,runs)),"warmEnhanced":summary(sample(we,runs)),"defaultPolicy":summary(sample(dp,runs))}
  for temp in ("cold","warm"):
   b=r[temp+"Baseline"]["medianMs"];e=r[temp+"Enhanced"]["medianMs"];r[temp+"DeltaMs"]=e-b;r[temp+"DeltaPercent"]=(e/b-1)*100 if b else 0
  return r
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--runs",type=int,default=11);ap.add_argument("--max-delta-percent",type=float,default=10);ap.add_argument("--max-policy-ms",type=float,default=5);ap.add_argument("--no-fail",action="store_true");args=ap.parse_args();cases=[case(m,s,args.runs) for m in (12,122,602) for s in (0,5)];print(json.dumps(cases,indent=2));fail=[]
 for c in cases:
  for temp in ("cold","warm"):
   if c[temp+"DeltaPercent"]>args.max_delta_percent:fail.append(f"{c['modules']}/{c['sinkEvery']} {temp} {c[temp+'DeltaPercent']:.2f}%")
  if c["defaultPolicy"]["medianMs"]>args.max_policy_ms:fail.append(f"policy {c['modules']}/{c['sinkEvery']}")
 if fail and not args.no_fail:raise SystemExit("benchmark gate failed: "+"; ".join(fail))
if __name__=="__main__":main()

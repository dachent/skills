"""Local-only CodeQL discovery, lifecycle, targeted query, and cache integration."""
from __future__ import annotations
import csv,hashlib,json,os,re,shutil,subprocess,tempfile,time
from pathlib import Path
from typing import Any,Mapping
from _codeql_policy import *

QUERY_SCHEMA_VERSION=1;HISTORY_SCHEMA_VERSION=1;DATABASE_SCHEMA_VERSION=1;RESULT_SCHEMA_VERSION=1;MIN_BUILD_MODE_NONE_VERSION=(2,16,4)
DEFAULT_BUDGETS={"semanticThreshold":8,"automaticBuildThreshold":15,"reviewBuildThreshold":8,"maxBuildSeconds":60.0,"maxDatabaseMb":1024.0,"maxQuerySeconds":5.0}

def _read(path,default):
 try:return json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError,TypeError):return default
def _write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(value,indent=2,sort_keys=True),encoding="utf-8");os.replace(tmp,path)
def _hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _ql_string(value):return '"'+value.replace("\\","\\\\").replace('"','\\"')+'"'
def _selected_sinks(metrics):
 out=[]
 for sink in metrics.get("selectedSinks",[]) or []:
  try:index=int(sink.get("argumentIndex",0));line=int(sink.get("line",0))
  except (TypeError,ValueError):continue
  if index<0 or line<=0 or not sink.get("file"):continue
  out.append({"file":str(sink["file"]).replace("\\","/"),"line":line,"argumentIndex":index,"relationship":str(sink.get("relationship","ARTIFACT"))})
 unique={_hash(s):s for s in out};return sorted(unique.values(),key=lambda s:(s["file"],s["line"],s["argumentIndex"],s["relationship"]))
def _query_template():return r'''/**
 * @name Targeted local artifact value and taint flow
 * @kind table
 * @id code-mapper/targeted-local-artifact-flow
 */
import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
/*__SELECTED_ARGUMENTS__*/
from DataFlow::CallCfgNode call, DataFlow::Node argument,
     DataFlow::LocalSourceNode source, string sinkKind, string flowKind
where selectedArgument(call, argument, sinkKind) and
  (flowKind = "value" and source.flowsTo(argument)
   or flowKind = "taint" and TaintTracking::localTaint(source, argument) and not source.flowsTo(argument))
select sinkKind, flowKind, source, call,
  call.getLocation().getFile().getRelativePath(), call.getLocation().getStartLine()
'''
def generate_targeted_query(metrics):
 clauses=[]
 for sink in _selected_sinks(metrics):clauses.append("  (call.getLocation().getFile().getRelativePath() = {file} and call.getLocation().getStartLine() = {line} and argument = call.getArg({index}) and sinkKind = {kind})".format(file=_ql_string(sink["file"]),line=sink["line"],index=sink["argumentIndex"],kind=_ql_string(sink["relationship"])))
 predicate="predicate selectedArgument(DataFlow::CallCfgNode call, DataFlow::Node argument, string sinkKind) {\n"+("\n  or\n".join(clauses) if clauses else "  none()")+"\n}"
 return _query_template().replace("/*__SELECTED_ARGUMENTS__*/",predicate)
def _query_hash():return hashlib.sha256(_query_template().encode()).hexdigest()
def load_history(d):
 h=_read(d/"history.json",{});return h if h.get("schemaVersion")==HISTORY_SCHEMA_VERSION else {"schemaVersion":HISTORY_SCHEMA_VERSION}
def save_history(d,h):payload=dict(h);payload["schemaVersion"]=HISTORY_SCHEMA_VERSION;_write(d/"history.json",payload)
def repository_signals(root):
 wf=root/".github"/"workflows";configured=any(wf.glob("*codeql*.yml")) or any(wf.glob("*codeql*.yaml")) or any((root/name).exists() for name in ("codeql-config.yml","codeql-config.yaml",".github/codeql-config.yml",".github/codeql-config.yaml"));temp=Path(tempfile.gettempdir()).resolve()
 try:temporary=root.resolve().is_relative_to(temp)
 except AttributeError:temporary=str(root.resolve()).startswith(str(temp))
 return {"hasCodeQLConfiguration":configured,"temporary":temporary}
def projected_budgets(metrics,history,overrides=None):
 b=dict(DEFAULT_BUDGETS);mb=float(metrics.get("pythonBytes",0) or 0)/1_000_000;b["projectedBuildSeconds"]=float(history.get("lastBuildSeconds",0) or max(5.0,mb*3));b["projectedDatabaseMb"]=float(history.get("lastDatabaseMb",0) or max(50.0,mb*8))
 for k,v in (overrides or {}).items():
  if v is not None:b[k]=v
 return b
def codeql_version(codeql,timeout=5.0):
 try:
  result=subprocess.run([codeql,"version","--format=json"],capture_output=True,text=True,timeout=timeout,check=True);obj=json.loads(result.stdout);return str(obj.get("version") or obj.get("versionNumber") or "unknown")
 except (subprocess.SubprocessError,json.JSONDecodeError,OSError):
  try:
   result=subprocess.run([codeql,"version"],capture_output=True,text=True,timeout=timeout,check=True);return result.stdout.strip().splitlines()[0] if result.stdout.strip() else "unknown"
  except (subprocess.SubprocessError,OSError):return "unknown"
def codeql_version_tuple(version):
 match=re.search(r"(\d+)\.(\d+)\.(\d+)",version);return tuple(int(x) for x in match.groups()) if match else None
def supports_safe_python_build(version):
 parsed=codeql_version_tuple(version);return parsed is not None and parsed>=MIN_BUILD_MODE_NONE_VERSION
def _db_meta(d):return _read(d/"database-metadata.json",{})
def database_is_current(d,root,fingerprint,version):
 m=_db_meta(d);return (d/"database").is_dir() and m.get("schemaVersion")==DATABASE_SCHEMA_VERSION and m.get("repoRoot")==str(root.resolve()) and m.get("sourceFingerprint")==fingerprint and m.get("codeqlVersion")==version
def _result_key(fingerprint,version,query_hash,sinks):return _hash({"schemaVersion":RESULT_SCHEMA_VERSION,"sourceFingerprint":fingerprint,"codeqlVersion":version,"queryHash":query_hash,"sinks":sinks})
def _cached(d,key):
 p=_read(d/"results.json",{});return p if p.get("schemaVersion")==RESULT_SCHEMA_VERSION and p.get("key")==key else None
def _size_mb(path):
 total=0
 for child in path.rglob("*") if path.exists() else []:
  try:
   if child.is_file():total+=child.stat().st_size
  except OSError:pass
 return total/1_000_000
def build_database(codeql,root,d,fingerprint,version,timeout):
 if not supports_safe_python_build(version):return {"ok":False,"timeout":False,"error":f"CodeQL {version} lacks required safe Python --build-mode=none support (minimum 2.16.4)"}
 d.mkdir(parents=True,exist_ok=True);database=d/"database";tmp=d/"database-building";shutil.rmtree(tmp,ignore_errors=True);started=time.perf_counter();cmd=[codeql,"database","create","--language=python",f"--source-root={root.resolve()}","--build-mode=none","--overwrite","--",str(tmp)]
 try:subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=True)
 except subprocess.TimeoutExpired:shutil.rmtree(tmp,ignore_errors=True);return {"ok":False,"timeout":True,"error":f"CodeQL database build exceeded {timeout:.1f}s"}
 except (subprocess.CalledProcessError,OSError) as exc:shutil.rmtree(tmp,ignore_errors=True);return {"ok":False,"timeout":False,"error":(getattr(exc,"stderr","") or str(exc)).strip()}
 elapsed=time.perf_counter()-started;shutil.rmtree(database,ignore_errors=True);os.replace(tmp,database);meta={"schemaVersion":DATABASE_SCHEMA_VERSION,"repoRoot":str(root.resolve()),"sourceFingerprint":fingerprint,"codeqlVersion":version,"buildSeconds":elapsed,"databaseMb":_size_mb(database),"buildMode":"none"};_write(d/"database-metadata.json",meta);return {"ok":True,"timeout":False,**meta}

def _codeql_search_path(codeql):
 p=Path(codeql).resolve()
 for candidate in (p.parent/"qlpacks",p.parent.parent/"qlpacks"):
  if candidate.is_dir():return candidate
 env=os.environ.get("CODEQL_SEARCH_PATH")
 return Path(env) if env else None

def _parse_csv(path):
 try:
  with path.open("r",encoding="utf-8-sig",newline="") as f:rows=list(csv.reader(f))
 except OSError:return []
 if not rows:return []
 start=1 if rows[0] and any(c.lower() in {"sinkkind","flowkind"} for c in rows[0]) else 0;out=[]
 for row in rows[start:]:
  if len(row)<6:continue
  out.append({"sinkKind":row[0],"flowKind":row[1],"source":row[2],"sink":row[3],"file":row[4].replace("\\","/"),"line":int(row[5]) if row[5].isdigit() else row[5]})
 return out
def run_query(codeql,d,metrics,key,timeout):
 db=d/"database";query=d/"targeted-local-artifact-flow.ql";bqrs=d/"targeted-local-artifact-flow.bqrs";csv_path=d/"targeted-local-artifact-flow.csv";query.write_text(generate_targeted_query(metrics),encoding="utf-8");started=time.perf_counter()
 try:
  cmd=[codeql,"query","run",f"--database={db}",f"--output={bqrs}"];search=_codeql_search_path(codeql);cmd.extend([f"--search-path={search}"] if search else []);cmd.extend(["--",str(query)]);subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=True)
  subprocess.run([codeql,"bqrs","decode","--format=csv","--entities=string",f"--output={csv_path}","--",str(bqrs)],capture_output=True,text=True,timeout=timeout,check=True)
 except subprocess.TimeoutExpired:return {"ok":False,"timeout":True,"error":f"CodeQL query exceeded {timeout:.1f}s"}
 except (subprocess.CalledProcessError,OSError) as exc:return {"ok":False,"timeout":False,"error":(getattr(exc,"stderr","") or str(exc)).strip()}
 payload={"schemaVersion":RESULT_SCHEMA_VERSION,"key":key,"querySeconds":time.perf_counter()-started,"rows":_parse_csv(csv_path)};_write(d/"results.json",payload);return {"ok":True,"timeout":False,**payload}
def _semantic_edges(rows):
 seen=set();out=[]
 for row in rows:
  rel="VALUE_FLOWS_TO" if row.get("flowKind")=="value" else "INFLUENCES";target=f"{row.get('sinkKind')}@{row.get('file')}:{row.get('line')}";key=(row.get("source"),rel,target)
  if key in seen:continue
  seen.add(key);out.append({"source":str(row.get("source")),"relationship":rel,"target":target,"targetType":"semantic-sink","confidence":"semantic","evidence":{"file":str(row.get("file")),"line":row.get("line"),"extractor":"codeql-local-flow" if rel=="VALUE_FLOWS_TO" else "codeql-local-taint"}})
 return out
def _record(history,worthy,decision,build=None,query=None):
 history["analysisRuns"]=int(history.get("analysisRuns",0))+1
 if worthy:history["codeqlWorthyRuns"]=int(history.get("codeqlWorthyRuns",0))+1
 history["lastDecision"]=decision.to_dict()
 for kind,result in (("build",build),("query",query)):
  if not result:continue
  if result.get("ok"):
   history[kind+"s"]=int(history.get(kind+"s",0))+1;history["consecutiveFailures"]=0
   if kind=="build":history["lastBuildSeconds"]=result.get("buildSeconds",0);history["lastDatabaseMb"]=result.get("databaseMb",0)
   else:history["lastQuerySeconds"]=result.get("querySeconds",0);history["usefulFindings"]=int(history.get("usefulFindings",0))+len(result.get("rows",[]))
  else:history["consecutiveFailures"]=int(history.get("consecutiveFailures",0))+1

def metrics_from_graph(graph):
 metrics=dict(graph.get("analysisMetrics",{}))
 if metrics.get("selectedSinks"):return metrics
 selected=[];unresolved=transformed=parameterized=high=dynamic_sql=0;high_rel={"WRITES_FILE","READS_TABLE","WRITES_TABLE","LOADS_MODEL","CONSUMES_ENDPOINT","PRODUCES_EVENT","EXECUTES_PROCESS"}
 for edge in graph.get("edges",[]):
  confidence=edge.get("confidence");target=str(edge.get("target",""));relation=str(edge.get("relationship",""));evidence=edge.get("evidence",{})
  if confidence not in {"inferred","unknown"} and "${" not in target:continue
  unresolved+=1
  if "${" in target:parameterized+=1
  if relation in high_rel:high+=1
  if relation in {"READS_TABLE","WRITES_TABLE"}:dynamic_sql+=1
  selected.append({"file":evidence.get("file",""),"line":evidence.get("line",0),"argumentIndex":0,"relationship":relation})
 metrics.update({"unresolvedSinkArguments":unresolved,"transformedSinkArguments":transformed,"parameterToSinkCandidates":parameterized,"ambiguousReadWriteModes":0,"dynamicSqlCandidates":dynamic_sql,"unresolvedConfigSources":0,"highBranchingTargetFunctions":0,"highValueUnresolvedSinks":high,"parameterizedHighValueSinks":sum(1 for e in selected if e["relationship"] in high_rel),"selectedSinks":selected,"pythonBytes":metrics.get("pythonBytes",0)})
 return metrics

def enrich_with_codeql(*,repo_root,cache_dir,graph,mode="existing",intent="mapping",budget_overrides=None,codeql_override=None):
 if mode not in CODEQL_MODES:raise ValueError(f"unsupported CodeQL mode: {mode}")
 if intent not in CODEQL_INTENTS:raise ValueError(f"unsupported CodeQL intent: {intent}")
 root=Path(repo_root).resolve();d=Path(cache_dir)/"codeql";metrics=metrics_from_graph(graph);history=load_history(d);repo=repository_signals(root);budgets=projected_budgets(metrics,history,budget_overrides);score=semantic_need_score(metrics,intent);worthy=has_hard_semantic_trigger(metrics,intent) or score>=int(budgets["semanticThreshold"]);sinks=_selected_sinks(metrics);qh=_query_hash();fingerprint=str(graph.get("sourceFingerprint",""));stored=str(_db_meta(d).get("codeqlVersion","unknown"));key=_result_key(fingerprint,stored,qh,sinks);cached=_cached(d,key);timeout_fp=_hash({"source":fingerprint,"query":qh,"sinks":sinks});timed_out=history.get("lastTimeoutFingerprint")==timeout_fp
 def finish(decision,rows=None,cached_flag=False,build=None,query=None):
  rows=rows or [];graph["codeql"]={"decision":decision.to_dict(),"rows":rows,"cached":cached_flag,"build":build,"query":query};graph["semanticEdges"]=_semantic_edges(rows);_record(history,worthy,decision,build,query);save_history(d,history);return graph,decision
 if mode=="off" or (not worthy and mode!="build"):
  decision=select_codeql_action(mode=mode,intent=intent,metrics=metrics,environment={"cachedResultsCurrent":False,"codeqlInstalled":True,"currentDatabaseExists":False,"previousTimeout":timed_out},history=history,repository=repo,budgets=budgets);return finish(decision)
 if cached:
  decision=select_codeql_action(mode=mode,intent=intent,metrics=metrics,environment={"cachedResultsCurrent":True,"codeqlInstalled":False,"currentDatabaseExists":False,"previousTimeout":timed_out},history=history,repository=repo,budgets=budgets);return finish(decision,cached.get("rows",[]),True)
 if mode=="existing" and not (d/"database").is_dir():
  decision=select_codeql_action(mode=mode,intent=intent,metrics=metrics,environment={"cachedResultsCurrent":False,"codeqlInstalled":True,"currentDatabaseExists":False,"previousTimeout":timed_out},history=history,repository=repo,budgets=budgets);return finish(decision)
 codeql=codeql_override or shutil.which("codeql")
 if not codeql:
  decision=select_codeql_action(mode=mode,intent=intent,metrics=metrics,environment={"cachedResultsCurrent":False,"codeqlInstalled":False,"currentDatabaseExists":False,"previousTimeout":timed_out,"buildSupported":False},history=history,repository=repo,budgets=budgets);return finish(decision)
 version=codeql_version(codeql);current=database_is_current(d,root,fingerprint,version);key=_result_key(fingerprint,version,qh,sinks);cached=_cached(d,key);env={"cachedResultsCurrent":cached is not None,"codeqlInstalled":True,"currentDatabaseExists":current,"previousTimeout":timed_out,"buildSupported":supports_safe_python_build(version)};decision=select_codeql_action(mode=mode,intent=intent,metrics=metrics,environment=env,history=history,repository=repo,budgets=budgets);build=query=None;rows=[]
 if decision.action==USE_CACHED_RESULTS:rows=cached.get("rows",[]) if cached else []
 elif decision.action==BUILD_AND_RUN:
  build=build_database(codeql,root,d,fingerprint,version,float(budgets["maxBuildSeconds"]))
  if build.get("ok"):query=run_query(codeql,d,metrics,key,float(budgets["maxQuerySeconds"]));rows=query.get("rows",[]) if query.get("ok") else []
 elif decision.action==RUN_EXISTING_DATABASE:
  query=run_query(codeql,d,metrics,key,float(budgets["maxQuerySeconds"]));rows=query.get("rows",[]) if query.get("ok") else []
 if (build and build.get("timeout")) or (query and query.get("timeout")):history["lastTimeoutFingerprint"]=timeout_fp
 return finish(decision,rows,decision.action==USE_CACHED_RESULTS,build,query)
def render_codeql_section(graph):
 c=graph.get("codeql",{});d=c.get("decision",{});edges=graph.get("semanticEdges",[]);lines=["## CodeQL semantic enrichment","",f"- Action: `{d.get('action','skip')}`",f"- Reason: {d.get('reason','not evaluated')}",f"- Semantic score: {d.get('semantic_score',0)}",f"- Database build score: {d.get('build_score',0)}",f"- Semantic edges: {len(edges)}"]
 if c.get("build") and not c["build"].get("ok"):lines.append(f"- Build warning: {c['build'].get('error','failed')}")
 if c.get("query") and not c["query"].get("ok"):lines.append(f"- Query warning: {c['query'].get('error','failed')}")
 for edge in edges[:25]:lines.append(f"- `{edge['relationship']}`: `{edge['source']}` → `{edge['target']}`")
 return "\n".join(lines)

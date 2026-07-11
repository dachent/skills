"""Fast local orchestration for artifacts, contracts, lineage, and CodeQL trigger evidence."""
from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Iterable
from _contract_relationships import parse_contract_file
from _python_relationships import scan_python_file
from _relationship_common import _dedupe_edges,_dedupe_signals
SCHEMA_VERSION=2
PRODUCER="https://github.com/dachent/skills/tree/main/code-mapper-skill"
OPENLINEAGE_SCHEMA="https://openlineage.io/spec/2-0-2/OpenLineage.json"
SKIP_DIRS={".git",".hg",".svn",".tox",".nox",".venv","venv","env","__pycache__",".mypy_cache",".pytest_cache",".ruff_cache","node_modules","site-packages","dist","build","target",".dep-map-cache"}
CONTRACT_NAMES={"openapi.yaml","openapi.yml","openapi.json","swagger.yaml","swagger.yml","swagger.json","asyncapi.yaml","asyncapi.yml","asyncapi.json","catalog-info.yaml","catalog-info.yml"}
CONTRACT_SUFFIXES=(".graphql",".gql",".proto",".avsc")
def _utc_now():return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def _rel(path,root):
 try:return path.relative_to(root).as_posix()
 except ValueError:return path.as_posix()
def _iter_files(root,predicate)->Iterable[Path]:
 stack=[root]
 while stack:
  current=stack.pop()
  try:entries=list(current.iterdir())
  except OSError:continue
  for entry in entries:
   if entry.is_dir():
    if entry.name not in SKIP_DIRS and not entry.is_symlink():stack.append(entry)
   elif predicate(entry):yield entry
def _python_files(package):return sorted(_iter_files(package,lambda p:p.suffix.lower()==".py"))
def _contract_files(root):
 def wanted(path):
  name=path.name.lower();suffix=path.suffix.lower()
  if name in CONTRACT_NAMES or name.startswith("catalog-info.") or suffix in CONTRACT_SUFFIXES:return True
  if suffix==".json":return any(t in name for t in ("schema","openapi","swagger","asyncapi","pact"))
  if suffix in {".yaml",".yml"}:return any(t in name for t in ("openapi","swagger","asyncapi","catalog"))
  return False
 return sorted(_iter_files(root,wanted))
def _sha256(data):return hashlib.sha256(data).hexdigest()
def _source_fingerprint(files):
 rows=[f"{n}:{e.get('sha256','')}" for n,e in files.items() if e.get("kind")=="python"]
 return hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest()
def _analysis_metrics(signals,files):
 complex_sources={s.get("source") for s in signals if int(s.get("functionComplexity",1))>=10}
 selected=[{"file":s.get("file"),"line":s.get("line"),"argumentIndex":s.get("argumentIndex",0),"source":s.get("source"),"relationship":s.get("relationship")} for s in signals if s.get("unresolved") or s.get("transformed") or s.get("parameterToSink")]
 return {"unresolvedSinkArguments":sum(bool(s.get("unresolved")) for s in signals),"transformedSinkArguments":sum(bool(s.get("transformed")) for s in signals),"parameterToSinkCandidates":sum(bool(s.get("parameterToSink")) for s in signals),"ambiguousReadWriteModes":sum(bool(s.get("ambiguousReadWriteMode")) for s in signals),"dynamicSqlCandidates":sum(bool(s.get("dynamicSql")) for s in signals),"unresolvedConfigSources":sum(bool(s.get("unresolvedConfig")) for s in signals),"highBranchingTargetFunctions":len(complex_sources),"highValueUnresolvedSinks":sum(bool(s.get("highValue") and s.get("unresolved")) for s in signals),"parameterizedHighValueSinks":sum(bool(s.get("highValue") and s.get("parameterToSink")) for s in signals),"selectedSinks":selected,"pythonFiles":sum(e.get("kind")=="python" for e in files.values()),"pythonBytes":sum(int(e.get("size",0)) for e in files.values() if e.get("kind")=="python")}
def _dataset_namespace(edge):
 rel=edge["relationship"];target=edge["target"]
 if "TABLE" in rel:return "database"
 if target.startswith(("s3://","gs://","az://")):return target.split(":",1)[0]
 if rel in {"LOADS_MODEL","SAVES_MODEL"}:return "model"
 return "file"
def to_openlineage_job_events(edges,event_time=None):
 event_time=event_time or _utc_now();grouped={};inputs={"READS_FILE","READS_TABLE","LOADS_MODEL"};outputs={"WRITES_FILE","WRITES_TABLE","SAVES_MODEL"}
 for edge in edges:
  rel=edge["relationship"]
  if rel not in inputs|outputs:continue
  bucket=grouped.setdefault(edge["source"],{"inputs":[],"outputs":[]});dataset={"namespace":_dataset_namespace(edge),"name":edge["target"]};key="inputs" if rel in inputs else "outputs"
  if dataset not in bucket[key]:bucket[key].append(dataset)
 return [{"eventTime":event_time,"producer":PRODUCER,"schemaURL":OPENLINEAGE_SCHEMA,"job":{"namespace":"code-mapper","name":job},"inputs":sorted(ds["inputs"],key=lambda d:(d["namespace"],d["name"])),"outputs":sorted(ds["outputs"],key=lambda d:(d["namespace"],d["name"]))} for job,ds in sorted(grouped.items())]
def scan_repository(repo_root,package_dir,package,cache_dir):
 repo_root=Path(repo_root).resolve();package_dir=Path(package_dir).resolve();cache_dir=Path(cache_dir);cache_dir.mkdir(parents=True,exist_ok=True);cache_file=cache_dir/"relationship-cache.json"
 try:
  cache=json.loads(cache_file.read_text(encoding="utf-8"))
  if cache.get("schemaVersion")!=SCHEMA_VERSION:cache={"schemaVersion":SCHEMA_VERSION,"files":{}}
 except (OSError,json.JSONDecodeError):cache={"schemaVersion":SCHEMA_VERSION,"files":{}}
 old=cache.get("files",{});candidates=[(p,"python") for p in _python_files(package_dir)];seen={p for p,_ in candidates};candidates.extend((p,"contract") for p in _contract_files(repo_root) if p not in seen)
 info=[];unchanged=len(candidates)==len(old);pre_errors=[]
 for path,kind in candidates:
  rel=_rel(path,repo_root)
  try:stat=path.stat()
  except OSError as exc:pre_errors.append({"file":rel,"error":str(exc)});unchanged=False;continue
  info.append((path,kind,rel,stat));cached=old.get(rel)
  if not cached or cached.get("size")!=stat.st_size or cached.get("mtimeNs")!=stat.st_mtime_ns or cached.get("kind")!=kind:unchanged=False
 aggregate=cache.get("aggregate")
 if unchanged and aggregate and not pre_errors:
  graph=dict(aggregate);graph["stats"]=dict(graph.get("stats",{}));graph["stats"].update({"candidateFiles":len(candidates),"parsedFiles":0,"cacheHits":len(candidates),"edges":len(graph.get("edges",[])),"contracts":len(graph.get("contracts",[]))});return graph
 new={};all_edges=[];all_contracts=[];all_signals=[];errors=list(pre_errors);parsed=hits=0
 for path,kind,rel,stat in info:
  cached=old.get(rel)
  if cached and cached.get("size")==stat.st_size and cached.get("mtimeNs")==stat.st_mtime_ns and cached.get("kind")==kind:result=cached.get("result",{});digest=cached.get("sha256");hits+=1
  else:
   try:data=path.read_bytes();digest=_sha256(data)
   except OSError as exc:errors.append({"file":rel,"error":str(exc)});continue
   if cached and cached.get("sha256")==digest and cached.get("kind")==kind:result=cached.get("result",{});hits+=1
   else:result=scan_python_file(path,package_dir,package,repo_root,data) if kind=="python" else parse_contract_file(path,repo_root,data);parsed+=1
  new[rel]={"kind":kind,"size":stat.st_size,"mtimeNs":stat.st_mtime_ns,"sha256":digest,"result":result};all_edges.extend(result.get("edges",[]));all_contracts.extend(result.get("contracts",[]));all_signals.extend(result.get("signals",[]));errors.extend(result.get("errors",[]))
 edges=_dedupe_edges(all_edges);signals=_dedupe_signals(all_signals);contracts=sorted(all_contracts,key=lambda c:(c.get("kind",""),c.get("name",""),c.get("file","")));generated=_utc_now()
 graph={"schemaVersion":SCHEMA_VERSION,"generatedAt":generated,"root":str(repo_root),"package":package,"sourceFingerprint":_source_fingerprint(new),"edges":edges,"contracts":contracts,"analysisSignals":signals,"analysisMetrics":_analysis_metrics(signals,new),"errors":errors,"stats":{"candidateFiles":len(candidates),"parsedFiles":parsed,"cacheHits":hits,"edges":len(edges),"contracts":len(contracts)}}
 events=to_openlineage_job_events(edges,generated);graph["openLineageEvents"]=len(events);payload={"schemaVersion":SCHEMA_VERSION,"files":new,"aggregate":graph};cache_file.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8");(cache_dir/"relationships.json").write_text(json.dumps(graph,indent=2,sort_keys=True),encoding="utf-8");(cache_dir/"openlineage-job-events.json").write_text(json.dumps(events,indent=2,sort_keys=True),encoding="utf-8");return graph
def render_relationships(module,graph):
 edges=[e for e in graph.get("edges",[]) if e.get("source")==module or str(e.get("source","")).startswith(module+".")];lines=[f"## Artifact and contract relationships for `{module}` ({len(edges)})",""]
 if not edges:lines.append("_none found by the fast static scanners_")
 else:
  for edge in edges:
   ev=edge["evidence"];lines.append(f"- `{edge['relationship']}` -> `{edge['target']}` (`{ev['file']}:{ev['line']}`, {edge['confidence']})")
 stats=graph.get("stats",{});metrics=graph.get("analysisMetrics",{});lines += ["","## Repository contracts and lineage","",f"- Contract/catalog records: {stats.get('contracts',0)}",f"- Relationship edges: {stats.get('edges',0)}",f"- Scanner cache: {stats.get('cacheHits',0)} hit(s), {stats.get('parsedFiles',0)} parsed file(s)",f"- OpenLineage-compatible JobEvents: {graph.get('openLineageEvents',0)}",f"- Unresolved semantic sinks: {metrics.get('unresolvedSinkArguments',0)}"]
 if graph.get("errors"):lines.append(f"- Scanner warnings: {len(graph['errors'])}")
 return "\n".join(lines)

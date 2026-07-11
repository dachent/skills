"""Shared primitives for the local relationship scanners."""
from __future__ import annotations
import ast, re
from pathlib import Path
from typing import Any, Iterable

HTTP_METHODS={"get","post","put","patch","delete","head","options","trace"}
READ_CALLS={
 "pandas.read_csv":(0,"file"),"pandas.read_parquet":(0,"file"),"pandas.read_excel":(0,"file"),
 "pandas.read_json":(0,"file"),"pandas.read_feather":(0,"file"),"pandas.read_pickle":(0,"file"),
 "polars.read_csv":(0,"file"),"polars.read_parquet":(0,"file"),"joblib.load":(0,"model"),"torch.load":(0,"model"),
}
WRITE_CALLS={"joblib.dump":(1,"model"),"torch.save":(1,"model")}
METHOD_READS={"read_text":(0,"file"),"read_bytes":(0,"file")}
PATH_METHOD_WRITES={"write_text","write_bytes"}
METHOD_WRITES={"to_csv":(0,"file"),"to_parquet":(0,"file"),"to_excel":(0,"file"),"to_json":(0,"file"),"to_feather":(0,"file"),"to_pickle":(0,"file")}
HTTP_CLIENT_PREFIXES=("requests.","httpx.")
SQL_READ_RE=re.compile(r"\b(?:from|join)\s+([A-Za-z_][\w.$-]*)",re.IGNORECASE)
SQL_WRITE_RE=re.compile(r"\b(?:insert\s+into|update|delete\s+from|create\s+table|merge\s+into)\s+([A-Za-z_][\w.$-]*)",re.IGNORECASE)
HIGH_VALUE_RELATIONS={"WRITES_FILE","READS_TABLE","WRITES_TABLE","LOADS_MODEL","CONSUMES_ENDPOINT","PRODUCES_EVENT","EXECUTES_PROCESS"}

def _rel(path:Path,root:Path)->str:
 try:return path.relative_to(root).as_posix()
 except ValueError:return path.as_posix()

def _edge(source,relationship,target,*,file,line=1,symbol=None,confidence="exact",extractor="python-ast",target_type="artifact"):
 evidence={"file":file,"line":line,"extractor":extractor}
 if symbol:evidence["symbol"]=symbol
 return {"source":source,"relationship":relationship,"target":target,"targetType":target_type,"confidence":confidence,"evidence":evidence}

def _dedupe_edges(edges:Iterable[dict[str,Any]])->list[dict[str,Any]]:
 seen=set();out=[]
 for edge in edges:
  ev=edge.get("evidence",{});key=(edge.get("source"),edge.get("relationship"),edge.get("target"),ev.get("file"),ev.get("line"),ev.get("symbol"))
  if key not in seen:seen.add(key);out.append(edge)
 return sorted(out,key=lambda e:(e["source"],e["relationship"],e["target"],e["evidence"].get("file",""),e["evidence"].get("line",0)))

def _dedupe_signals(signals:Iterable[dict[str,Any]])->list[dict[str,Any]]:
 seen=set();out=[]
 for signal in signals:
  key=(signal.get("file"),signal.get("line"),signal.get("source"),signal.get("relationship"),signal.get("argumentIndex"))
  if key not in seen:seen.add(key);out.append(signal)
 return sorted(out,key=lambda s:(s.get("file",""),s.get("line",0),s.get("relationship","")))

def _dotted(node:ast.AST,aliases:dict[str,str])->str|None:
 if isinstance(node,ast.Name):return aliases.get(node.id,node.id)
 if isinstance(node,ast.Attribute):
  base=_dotted(node.value,aliases);return f"{base}.{node.attr}" if base else node.attr
 return None

def _literal(node:ast.AST|None,aliases:dict[str,str])->tuple[str|None,str]:
 if node is None:return None,"unknown"
 if isinstance(node,ast.Constant) and isinstance(node.value,(str,int,float)):return str(node.value),"exact"
 if isinstance(node,ast.Name):return "${"+node.id+"}","inferred"
 if isinstance(node,ast.Attribute):
  name=_dotted(node,aliases);return ("${"+name+"}" if name else None),"inferred"
 if isinstance(node,(ast.List,ast.Tuple)):
  values=[_literal(item,aliases) for item in node.elts]
  if values and all(value is not None for value,_ in values):
   return " ".join(str(value) for value,_ in values),"exact" if all(confidence=="exact" for _,confidence in values) else "inferred"
 if isinstance(node,ast.JoinedStr):
  parts=[]
  for value in node.values:
   if isinstance(value,ast.Constant):parts.append(str(value.value))
   elif isinstance(value,ast.FormattedValue):
    text,_=_literal(value.value,aliases);parts.append(text or "${expr}")
  return "".join(parts),"inferred"
 if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Div,ast.Add)):
  left,lc=_literal(node.left,aliases);right,rc=_literal(node.right,aliases)
  if left is not None and right is not None:
   sep="/" if isinstance(node.op,ast.Div) else ""
   return left.rstrip("/")+sep+right.lstrip("/"),"exact" if lc==rc=="exact" else "inferred"
 if isinstance(node,ast.Call):
  name=_dotted(node.func,aliases)
  if name in {"Path","pathlib.Path"} and node.args:return _literal(node.args[0],aliases)
  if name in {"os.path.join","posixpath.join","ntpath.join"}:
   vals=[_literal(arg,aliases) for arg in node.args]
   if vals and all(v[0] is not None for v in vals):return "/".join(str(v[0]).strip("/") for v in vals),"exact" if all(v[1]=="exact" for v in vals) else "inferred"
 return None,"unknown"

def _arg(call:ast.Call,index:int,keyword:str|None=None)->ast.AST|None:
 if len(call.args)>index:return call.args[index]
 if keyword:
  for kw in call.keywords:
   if kw.arg==keyword:return kw.value
 return None

def _expr_names(node):return set() if node is None else {c.id for c in ast.walk(node) if isinstance(c,ast.Name)}
def _expr_is_transformed(node):return isinstance(node,(ast.JoinedStr,ast.BinOp,ast.Call,ast.Subscript,ast.IfExp))
def _expr_text(node):return type(node).__name__ if node is not None else ""

def _sql_edges(sql,source,file,line,symbol):
 edges=[]
 for table in SQL_READ_RE.findall(sql):edges.append(_edge(source,"READS_TABLE",table,file=file,line=line,symbol=symbol,target_type="dataset"))
 for table in SQL_WRITE_RE.findall(sql):edges.append(_edge(source,"WRITES_TABLE",table,file=file,line=line,symbol=symbol,target_type="dataset"))
 return edges

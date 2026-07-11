"""Python AST relationship and semantic-trigger extraction; never imports target code."""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Any
from _relationship_common import (
 HIGH_VALUE_RELATIONS, HTTP_CLIENT_PREFIXES, HTTP_METHODS, METHOD_READS, METHOD_WRITES,
 PATH_METHOD_WRITES, READ_CALLS, WRITE_CALLS, _arg, _dedupe_edges, _dedupe_signals,
 _dotted, _edge, _expr_is_transformed, _expr_names, _expr_text, _literal, _rel, _sql_edges,
)

def _function_complexity(node):
 branch_types=(ast.If,ast.For,ast.AsyncFor,ast.While,ast.Try,ast.Match)
 return 1+sum(isinstance(statement,branch_types) for statement in node.body)

class PythonRelationshipVisitor(ast.NodeVisitor):
 def __init__(self,module,file_rel):
  self.module=module;self.file_rel=file_rel;self.scope=[];self.aliases={};self.edges=[];self.signals=[];self.parameter_stack=[];self.complexity_stack=[]
 @property
 def source(self):return ".".join([self.module,*self.scope]) if self.scope else self.module
 @property
 def symbol(self):return self.source
 @property
 def parameters(self):return self.parameter_stack[-1] if self.parameter_stack else set()
 @property
 def complexity(self):return self.complexity_stack[-1] if self.complexity_stack else 1
 def _record_signal(self,node,relation,argument,index,confidence,target,*,ambiguous_mode=False,dynamic_sql=False,unresolved_config=False):
  names=sorted(_expr_names(argument));params=sorted(set(names)&self.parameters)
  self.signals.append({"source":self.source,"relationship":relation,"file":self.file_rel,"line":node.lineno,"argumentIndex":index,"argumentExpression":_expr_text(argument),"target":target,"confidence":confidence,"unresolved":target is None or confidence!="exact","transformed":_expr_is_transformed(argument),"parameterNames":params,"parameterToSink":bool(params),"ambiguousReadWriteMode":ambiguous_mode,"dynamicSql":dynamic_sql,"unresolvedConfig":unresolved_config,"highValue":relation in HIGH_VALUE_RELATIONS,"functionComplexity":self.complexity})
 def _artifact(self,node,relation,argument,index,*,target_type="dataset",ambiguous_mode=False):
  target,confidence=_literal(argument,self.aliases);self._record_signal(node,relation,argument,index,confidence,target,ambiguous_mode=ambiguous_mode)
  if target:self.edges.append(_edge(self.source,relation,target,file=self.file_rel,line=node.lineno,symbol=self.symbol,confidence=confidence,target_type=target_type))
  return target,confidence
 def visit_Import(self,node):
  for alias in node.names:self.aliases[alias.asname or alias.name.split(".")[0]]=alias.name
 def visit_ImportFrom(self,node):
  module=node.module or ""
  for alias in node.names:self.aliases[alias.asname or alias.name]=f"{module}.{alias.name}".strip(".")
 def visit_ClassDef(self,node):
  bases={_dotted(base,self.aliases) for base in node.bases}
  if any(base and (base.endswith("BaseModel") or base.endswith("TypedDict")) for base in bases):self.edges.append(_edge(self.source,"DEFINES_SCHEMA",f"python:{self.module}.{node.name}",file=self.file_rel,line=node.lineno,symbol=f"{self.module}.{node.name}",target_type="contract"))
  self.scope.append(node.name);self.generic_visit(node);self.scope.pop()
 def visit_Subscript(self,node):
  owner=_dotted(node.value,self.aliases)
  if owner in {"os.environ","environ"}:
   value,confidence=_literal(node.slice,self.aliases)
   if value:self.edges.append(_edge(self.source,"READS_CONFIG",value,file=self.file_rel,line=node.lineno,symbol=self.symbol,confidence=confidence,target_type="config"))
  self.generic_visit(node)
 def visit_Call(self,node):
  name=_dotted(node.func,self.aliases) or "";method=name.rsplit(".",1)[-1]
  if name in {"open","builtins.open","io.open"}:
   arg=_arg(node,0,"file");mode_node=_arg(node,1,"mode");mode,mc=_literal(mode_node,self.aliases);rel="WRITES_FILE" if mode and any(f in mode for f in "wax+") else "READS_FILE";self._artifact(node,rel,arg,0,ambiguous_mode=mode_node is not None and mc!="exact")
  if name in READ_CALLS:
   idx,kind=READ_CALLS[name];self._artifact(node,"LOADS_MODEL" if kind=="model" else "READS_FILE",_arg(node,idx),idx)
  if name in WRITE_CALLS:
   idx,kind=WRITE_CALLS[name];self._artifact(node,"SAVES_MODEL" if kind=="model" else "WRITES_FILE",_arg(node,idx),idx)
  if method in METHOD_READS:self._artifact(node,"READS_FILE",node.func.value if isinstance(node.func,ast.Attribute) else None,-1)
  if method in PATH_METHOD_WRITES:self._artifact(node,"WRITES_FILE",node.func.value if isinstance(node.func,ast.Attribute) else None,-1)
  if method in METHOD_WRITES:
   idx,_=METHOD_WRITES[method];self._artifact(node,"WRITES_FILE",_arg(node,idx),idx)
  if method=="open" and isinstance(node.func,ast.Attribute):
   mode_node=_arg(node,0,"mode");mode,mc=_literal(mode_node,self.aliases);rel="WRITES_FILE" if mode and any(f in mode for f in "wax+") else "READS_FILE";self._artifact(node,rel,node.func.value,-1,ambiguous_mode=mode_node is not None and mc!="exact")
  if name in {"pandas.read_sql","pandas.read_sql_query"}:
   arg=_arg(node,0,"sql");sql,confidence=_literal(arg,self.aliases);self._record_signal(node,"READS_TABLE",arg,0,confidence,sql,dynamic_sql=sql is None or confidence!="exact")
   if sql and confidence=="exact":self.edges.extend(_sql_edges(sql,self.source,self.file_rel,node.lineno,self.symbol))
  if method=="to_sql":self._artifact(node,"WRITES_TABLE",_arg(node,0,"name"),0)
  if name in {"os.getenv","os.environ.get"}:
   arg=_arg(node,0);target,confidence=_literal(arg,self.aliases);self._record_signal(node,"READS_CONFIG",arg,0,confidence,target,unresolved_config=target is None or confidence!="exact")
   if target:self.edges.append(_edge(self.source,"READS_CONFIG",target,file=self.file_rel,line=node.lineno,symbol=self.symbol,confidence=confidence,target_type="config"))
  if any(name.startswith(prefix) for prefix in HTTP_CLIENT_PREFIXES) and method.lower() in HTTP_METHODS:
   arg=_arg(node,0,"url");target,confidence=_literal(arg,self.aliases);rendered=f"{method.upper()} {target}" if target else None;self._record_signal(node,"CONSUMES_ENDPOINT",arg,0,confidence,rendered)
   if rendered:self.edges.append(_edge(self.source,"CONSUMES_ENDPOINT",rendered,file=self.file_rel,line=node.lineno,symbol=self.symbol,confidence=confidence,target_type="contract"))
  if method in {"execute","executemany"}:
   arg=_arg(node,0);sql,confidence=_literal(arg,self.aliases);self._record_signal(node,"READS_TABLE",arg,0,confidence,sql,dynamic_sql=sql is None or confidence!="exact")
   if sql and confidence=="exact":self.edges.extend(_sql_edges(sql,self.source,self.file_rel,node.lineno,self.symbol))
  if name in {"subprocess.run","subprocess.Popen","subprocess.call","subprocess.check_call","subprocess.check_output","os.system"}:self._artifact(node,"EXECUTES_PROCESS",_arg(node,0),0,target_type="process")
  if method in {"publish","produce","send"}:self._artifact(node,"PRODUCES_EVENT",_arg(node,0,"topic"),0,target_type="contract")
  if method in {"subscribe","consume"}:self._artifact(node,"CONSUMES_EVENT",_arg(node,0,"topic"),0,target_type="contract")
  self.generic_visit(node)
 def _route(self,decorator):
  if not isinstance(decorator,ast.Call):return None
  name=_dotted(decorator.func,self.aliases) or "";method=name.rsplit(".",1)[-1].lower()
  if method not in HTTP_METHODS and method!="route":return None
  path,confidence=_literal(_arg(decorator,0,"path"),self.aliases)
  if not path:return None
  http=method.upper()
  if method=="route":
   for kw in decorator.keywords:
    if kw.arg=="methods" and isinstance(kw.value,(ast.List,ast.Tuple)) and kw.value.elts:
     candidate,_=_literal(kw.value.elts[0],self.aliases)
     if candidate:http=candidate.upper()
  return f"{http} {path}",confidence,decorator.lineno
 def _visit_route(self,node):
  for decorator in node.decorator_list:
   route=self._route(decorator)
   if route:
    target,confidence,line=route;source=f"{self.module}.{'.'.join([*self.scope,node.name])}" if self.scope else f"{self.module}.{node.name}";self.edges.append(_edge(source,"IMPLEMENTS_ENDPOINT",target,file=self.file_rel,line=line,symbol=source,confidence=confidence,target_type="contract"))
 def visit_FunctionDef(self,node):
  self._visit_route(node);args={a.arg for a in [*node.args.posonlyargs,*node.args.args,*node.args.kwonlyargs]}
  if node.args.vararg:args.add(node.args.vararg.arg)
  if node.args.kwarg:args.add(node.args.kwarg.arg)
  self.scope.append(node.name);self.parameter_stack.append(args);self.complexity_stack.append(_function_complexity(node));self.generic_visit(node);self.complexity_stack.pop();self.parameter_stack.pop();self.scope.pop()
 visit_AsyncFunctionDef=visit_FunctionDef

def _module_for_file(path,package_dir,package):
 rel=path.relative_to(package_dir).with_suffix("");parts=list(rel.parts)
 if parts and parts[-1]=="__init__":parts.pop()
 return ".".join([package,*parts]) if parts else package

def scan_python_file(path,package_dir,package,repo_root,data=None):
 file_rel=_rel(path,repo_root);module=_module_for_file(path,package_dir,package)
 try:tree=ast.parse((data if data is not None else path.read_bytes()).decode("utf-8-sig"),filename=str(path))
 except (OSError,UnicodeError,SyntaxError) as exc:return {"edges":[],"contracts":[],"signals":[],"errors":[{"file":file_rel,"error":str(exc)}]}
 visitor=PythonRelationshipVisitor(module,file_rel);visitor.visit(tree)
 return {"edges":_dedupe_edges(visitor.edges),"contracts":[],"signals":_dedupe_signals(visitor.signals),"errors":[]}

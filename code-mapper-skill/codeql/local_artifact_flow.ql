/**
 * @name Local artifact value and taint flow
 * @description Finds function parameters that flow into or influence common Python artifact sink arguments.
 * @kind table
 * @id code-mapper/local-artifact-flow
 */
import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.ApiGraphs

predicate artifactArgument(DataFlow::CallCfgNode call, DataFlow::Node argument, string kind) {
  call = API::builtin("open").getACall() and
  argument = call.getArg(0) and kind = "file-open"
  or
  call = API::moduleImport("os").getMember("open").getACall() and
  argument = call.getArg(0) and kind = "os-open"
  or
  call = API::moduleImport("pandas").getMember("read_csv").getACall() and
  argument = call.getArg(0) and kind = "pandas-read-csv"
  or
  call = API::moduleImport("pandas").getMember("read_parquet").getACall() and
  argument = call.getArg(0) and kind = "pandas-read-parquet"
  or
  call = API::moduleImport("pandas").getMember("read_excel").getACall() and
  argument = call.getArg(0) and kind = "pandas-read-excel"
  or
  call = API::moduleImport("subprocess").getMember("run").getACall() and
  argument = call.getArg(0) and kind = "subprocess-run"
}

from DataFlow::CallCfgNode call, DataFlow::ParameterNode source,
     DataFlow::Node argument, string kind, string flowKind
where
  artifactArgument(call, argument, kind) and
  (
    flowKind = "value" and DataFlow::localFlow(source, argument)
    or
    flowKind = "taint" and TaintTracking::localTaint(source, argument) and
      not DataFlow::localFlow(source, argument)
  )
select
  kind,
  flowKind,
  source,
  call,
  call.getLocation().getFile().getRelativePath(),
  call.getLocation().getStartLine()

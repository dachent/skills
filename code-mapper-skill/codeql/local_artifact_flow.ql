/**
 * @name Local artifact argument flow
 * @description Finds local sources that flow into common Python file/data access arguments.
 * @kind table
 * @id code-mapper/local-artifact-flow
 */
import python
import semmle.python.dataflow.new.DataFlow
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
}

from DataFlow::CallCfgNode call, DataFlow::LocalSourceNode source, DataFlow::Node argument, string kind
where artifactArgument(call, argument, kind) and source.flowsTo(argument)
select call, kind, source, argument

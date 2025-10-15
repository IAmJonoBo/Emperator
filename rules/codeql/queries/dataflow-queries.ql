/**
 * @name Untrusted data reaching os.system
 * @description Tracks tainted data reaching os.system.
 * @kind path-problem
 * @problem.severity warning
 * @tags security, external/cwe/cwe-078
 */
import python
import semmle.python.security.dataflow.TaintTracking

class CommandExecutionConfig extends TaintTracking::Configuration {
  CommandExecutionConfig() { this = "CommandExecutionConfig" }

  override predicate isSource(DataFlow::Node source) {
    source.asExpr() instanceof Parameter
  }

  override predicate isSink(DataFlow::Node sink) {
    exists(CallExpr call |
      call.getFunc().(Name).getId() = "system" and
      call.getArgument(0) = sink.asExpr()
    )
  }
}

from CommandExecutionConfig::PathNode source, CommandExecutionConfig::PathNode sink
where source.flowsTo(sink)
select sink, source, "Untrusted input reaches os.system"

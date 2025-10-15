/**
 * @name Ban eval usage
 * @description Flags calls to eval that execute dynamic code.
 * @kind problem
 * @problem.severity error
 * @tags security, external/cwe/cwe-95
 */
import python

from CallExpr call
where call.getFunc().(Name).getId() = "eval"
select call, "Use ast.literal_eval() or json.loads() instead of eval()."

/**
 * @name Ban exec usage
 * @description Disallows exec which executes arbitrary strings as code.
 * @kind problem
 * @problem.severity error
 * @tags security, external/cwe/cwe-95
 */
from CallExpr call
where call.getFunc().(Name).getId() = "exec"
select call, "Avoid exec(); refactor to explicit functions."

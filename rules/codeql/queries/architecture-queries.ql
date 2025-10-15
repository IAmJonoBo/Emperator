/**
 * @name Detect forbidden import from domain to api layer
 * @description Ensures domain modules are not importing FastAPI resources.
 * @kind problem
 * @problem.severity warning
 * @tags architecture
 */
import python

from Import importImport, string moduleName
where
  importImport.getFile().getRelativePath().matches("src/emperator/domain/%") and
  moduleName = importImport.getImportedModuleName() and
  moduleName.startsWith("src.emperator.api")
select importImport, "Domain modules should not depend on API layer abstractions."

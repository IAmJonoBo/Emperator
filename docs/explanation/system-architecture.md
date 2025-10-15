# System Architecture Deep Dive

Emperator’s architecture turns a versioned Project Contract into actionable checks, deterministic fixes, and scaffolded code. The system can be reasoned about in three layers that align with the Contract→IR→Action pipeline illustrated below.

```mermaid
flowchart LR
  subgraph Contract Layer
    A[Contract Assets<br/>(OpenAPI • CUE • Rego • Templates)]
  end
  subgraph IR & Analysis Layer
    B[Universal Code IR<br/>– Tree-sitter CST<br/>– CodeQL semantic DB<br/>– Semgrep pattern index]
  end
  subgraph Execution Layer
    C1[Check Engines]
    C2[Fix Engines]
    C3[Scaffold & Format]
  end
  A --> B --> C1
  C1 -->|Violations?| D{Safety Gate}
  D -->|Auto-fixable| C2 --> C3 --> E[Proposed or Applied Changes]
  D -->|Review needed| E
  E --> F[Re-check & Optional Tests]
  F -->|Pass| G[✅ Standards satisfied]
  F -->|Fail| H[Rollback & Report]
```

## Layered overview

- **Contract layer:** Stores declarative standards in existing open formats (OpenAPI for interface contracts, CUE for naming/config constraints, OPA Rego for policies, plus codemod templates). Contracts are version-controlled and treated as first-class artefacts so standards evolve without drifting from code.
- **IR & analysis layer:** Builds a polyglot intermediate representation by combining Tree-sitter concrete syntax trees, CodeQL semantic databases, and Semgrep’s pattern index. The result is a unified graph that supports fast local checks and deep cross-language reasoning.
- The CLI’s `analysis inspect` command surfaces this context directly for developers, confirming language coverage and highlighting which analyzers are ready before deeper orchestration begins.
- **Execution layer:** Compiles contract rules into checks, fixes, scaffolds, and formatter runs. Each action is orchestrated through the Safety Gate, which classifies findings by severity and determines whether Emperator can auto-remediate or should defer to a developer.

This structure maps cleanly to a C4 view: the CLI/LSP service acts as the primary container, backed by modular components (contract loader, IR builder, check coordinator, codemod runner, formatter and report generator) that communicate via typed rule and finding objects.

## Contract layer responsibilities

- **Standards as code:** Contracts leverage proven DSLs so the same definitions can be validated independently or shared across systems. OpenAPI specs drive handler scaffolding, CUE encodes structural constraints, and Rego expresses higher-order policies such as dependency allowlists or security posture requirements.
- **Versioning and provenance:** Every rule change is traceable. Emperator stamps applied fixes with the contract revision and logs the reasoning, enabling audits and staged rollouts (e.g., warn-only before enforcing breaking rules).
- **Evidence grading:** Rules can reference external standards (OWASP, MISRA, internal policies) with citations so developers understand the “why” behind each enforcement.

## Universal IR construction

- **Tree-sitter parsing:** Provides incremental, lossless CSTs for dozens of languages. Emperator uses them to trigger near real-time diagnostics in editor integrations and to feed higher-level analyses without reparsing entire files.
- **CodeQL enrichment:** Generates semantic databases for supported languages, exposing control-flow and data-flow relationships. Emperator ships with curated query packs that enforce architecture boundaries, detect security issues, and surface dependency violations.
- **Semgrep pattern catalog:** Converts contract snippets into multi-language patterns for quick, diff-friendly scans. Community security rules and custom project checks run alongside the contract-derived rules.
- **Incremental updates:** A background daemon watches source changes, re-running only the relevant analyses. This keeps feedback loops short while supporting large repositories.

## Action engines and safety envelope

- **Check engines:** Run Semgrep rules, CodeQL queries, and contract validators. Findings are tagged with severity, evidence confidence, and auto-fix eligibility. High-noise detections are triaged for manual review.
- **Fix engines:** Apply deterministic codemods (LibCST, OpenRewrite, language-specific refactorers) for rules classified as safe. Complex migrations can be proposed as diffs rather than applied automatically.
- **Scaffold & generate:** Templates in `contract/generators/` create handlers, tests, or migration stubs based on contract deltas (e.g., new OpenAPI endpoints). Generated code is re-checked before acceptance.
- **Formatters:** Invoke battle-tested formatters such as Ruff, Black, Prettier, gofmt, or clang-format to ensure minimal diffs that match team conventions (see the [Toolchain Matrix](../reference/toolchain.md#recommended-lint-and-formatter-stacks) for language-specific pairings).
- **Safety gate:** Categorizes each change into tiers (formatting, low-risk refactor, complex migration) and enforces validation. After a fix, Emperator re-runs the relevant checks and optional property-based tests before marking the issue resolved. Failures result in automatic rollback and a detailed report.

## Extensibility and performance

- **Plugin interfaces:** New languages integrate by implementing parser adapters, analyzer hooks, and codemod providers. Policy plug-ins can introduce specialized analyzers (e.g., MISRA checkers) without altering the core orchestrator.
- **Performance budgets:** Emperator differentiates between fast interactive checks and exhaustive CI runs. Users can opt into deeper analyses (full CodeQL packs, fuzz tests) in pipelines while keeping pre-commit execution under a few seconds.
  <a id="offline-operation"></a>
- **Offline operation:** All components run locally, ensuring suitability for air-gapped environments. Optional AI assistance uses on-prem models only (see the AI-assisted how-to guide for details).

With this architecture, Emperator ensures contracts remain executable, analyses stay coherent across languages, and automated changes land safely under rigorous validation.

## Related references

- Map contract rules to analyzers in the [Toolchain Matrix](../reference/toolchain.md).
- Follow the rollout stages in the [Implementation Roadmap](implementation-roadmap.md).
- Align governance levers with the [Governance and Compliance reference](../reference/governance.md).

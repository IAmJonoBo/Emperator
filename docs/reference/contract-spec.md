# Project Contract Reference

Use this page to look up the canonical structure, rule metadata fields, severity tiers, and exemption syntax for Emperator contracts. Treat it as the contract maintainer’s quick reference.

## Directory layout

| Path                          | Description                                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------------- |
| `contract/conventions.cue`    | CUE schemas for naming conventions, file layout, formatter preferences, and architectural wiring. |
| `contract/api/`               | OpenAPI or GraphQL interface specs that drive scaffolding and contract-aware tests.               |
| `contract/policy/`            | OPA Rego modules defining deny/warn rules, dependency allowlists, and governance policies.        |
| `contract/generators/`        | Codemod recipes, code templates, and scaffolding scripts keyed by language and rule.              |
| `contract/rules/catalog.yaml` | Canonical rule metadata catalog consumed by analyzers and the correlation engine.                 |
| `contract/exemptions.yaml`    | Optional registry of approved waivers with owner, expiry, and mitigation notes.                   |
| `contract/README.md`          | Human-readable change log, review checklist, and links to external standards.                     |

> **Current status:** Rule generators and contract-aware assets remain planned work. `contract/generators/` and `contract/generated/` presently contain scaffolding only; Semgrep and CodeQL packs described in Sprint 4 have not been produced yet.

## Protobuf schemas {#protobuf-schemas}

- Store `.proto` files either under `contract/api/` or the service repository’s source tree and reference them from the contract via relative paths.
- Run `buf format` and `buf lint` as part of contract validation so code generation and API compatibility checks stay aligned with the [Toolchain Matrix](toolchain.md#recommended-lint-and-formatter-stacks).
- Version generated language bindings (Go, Java, C#) through Emperator scaffolds to maintain parity between the canonical schema and downstream usage.

## Rule metadata schema

Each rule compiled from the contract exposes the following fields in Emperator outputs and reports. The canonical source of this metadata is `contract/rules/catalog.yaml`, which powers the analyzer correlation engine and upcoming rule generators:

| Field         | Meaning                                                                                                |
| ------------- | ------------------------------------------------------------------------------------------------------ |
| `id`          | Stable identifier (e.g., `LayeringPolicy.ControllerToDB`). Use dot notation for hierarchy.             |
| `description` | Concise explanation shown in diagnostics. Include the “why” and reference to standards where relevant. |
| `source`      | File and section inside the contract (e.g., `conventions.cue#controllers.allowImports`).               |
| `severity`    | `info`, `low`, `medium`, `high`, or `critical`. Drives CI gating and alert styling.                    |
| `auto_apply`  | `true` / `false`. Indicates whether Emperator may execute deterministic fixes without human approval.  |
| `safety_tier` | `formatting`, `low`, `medium`, `high`. Governs downstream automation (AI assistants, codemod runners). |
| `evidence`    | Optional citation list (URLs or doc references) supporting the rule rationale.                         |
| `tags`        | Keyword array (e.g., `security`, `style`, `compliance`) for filtering dashboards and reports.          |

Rules authored in CUE, Rego, or metadata YAML should populate these fields so Emperator can render uniform diagnostics.

### IR-Related Metadata (Sprint 4+)

Additional fields for rules that leverage the Intermediate Representation:

| Field               | Meaning                                                                           | Example Value                        |
| ------------------- | --------------------------------------------------------------------------------- | ------------------------------------ |
| `ir_analysis_level` | IR layer required: `cst` (syntax tree), `semantic` (CodeQL), `pattern` (Semgrep). | `"semantic"`                         |
| `symbols_required`  | Symbol types needed for analysis (e.g., functions, classes, imports).             | `["function", "import"]`             |
| `cross_file`        | Whether rule requires multi-file analysis (dependency graph).                     | `false`                              |
| `query_language`    | Query engine: `semgrep`, `codeql`, `tree-sitter-query`.                           | `"codeql"`                           |
| `query_path`        | Path to query file in `rules/` directory.                                         | `"rules/codeql/layer-violations.ql"` |
| `cache_key`         | Optional cache key for expensive analysis results.                                | `"layering-check-v1"`                |
| `performance_tier`  | Expected execution time: `fast` (\<1s), `medium` (\<10s), `slow` (>10s).          | `"medium"`                           |
| `fix_transformer`   | Transformer class for automated fixes (Sprint 5+).                                | `"RenameTransformer"`                |
| `fix_risk_tier`     | Risk tier for automated fix: `0` (formatting) to `3` (architectural).             | `1`                                  |

> **Reality check:** ADR-0004 defines the Tree-sitter backed IR builder, but the repository does not yet ship an `ir` package, cache format, or telemetry integration. Populate the metadata below once the IR layer exists.

**Example Contract Rule with IR Metadata:**

```yaml
# contract/rules/layering-violations.yaml
rules:
  - id: LayeringPolicy.ControllerToDB
    description: Controllers must not directly call database layer; use service layer
    source: contract/policy/architecture.rego#layer_violations
    severity: high
    auto_apply: false
    safety_tier: high
    tags: [architecture, layering]
    evidence:
      - https://martinfowler.com/bliki/PresentationDomainDataLayering.html

    # IR-specific metadata
    ir_analysis_level: semantic
    symbols_required: [function, import]
    cross_file: true
    query_language: codeql
    query_path: rules/codeql/controller-to-db.ql
    performance_tier: medium

  # Fix metadata (Sprint 5)
  fix_transformer: LayerViolationFixTransformer
  fix_risk_tier: 3

> **Safety envelope gap:** ADR-0005 outlines LibCST/OpenRewrite transformers and risk tiers, but no fix modules or transformer classes exist yet. Add `fix_transformer` and `fix_risk_tier` only after the safety pipeline lands.
```

## Severity guidance

| Severity   | When to use                                                                  | Default enforcement                                               |
| ---------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `info`     | Advisory checks, upcoming policies, style suggestions with known exceptions. | Logged only; no CI failure.                                       |
| `low`      | Minor hygiene issues with safe autofixes (e.g., formatting drift).           | Auto-fix and continue.                                            |
| `medium`   | Issues that may cause maintainability problems or mild security risks.       | Block CI until resolved or justified.                             |
| `high`     | Significant security, compliance, or architectural violations.               | Fail CI, raise blocker in PR, optional auto-fix if deterministic. |
| `critical` | Actively exploitable security flaws or policy breaches that must not ship.   | Immediate failure; require manual remediation and sign-off.       |

## Exemption syntax

Apply exemptions sparingly and always include justification plus expiry metadata.

```python
# emperator:ignore LayeringPolicy.ControllerToDB -- justification="Legacy module awaiting service rewrite" -- expires="2025-12-31"
def legacy_handler():
    ...
```

- Place ignore annotations on the minimal scope (line, block, or file). Emperator will record the exemption in reports.
- Exemptions without `justification` or `expires` are rejected when `emperator check --strict --enforce-expiry` runs.
- Track long-lived waivers in `contract/exemptions.yaml`:

```yaml
- rule: LayeringPolicy.ControllerToDB
  location: src/legacy/orders_controller.py:42
  owner: platform-team
  justification: Temporary waiver while migrating to OrderService
  expires: 2025-12-31
```

## Contract review checklist

1. Run `cue fmt` and `cue vet contract/conventions.cue` to ensure structural validity.
1. Execute `opa check` on Rego modules and run `opa eval` against sample findings.
1. Dry-run Emperator (`emperator apply --diff --no-commit --fast`) to see the impact of new rules.
1. Update `docs/includes/copilot-prompts.md` with new rule exemplars.
1. Increment the contract version tag and note changes in `contract/README.md`.

Keep this reference close during contract updates to ensure every rule remains actionable, auditable, and aligned with the wider engineering standards.

## Programmatic access

Runtime components can rely on :mod:`emperator.contract` for strongly-typed helpers
when they need to surface contract metadata. `get_contract_path()` returns the
authoritative repository location, `load_contract_spec()` exposes the parsed
OpenAPI document as an immutable mapping, and `get_contract_info()` condenses the
`info` section into a :class:`emperator.contract.ContractInfo` dataclass.

```python
from emperator.contract import ContractInfo, get_contract_info

info: ContractInfo = get_contract_info()
print(info.version)
print(info.source_path)
```

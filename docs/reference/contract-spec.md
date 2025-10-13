# Project Contract Reference

Use this page to look up the canonical structure, rule metadata fields, severity tiers, and exemption syntax for Emperator contracts. Treat it as the contract maintainer’s quick reference.

## Directory layout

| Path | Description |
| --- | --- |
| `contract/conventions.cue` | CUE schemas for naming conventions, file layout, formatter preferences, and architectural wiring. |
| `contract/api/` | OpenAPI or GraphQL interface specs that drive scaffolding and contract-aware tests. |
| `contract/policy/` | OPA Rego modules defining deny/warn rules, dependency allowlists, and governance policies. |
| `contract/generators/` | Codemod recipes, code templates, and scaffolding scripts keyed by language and rule. |
| `contract/exemptions.yaml` | Optional registry of approved waivers with owner, expiry, and mitigation notes. |
| `contract/README.md` | Human-readable change log, review checklist, and links to external standards. |

## Rule metadata schema

Each rule compiled from the contract exposes the following fields in Emperator outputs and reports:

| Field | Meaning |
| --- | --- |
| `id` | Stable identifier (e.g., `LayeringPolicy.ControllerToDB`). Use dot notation for hierarchy. |
| `description` | Concise explanation shown in diagnostics. Include the “why” and reference to standards where relevant. |
| `source` | File and section inside the contract (e.g., `conventions.cue#controllers.allowImports`). |
| `severity` | `info`, `low`, `medium`, `high`, or `critical`. Drives CI gating and alert styling. |
| `auto_apply` | `true` / `false`. Indicates whether Emperator may execute deterministic fixes without human approval. |
| `safety_tier` | `formatting`, `low`, `medium`, `high`. Governs downstream automation (AI assistants, codemod runners). |
| `evidence` | Optional citation list (URLs or doc references) supporting the rule rationale. |
| `tags` | Keyword array (e.g., `security`, `style`, `compliance`) for filtering dashboards and reports. |

Rules authored in CUE, Rego, or metadata YAML should populate these fields so Emperator can render uniform diagnostics.

## Severity guidance

| Severity | When to use | Default enforcement |
| --- | --- | --- |
| `info` | Advisory checks, upcoming policies, style suggestions with known exceptions. | Logged only; no CI failure. |
| `low` | Minor hygiene issues with safe autofixes (e.g., formatting drift). | Auto-fix and continue. |
| `medium` | Issues that may cause maintainability problems or mild security risks. | Block CI until resolved or justified. |
| `high` | Significant security, compliance, or architectural violations. | Fail CI, raise blocker in PR, optional auto-fix if deterministic. |
| `critical` | Actively exploitable security flaws or policy breaches that must not ship. | Immediate failure; require manual remediation and sign-off. |

## Exemption syntax

Apply exemptions sparingly and always include justification plus expiry metadata.

```python
# emperator:ignore LayeringPolicy.ControllerToDB -- justification="Legacy module awaiting service rewrite" -- expires="2025-12-31"
def legacy_handler():
    ...
```

- Place ignore annotations on the minimal scope (line, block, or file). Emperator will record the exemption in reports.
- Exemptions without `justification` or `expires` are rejected when `emperor check --strict --enforce-expiry` runs.
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
2. Execute `opa check` on Rego modules and run `opa eval` against sample findings.
3. Dry-run Emperator (`emperor apply --diff --no-commit --fast`) to see the impact of new rules.
4. Update `docs/includes/copilot-prompts.md` with new rule exemplars.
5. Increment the contract version tag and note changes in `contract/README.md`.

Keep this reference close during contract updates to ensure every rule remains actionable, auditable, and aligned with the wider engineering standards.

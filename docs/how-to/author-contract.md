# Authoring and Evolving the Project Contract

The Project Contract is the single source of truth for Emperator’s standards. This guide shows how to structure the contract repository, encode rules with open standards, validate changes, and stage rollouts safely.

## 1. Scaffold the contract directory

Place the contract in a top-level `contract/` folder so Emperator can discover it automatically.

```text
contract/
├── api/            # OpenAPI or GraphQL interface specs
├── conventions.cue # CUE constraints for naming, layout, metadata
├── policy/         # OPA Rego policies for security and governance
├── generators/     # Templates and codemod recipes
└── README.md       # Change log and review checklist
```

Best practices:

- Keep contract artefacts close to the code they govern. Co-locating the contract eliminates drift between documentation and implementation.
- Document intent in `README.md`; include reviewer checklists and links to upstream standards (OWASP, SLSA, internal policies).
- Group generators by language or domain (`generators/python/`, `generators/devsecops/`) to simplify maintenance.

## 2. Define structural conventions with CUE

CUE expresses schema-like constraints succinctly and supports rich validation.

```cue title="contract/conventions.cue"
package contract

controllers: {
  files: [...string] & =~"^[a-z0-9_]+\.py$"
  allowImports: [...string] | *["services", "logging"]
}

formatting: {
  python: {
    formatter: "ruff"
    lineLength: 100
  }
}
```

- The regex ensures controller filenames stay in `snake_case`.
- The `allowImports` array drives layering rules (hooked into Semgrep and CodeQL queries).
- Formatting settings flow into Emperator’s formatter adapters so generated code matches expectations.

Validate CUE edits with `cue vet` or `cue export` during contract review.

## 3. Capture policies with OPA Rego

Use Rego to codify security and governance rules that span multiple analyses.

```rego title="contract/policy/rules.rego"
package contract.security

deny[msg] {
  input.findings[_].rule == "SecretDetection"
  msg := "Hardcoded secret detected"
}

warn[msg] {
  some finding
  finding := input.findings[_]
  finding.rule == "LayeringPolicy"
  finding.severity == "medium"
  msg := sprintf("Layering violation (%s) requires review", [finding.location])
}
```

- Feed Emperator’s findings JSON into OPA to aggregate, suppress, or escalate alerts.
- Use `deny` for blocking issues, `warn` for advisory or transitional policies.
- Keep policies composable; break complex rules into helper modules and import them.

Evaluate policies locally with `opa eval -i findings.json -d contract/policy 'data.contract'`.

## 4. Model API surfaces with OpenAPI or GraphQL

Interface specifications enable Emperator to scaffold handlers, tests, and clients consistently.

```yaml title="contract/api/openapi.yaml"
openapi: 3.1.0
info:
	title: Emperator Reference Contract
	version: 1.2.0
paths:
	/healthz:
		get:
			operationId: getHealth
			responses:
				'200':
					description: OK
```

- Align operation IDs with code generation templates in `contract/generators/`.
- Use shared schemas to enforce DTO structure. Emperator compares schemas against model code using the IR.
- Treat OpenAPI version bumps as contract releases; annotate the change log with migration guidance.

## 5. Create deterministic codemod recipes

- Write LibCST-based Python codemods or OpenRewrite recipes and store them under `contract/generators/`.
- Annotate each recipe with a `safety` tier (`format`, `low`, `medium`, `high`) so the Safety Gate knows whether to auto-apply or require review.
- Include unit tests for codemods where practical (e.g., `tests/generators/test_logging_migration.py`).

## 6. Review and version the contract

Follow a lightweight but disciplined review loop:

```mermaid
flowchart LR
	P[Draft rule change] --> R[Peer review
	(code + policy experts)]
	R --> V[Validate locally
	(cue vet, opa eval, emperor dry-run)]
	V --> D[Decide release tier
	(warn-only or enforce)]
	D --> T[Tag contract version]
	T --> B[Broadcast change
	(docs, release notes, Copilot prompts)]
```

- **Warn-only rollouts:** Introduce new rules in advisory mode first (`severity: info` or `auto_apply: false`) and flip to blocking once noise is under control.
- **Version tags:** Use semantic versioning (`contract@1.3.0`). Emperator logs the active version with every fix, giving auditors traceability.
- **Broadcast:** Update `docs/reference/contract-spec.md` and Copilot prompt packs so automated assistants surface the new expectations.

## 7. Manage exemptions deliberately

- Allow explicit overrides via inline comments such as `# emperator:ignore LayeringPolicy -- justification`. Reject exemptions without a justification string.
- Track approved exemptions in a dedicated file (`contract/exemptions.yaml`) including owner, expiry, and mitigation plan.
- Periodically audit and retire exemptions; Emperator’s governance reports list outstanding waivers.

## 8. Automate contract validation in CI

- Add a job that runs `emperor check --strict --no-fix` against the latest contract to ensure it compiles and that generated rules are lint-free.
- Fail fast if `cue fmt` or `opa fmt` detect formatting issues—consistency keeps diffs minimal.
- Publish generated documentation (mkdocs, SARIF summaries) as build artefacts for reviewers.

With these practices the Project Contract becomes a living, executable specification that guides every code change while remaining auditable and adaptable.

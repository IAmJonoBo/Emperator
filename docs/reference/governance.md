# Governance and Compliance Controls

Emperator reinforces software governance by generating auditable artefacts, enforcing policy-as-code, and keeping a verifiable trail of every automated change. This reference outlines the key mechanisms teams rely on during audits and compliance reviews.

## Architecture Decision Records

- Maintain the ADR log under `docs/adr/`, using zero-padded numbering and the shared template.
- Capture context, evaluated options, the final decision, and follow-up work for every strategic change.
- Reference ADR IDs in related pull requests, contract updates, and `Next_Steps.md` entries so auditors can trace the rationale quickly.

## SBOM production and validation

- Run `emperator sbom --format cyclonedx --output sbom/app.json` in CI after successful checks.
- Merge application SBOMs with base image or infrastructure SBOMs to achieve full-stack visibility.
- Feed generated SBOMs into vulnerability management platforms (Dependency-Track, Azure Defender, etc.) for continuous monitoring.
- Configure contract policies to block disallowed licenses or aged dependencies by querying SBOM metadata in OPA.

| Artefact         | Format             | Purpose                                                               |
| ---------------- | ------------------ | --------------------------------------------------------------------- |
| Application SBOM | CycloneDX JSON     | Documents runtime dependencies for audit trails and CVE scans.        |
| Contract SBOM    | SPDX               | Captures tools, codemod recipes, and templates used in enforcement.   |
| Combined SBOM    | CycloneDX BOM-Link | Links application and infrastructure SBOMs for end-to-end provenance. |

## Provenance and attestations

- Use `emperator attest --out provenance/intoto.jsonl` to emit in-toto statements describing the contract version, Emperator release, and rule outcomes.
- Sign attestations with Sigstore Cosign (`cosign attest --predicate provenance/intoto.jsonl image:tag`) or an internal PKI for regulated environments.
- Store signed attestations alongside release artefacts so auditors can verify origin and integrity.
- Include hashes of generated reports (SARIF, SBOM) inside the attestation payload for tamper evidence.

## Policy enforcement with OPA

- Maintain a dedicated policy package (e.g., `contract/policy/compliance.rego`) that evaluates Emperator findings and SBOM data for compliance thresholds.
- Example rules:
  - Fail builds when critical security findings remain unresolved.
  - Require justification tags for auto-fixes applied to `high` or `critical` rules.
  - Deny merges when contract exemptions exceed a predefined count or expiry window.
- Evaluate policies both locally (`opa eval`) and in CI to ensure consistent decisions across environments.

## Exemption governance {#managing-exemptions}

- Collect all approved waivers in `contract/exemptions.yaml` with owner, expiry, and mitigation plan.
- Schedule a recurring review (e.g., monthly) where compliance leads confirm whether exemptions can be retired.
- Set `emperator check --strict --enforce-expiry` in protected branch pipelines to prevent stale waivers from slipping through.
- Export exemption reports via `emperator explain --format json` and feed them into dashboards for executive visibility.

## Audit-ready logging

- Retain Emperator execution logs with timestamps, rule IDs, auto-fix decisions, and evidence links. Forward logs to a centralized system (Splunk, Elastic) for retention policies.
- Use the `--format json` option to store machine-readable results that can be cross-referenced with ticketing systems.
- Leverage the `docs/includes/copilot-prompts.md` prompts to ensure human reviewers mention rule IDs and contract versions in review comments, improving traceability.

## Documentation standards {#documentation-standards}

- Keep contracts and documentation tightly coupled by updating the [Toolchain Matrix](toolchain.md) and AI prompt include whenever enforcement rules change.
- Use the repository’s documentation CI (`mkdocs build --strict`, `markdownlint-cli2`, `lychee`) to fail fast on broken links or style regressions.
- Mirror CI checks locally via `npx markdownlint-cli2 "docs/**/*.md"` and `lychee --config .lychee.toml docs` so contributors catch issues before opening a pull request.

## Language owners {#language-owners}

- Assign a steward for each language/platform (Python, JVM, JS/TS, Go, Rust, Infrastructure) to review new rules and formatter changes.
- Document ownership in the Project Contract metadata and reference it from team onboarding guides, ensuring contributors know who approves rule updates.
- Schedule quarterly syncs between language owners and product security to evaluate lint noise, codemod quality, and roadmap adjustments.

## Compliance checklist

1. Contract change log updated with rationale and reviewer approvals.
1. Latest SBOMs generated, signed, and archived per release.
1. Attestations attached to build artefacts with verifiable signatures.
1. Exemptions reviewed within SLA and annotated with next steps.
1. SARIF/SAST reports stored for the required compliance retention window.
1. Evidence pack (contract, prompts, test results) bundled for external audits.

Following these practices ensures Emperator’s automation not only keeps codebases healthy but also provides the documentation and traceability auditors expect.

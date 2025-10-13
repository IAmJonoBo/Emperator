# Governance and Compliance Controls

Emperator reinforces software governance by generating auditable artefacts, enforcing policy-as-code, and keeping a verifiable trail of every automated change. This reference outlines the key mechanisms teams rely on during audits and compliance reviews.

## SBOM production and validation

- Run `emperor sbom --format cyclonedx --output sbom/app.json` in CI after successful checks.
- Merge application SBOMs with base image or infrastructure SBOMs to achieve full-stack visibility.
- Feed generated SBOMs into vulnerability management platforms (Dependency-Track, Azure Defender, etc.) for continuous monitoring.
- Configure contract policies to block disallowed licenses or aged dependencies by querying SBOM metadata in OPA.

| Artefact | Format | Purpose |
| --- | --- | --- |
| Application SBOM | CycloneDX JSON | Documents runtime dependencies for audit trails and CVE scans. |
| Contract SBOM | SPDX | Captures tools, codemod recipes, and templates used in enforcement. |
| Combined SBOM | CycloneDX BOM-Link | Links application and infrastructure SBOMs for end-to-end provenance. |

## Provenance and attestations

- Use `emperor attest --out provenance/intoto.jsonl` to emit in-toto statements describing the contract version, Emperator release, and rule outcomes.
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

## Exemption governance

- Collect all approved waivers in `contract/exemptions.yaml` with owner, expiry, and mitigation plan.
- Schedule a recurring review (e.g., monthly) where compliance leads confirm whether exemptions can be retired.
- Set `emperor check --strict --enforce-expiry` in protected branch pipelines to prevent stale waivers from slipping through.
- Export exemption reports via `emperor explain --format json` and feed them into dashboards for executive visibility.

## Audit-ready logging

- Retain Emperator execution logs with timestamps, rule IDs, auto-fix decisions, and evidence links. Forward logs to a centralized system (Splunk, Elastic) for retention policies.
- Use the `--format json` option to store machine-readable results that can be cross-referenced with ticketing systems.
- Leverage the `docs/includes/copilot-prompts.md` prompts to ensure human reviewers mention rule IDs and contract versions in review comments, improving traceability.

## Compliance checklist

1. Contract change log updated with rationale and reviewer approvals.
2. Latest SBOMs generated, signed, and archived per release.
3. Attestations attached to build artefacts with verifiable signatures.
4. Exemptions reviewed within SLA and annotated with next steps.
5. SARIF/SAST reports stored for the required compliance retention window.
6. Evidence pack (contract, prompts, test results) bundled for external audits.

Following these practices ensures Emperator’s automation not only keeps codebases healthy but also provides the documentation and traceability auditors expect.

# DevSecOps and Supply Chain Integration

Emperator embeds compliance and supply chain security controls into everyday development activities so provenance, SBOMs, and policy enforcement stay in lockstep with code changes.

## SBOM discipline and dependency guardrails

- Generate application SBOMs with `emperator sbom --format cyclonedx --output sbom/app.json` and merge them with base image or infrastructure BOMs to achieve full-stack visibility.
- Enforce license allowlists and dependency age thresholds by evaluating SBOM metadata through Rego policies.
- Feed generated SBOMs into vulnerability scanners such as Dependency-Track or Microsoft Defender for continuous monitoring and alerting.

## Provenance and SLSA alignment

- Emit in-toto attestations via `emperator attest --out provenance/intoto.jsonl`; sign them using Sigstore Cosign or internal PKI to establish a verifiable build record.
- Attach signed attestations and SBOMs to release artefacts so auditors can confirm the contract version, Emperator build version, and rule set applied.
- Keep the Project Contract versioned to provide a transparent change log for every standards update.

## Policy as code everywhere

- Store compliance logic in `contract/policy/*.rego` so the same rules can gate commits, CI pipelines, and runtime environments.
- Triangulate Semgrep, CodeQL, and Rego findings to reduce false positives and provide evidence-backed enforcement for security-critical policies.
- Configure rule severities and safety tiers to phase in new mandates gradually (warn → block) without overwhelming legacy codebases.

## Infrastructure-as-code guardrails {#infrastructure-as-code-guardrails}

- Enforce Terraform best practices with `terraform fmt` and `tflint`, keeping configurations aligned with the [Toolchain Matrix](../reference/toolchain.md#recommended-lint-and-formatter-stacks).
- Validate Kubernetes YAML and Helm charts using contract-aware OpenRewrite recipes plus Semgrep policies to prevent privilege escalation and drift.
- Require SBOM and attestation artefacts for infrastructure modules so platform teams can track IaC provenance alongside application deployments.

## Sandbox-friendly execution

- Package Emperator and its dependencies inside offline-friendly containers so classified or air-gapped environments can run the full pipeline with no external calls.
- Cache Semgrep and CodeQL databases between runs to maintain performance while respecting restricted network policies.
- Run optional dynamic checks (e.g., property-based tests) inside hardened temporary directories to limit exposure when executing user code.

## Exemption governance and reporting

- Record waivers in `contract/exemptions.yaml` with owner, expiry, and mitigation notes; Emperator can fail builds when waivers lapse or lack justification.
- Export waiver reports (`emperator explain --exemptions --format table`) for compliance dashboards and recurring review cadences.
- Require review comments to reference rule IDs so accepted risk is always traceable to the originating standard.

By treating supply chain signals as first-class artefacts, Emperator keeps code, policies, and audit evidence synchronized—helping teams reach higher SLSA tiers without bolting on one-off scripts.

# Security Engineering and Safety Envelope

Emperator hardens codebases by combining defense-in-depth analysis with conservative automation safeguards.

## Comprehensive vulnerability coverage

- Runs curated Semgrep and CodeQL query packs aligned with OWASP Top 10 and high-priority CWE categories.
- Uses taint tracking to detect untrusted data flows from external inputs to dangerous sinks (e.g., `os.system`, raw SQL execution).
- Integrates secret scanning patterns to block credentials, tokens, and keys from entering source control.

## Safety tiers for automation {#static-analysis-tiers}

- Classifies rules into tiers (formatting, low, medium, high) so only low-risk fixes auto-apply; higher tiers surface reviewable diffs.
- Re-runs static analysis and optional unit/property tests after every automated change, rolling back any patch that fails validation.
- Enforces idempotence: codemods are expected to produce no further changes when applied twice, preventing oscillating diffs.

## Property-based and regression testing

- Generates Hypothesis-based round-trip tests for designated data structures (e.g., DTO serialization) to confirm behaviour remains intact after refactors.
- Supports codemod regression suites (`emperator codemod verify`) to guarantee recipes remain safe as contracts evolve.

## Exemption hygiene

- Requires waiver annotations to include justification, owner, and expiry; pipeline flags expire soon or missing rationale.
- Produces waiver dashboards so security leads can track accepted risk and schedule remediation work.

## Threat-aware operations

- Runs entirely offline by default, avoiding data exfiltration risks and supporting air-gapped environments.
- Executes optional dynamic checks inside hardened temporary sandboxes to minimise exposure to adversarial code.
- Treats the contract as untrusted input, relying on vetted parsers for OpenAPI, CUE, and Rego to prevent injection attacks against the toolchain.

## Container hardening {#container-hardening}

- Provide hardened base images for developer containers and CI runners with pinned versions of formatters, linters, and Emperator binaries.
- Scan container layers with `hadolint` and follow the [Toolchain Matrix](../reference/toolchain.md#recommended-lint-and-formatter-stacks) to ensure Dockerfiles invoke vetted linters.
- Sign container images and publish SBOMs so downstream teams inherit the same provenance guarantees enforced upstream.

By combining rigorous detection with a “first, do no harm” automation policy, Emperator raises the security baseline without eroding trust in automated refactors.

# Emperator Project Plan Series

This plan packages Emperator’s delivery into sequential, reviewable planning volumes. Each volume closes with auditable evidence (tests, reports, provenance artefacts) before unlocking the next phase, preserving the Contract→IR→Action guarantees and governance controls described in the technical brief.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=63 path=docs/explanation/system-architecture.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/system-architecture.md#L1-L63"}​​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=68 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L1-L68"}​

---

## Document 0 – Foundations & Governance Setup (Weeks 0–2)

### Objectives

- Stand up contributor tooling (uv-managed Python, pnpm, pre-commit) and align every environment with the documented lint/format stacks.​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=200 path=docs/reference/developer-tooling.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/developer-tooling.md#L5-L200"}​​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=164 path=docs/reference/linting-formatting.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/linting-formatting.md#L1-L164"}​
- Baseline the Project Contract skeleton (CUE conventions, Rego policy stub, OpenAPI seed) and register governance expectations (SBOM, attestations, exemption workflow).​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=78 path=docs/reference/contract-spec.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/contract-spec.md#L5-L78"}​​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=39 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L5-L39"}​

### Workstreams

1. Toolchain bootstrap via `scripts/setup-tooling.sh`, ensuring Ruff, Biome/ESLint, yamllint, actionlint, and commitlint execute cleanly locally and in CI.​:codex-file-citation[codex-file-citation]{line_range_start=22 line_range_end=164 path=docs/reference/linting-formatting.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/linting-formatting.md#L22-L164"}​
2. Contract scaffolding: populate `contract/conventions.cue`, `contract/policy/*.rego`, and `contract/api/*.yaml` with minimal enforceable rules drawn from the tutorial samples.​:codex-file-citation[codex-file-citation]{line_range_start=24 line_range_end=111 path=docs/tutorial/getting-started.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/tutorial/getting-started.md#L24-L111"}​
3. Governance wiring: document SBOM/attestation expectations and exemption review cadences; add placeholders for `contract/exemptions.yaml` and provenance storage.​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=68 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L5-L68"}​

### Quality Gates

- `pytest --cov=emperator --cov-report=term-missing`
- `ruff check .`
- `ruff format --check .`
- `mypy src/emperator`
- `bandit -r src/emperator`
- `python -m build` (track SPDX metadata action item)​:codex-file-citation[codex-file-citation]{line_range_start=21 line_range_end=28 path=Next_Steps.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/Next_Steps.md#L21-L28"}​

### Evidence & Deliverables

- Passing CI run containing lint, type, security, and build stages.
- Initial SBOM/attestation templates stored under `sbom/` and `provenance/`.
- Updated `Next_Steps.md` noting tooling readiness and outstanding SPDX remediation.

### Hand-off Criteria

- Contract passes `cue fmt/vet`, `opa check`, and `emperor apply --diff --no-commit --fast` without errors.​:codex-file-citation[codex-file-citation]{line_range_start=71 line_range_end=76 path=docs/reference/contract-spec.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/contract-spec.md#L71-L76"}​
- Governance checklist entries 1–3 satisfied (contract change log, SBOM, attestation location).​:codex-file-citation[codex-file-citation]{line_range_start=61 line_range_end=66 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L61-L66"}​

### Leads & Coordination

- Tooling Steward (DevX)
- Contract Maintainer (Architecture)
- Compliance Lead (Security/Governance)

---

## Document 1 – Phase 1: Python-Focused Slice (Weeks 2–8)

### Objectives

- Deliver the Python slice: contract parsing, IR construction, checks, fixes, and CLI experience outlined in the roadmap.​:codex-file-citation[codex-file-citation]{line_range_start=15 line_range_end=23 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L15-L23"}​
- Ship a demo project exercising naming, layering, and security rules with deterministic fixes and property-based regression tests.​:codex-file-citation[codex-file-citation]{line_range_start=19 line_range_end=23 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L19-L23"}​

### Workstreams

1. Contract enrichment: encode concrete CUE naming/layout rules and Rego security policies; extend OpenAPI spec to drive scaffolds.​:codex-file-citation[codex-file-citation]{line_range_start=17 line_range_end=20 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L17-L20"}​
2. IR & analysis: integrate Tree-sitter, Semgrep, CodeQL flows for Python, caching IR for incremental runs.​:codex-file-citation[codex-file-citation]{line_range_start=41 line_range_end=54 path=docs/explanation/system-architecture.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/system-architecture.md#L41-L54"}​
3. Safety loop: implement property-based validation for codemod output (e.g., DTO round-trip) and ensure idempotent fixes.​:codex-file-citation[codex-file-citation]{line_range_start=21 line_range_end=22 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L21-L22"}​​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=20 path=docs/explanation/security-safety.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/security-safety.md#L5-L20"}​
4. CLI polish: `emperor apply` diff summaries, provenance logging, and exit codes consumable by pre-commit and CI.​:codex-file-citation[codex-file-citation]{line_range_start=3 line_range_end=33 path=docs/explanation/developer-experience.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/developer-experience.md#L3-L33"}​

### Quality Gates

- Baseline suite from Document 0.
- `emperor apply --diff --no-commit --fast` exits cleanly on seed repo and demo violations, producing SARIF.​:codex-file-citation[codex-file-citation]{line_range_start=31 line_range_end=33 path=docs/how-to/ci-integration.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ci-integration.md#L31-L33"}​
- Property-based tests (`emperor test --generators`) pass for generated scaffolds.​:codex-file-citation[codex-file-citation]{line_range_start=31 line_range_end=33 path=docs/how-to/ci-integration.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ci-integration.md#L31-L33"}​

### Evidence & Deliverables

- Demo repository with before/after snapshots and recorded runtime metrics.
- CLI documentation updates in `docs/cli.md` and tutorial walkthrough adjustments.​:codex-file-citation[codex-file-citation]{line_range_start=16 line_range_end=19 path=Next_Steps.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/Next_Steps.md#L16-L19"}​​:codex-file-citation[codex-file-citation]{line_range_start=24 line_range_end=182 path=docs/tutorial/getting-started.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/tutorial/getting-started.md#L24-L182"}​
- SARIF, SBOM, and attestation artefacts archived per governance checklist.​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=66 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L5-L66"}​

### Hand-off Criteria

- Pilot repo shows zero outstanding violations in strict mode; auto-fixes logged with contract version provenance.
- Coverage remains ≥100% for CLI and supporting modules (per existing deliverables).​:codex-file-citation[codex-file-citation]{line_range_start=16 line_range_end=18 path=Next_Steps.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/Next_Steps.md#L16-L18"}​

---

## Document 2 – Phase 2: Feedback Loop Hardening (Weeks 8–12)

### Objectives

- Collect pilot feedback, reduce noise, and harden pre-commit/CI integrations with SARIF uploads and provenance artefacts.​:codex-file-citation[codex-file-citation]{line_range_start=25 line_range_end=29 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L25-L29"}​​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=105 path=docs/how-to/ci-integration.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ci-integration.md#L5-L105"}​
- Expand docs/tutorials with waiver workflows and troubleshooting guidance.

### Workstreams

1. Telemetry: capture runtime metrics, violation counts, and acceptance rate to tune rule severities and noise.​:codex-file-citation[codex-file-citation]{line_range_start=101 line_range_end=105 path=docs/how-to/ci-integration.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ci-integration.md#L101-L105"}​
2. CI packaging: add dedicated Emperator compliance workflow, caching strategies, and SARIF publishing for PRs.​:codex-file-citation[codex-file-citation]{line_range_start=34 line_range_end=74 path=docs/how-to/ci-integration.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ci-integration.md#L34-L74"}​
3. Waiver governance: enforce `contract/exemptions.yaml`, expiry policies, and reporting dashboards.​:codex-file-citation[codex-file-citation]{line_range_start=34 line_range_end=39 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L34-L39"}​

### Quality Gates

- Fast vs full CI modes validated (PR vs main) with documented runtimes.
- Exemption lint (`emperor check --strict --enforce-expiry`) passes without expired waivers.​:codex-file-citation[codex-file-citation]{line_range_start=94 line_range_end=97 path=docs/how-to/ci-integration.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ci-integration.md#L94-L97"}​
- Documentation CI (`mkdocs build --strict`, markdownlint, lychee) green alongside code CI.​:codex-file-citation[codex-file-citation]{line_range_start=47 line_range_end=51 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L47-L51"}​

### Evidence & Deliverables

- Pilot report summarising feedback, noise remediation, and gating decisions.
- Updated Diátaxis docs (how-to, explanation, reference) reflecting new workflows.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=13 path=docs/index.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/index.md#L1-L13"}​
- Runbooks for CI exemptions and provenance handling referenced in governance docs.​:codex-file-citation[codex-file-citation]{line_range_start=18 line_range_end=45 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L18-L45"}​

### Hand-off Criteria

- PR pipeline enforces fast checks; mainline enforces strict mode plus SBOM/attestation production with signed artefacts.​:codex-file-citation[codex-file-citation]{line_range_start=31 line_range_end=105 path=docs/how-to/ci-integration.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ci-integration.md#L31-L105"}​
- User feedback backlog triaged with owners and due dates in `Next_Steps.md`.

---

## Document 3 – Phase 3: Polyglot Expansion (Weeks 12–20)

### Objectives

- Introduce Java and JS/TS support (OpenRewrite, TypeScript AST integrations), broaden Semgrep/CodeQL rule packs, and enhance LSP diagnostics.​:codex-file-citation[codex-file-citation]{line_range_start=31 line_range_end=35 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L31-L35"}​​:codex-file-citation[codex-file-citation]{line_range_start=22 line_range_end=93 path=docs/reference/toolchain.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/toolchain.md#L22-L93"}​
- Align formatter/lint stacks for new ecosystems per Toolchain Matrix and linting reference.

### Workstreams

1. Language adapters: integrate Tree-sitter grammars, CodeQL packs, formatter hooks, and codemod engines for each new language.​:codex-file-citation[codex-file-citation]{line_range_start=22 line_range_end=52 path=docs/reference/toolchain.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/toolchain.md#L22-L52"}​
2. Rule pack expansion: codify organisation-specific security checks and contract metadata for severity tiers/tags.​:codex-file-citation[codex-file-citation]{line_range_start=22 line_range_end=42 path=docs/reference/toolchain.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/toolchain.md#L22-L42"}​​:codex-file-citation[codex-file-citation]{line_range_start=22 line_range_end=48 path=docs/reference/contract-spec.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/contract-spec.md#L22-L48"}​
3. LSP enhancements: deliver richer diagnostics and quick fixes across languages using incremental IR updates.​:codex-file-citation[codex-file-citation]{line_range_start=17 line_range_end=47 path=docs/explanation/developer-experience.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/developer-experience.md#L17-L47"}​

### Quality Gates

- Language-specific lint/format/type/test suites pass in CI (`gofmt`, `golangci-lint`, `eslint`, `tsc`, etc. per matrix).​:codex-file-citation[codex-file-citation]{line_range_start=75 line_range_end=93 path=docs/reference/toolchain.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/toolchain.md#L75-L93"}​
- Contract metadata for new rules includes severity, safety tier, evidence, and tags.​:codex-file-citation[codex-file-citation]{line_range_start=22 line_range_end=36 path=docs/reference/contract-spec.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/contract-spec.md#L22-L36"}​
- Cross-language demo projects show clean runs in both fast and strict modes.

### Evidence & Deliverables

- Updated Toolchain Matrix with supported ecosystems and rollout notes.​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=109 path=docs/reference/toolchain.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/toolchain.md#L1-L109"}​
- LSP release notes documenting diagnostics, quick fix coverage, and offline operation support.​:codex-file-citation[codex-file-citation]{line_range_start=41 line_range_end=61 path=docs/explanation/system-architecture.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/system-architecture.md#L41-L61"}​
- Polyglot sample repositories with recorded run outputs.

### Hand-off Criteria

- CODEOWNERS / language owners assigned and documented for each new stack, with quarterly sync cadence captured in governance reference.​:codex-file-citation[codex-file-citation]{line_range_start=53 line_range_end=57 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L53-L57"}​
- All new languages integrated into automation (pre-commit, CI, docs).

---

## Document 4 – Phase 4: AI Augmentation (Weeks 20–28)

### Objectives

- Enable local LLM assistance following the propose → rank → validate loop, gated by rule safety tiers.​:codex-file-citation[codex-file-citation]{line_range_start=37 line_range_end=41 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L37-L41"}​​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=78 path=docs/how-to/ai-assisted-refactors.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ai-assisted-refactors.md#L1-L78"}​
- Instrument success metrics (auto-resolution rates, acceptance ratios) and convert successful AI transforms into deterministic codemods.

### Workstreams

1. Model provisioning: configure on-prem models, prompt packs, and provenance logging (`emperor ai init`, `emperor explain`).​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=68 path=docs/how-to/ai-assisted-refactors.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ai-assisted-refactors.md#L1-L68"}​​:codex-file-citation[codex-file-citation]{line_range_start=1 line_range_end=68 path=docs/includes/copilot-prompts.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/includes/copilot-prompts.md#L1-L68"}​
2. Safety enforcement: ensure AI suggestions respect safety tiers, run full validation, and emit evidence for audits.​:codex-file-citation[codex-file-citation]{line_range_start=69 line_range_end=115 path=docs/how-to/ai-assisted-refactors.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ai-assisted-refactors.md#L69-L115"}​​:codex-file-citation[codex-file-citation]{line_range_start=18 line_range_end=45 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L18-L45"}​
3. Regression harness: expand codemod verification suites and property-based tests for AI-generated patches.​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=24 path=docs/explanation/security-safety.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/security-safety.md#L5-L24"}​

### Quality Gates

- AI-assisted changes must pass existing baseline commands plus `emperor explain --last` provenance checks.
- Rejection feedback loop tracked; prompts adjusted when success rate falls below target thresholds.

### Evidence & Deliverables

- AI operations guide (model configuration, approval workflow, rollback).
- Metrics dashboard summarising AI usage, acceptance, and runtime.

### Hand-off Criteria

- Only `formatting`/`low` tier rules auto-apply AI fixes; higher tiers require human approval with documented rationale.​:codex-file-citation[codex-file-citation]{line_range_start=69 line_range_end=88 path=docs/how-to/ai-assisted-refactors.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/how-to/ai-assisted-refactors.md#L69-L88"}​
- Provenance records stored with SBOM/attestation artefacts per governance checklist.​:codex-file-citation[codex-file-citation]{line_range_start=18 line_range_end=45 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L18-L45"}​

---

## Document 5 – Phase 5: Governance & Reporting (Weeks 28–36)

### Objectives

- Deliver dashboards/reports covering contract compliance, SBOM status, waiver aging, and risk alignment; finalise audit evidence packs.​:codex-file-citation[codex-file-citation]{line_range_start=43 line_range_end=47 path=docs/explanation/implementation-roadmap.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/implementation-roadmap.md#L43-L47"}​​:codex-file-citation[codex-file-citation]{line_range_start=47 line_range_end=66 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L47-L66"}​
- Integrate with risk management systems and formalise release workflows with signed attestations and evidence bundling.

### Workstreams

1. Reporting pipeline: automate generation of HTML/JSON summaries, feed data into dashboards, and store artefacts with signatures.​:codex-file-citation[codex-file-citation]{line_range_start=18 line_range_end=45 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L18-L45"}​
2. Compliance automation: run scheduled waiver reviews, licence checks, and policy evaluations with OPA gating.​:codex-file-citation[codex-file-citation]{line_range_start=25 line_range_end=40 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L25-L40"}​
3. Release governance: enforce SLSA-aligned provenance, SBOM publication, and audit pack archival across environments.​:codex-file-citation[codex-file-citation]{line_range_start=5 line_range_end=52 path=docs/explanation/devsecops-supply-chain.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/explanation/devsecops-supply-chain.md#L5-L52"}​

### Quality Gates

- All releases accompanied by SBOM, attestation, SARIF, waiver report, and contract changelog entries.
- Governance checklist items 1–6 verified before marking the document complete.​:codex-file-citation[codex-file-citation]{line_range_start=61 line_range_end=66 path=docs/reference/governance.md git_url="https://github.com/IAmJonoBo/Emperator/blob/main/docs/reference/governance.md#L61-L66"}​

### Evidence & Deliverables

- Executive dashboard/report kit summarising key metrics and compliance posture.
- Runbooks for audit preparation and incident response referencing Emperator artefacts.

### Hand-off Criteria

- Contract governance process institutionalised (owners, cadence, tooling) with documented KPIs and risk thresholds.
- Final review confirms every previous document’s deliverables remain green; plan transitions into steady-state maintenance.

---

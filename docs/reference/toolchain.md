# Toolchain Matrix

Reference chart for the analyzers, codemods, formatters, and CLI options Emperator orchestrates. Use it alongside the [Getting Started tutorial](../tutorial/getting-started.md), the [Developer Tooling reference](developer-tooling.md), and the [System Architecture deep dive](../explanation/system-architecture.md) to map from contract capabilities to the concrete tooling each team needs.

```mermaid
graph LR
Contract[Project Contract]
Analyzer[Static analyzers<br/>(Tree-sitter, Semgrep, CodeQL)]
Codemods[Deterministic codemods]
Formatters[Formatter integrations]
Reports[SBOMs & Attestations]
Contract --> Analyzer
Analyzer --> Codemods
Codemods --> Formatters
Analyzer --> Reports
Formatters --> Reports
Reports --> Feedback[Developer & CI feedback loops]
```

## Static analysis support

| Language                | Tree-sitter | CodeQL  | Semgrep | Notes                                                                                                                                                              |
| ----------------------- | ----------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Python                  | ✔           | ✔       | ✔       | Full stack with LibCST codemods and Ruff formatter (see [AI-assisted refactors](../how-to/ai-assisted-refactors.md)).                                              |
| Java                    | ✔           | ✔       | ✔       | Leverages OpenRewrite recipes for framework upgrades; tie into [Implementation roadmap](../explanation/implementation-roadmap.md).                                 |
| JavaScript / TypeScript | ✔           | Partial | ✔       | CodeQL JS pack supports security queries; OpenRewrite JS recipes available; aligns with [contract authoring guide](../how-to/author-contract.md).                  |
| Go                      | ✔           | ✔       | ✔       | gofmt integration for formatting; see [CI integration playbook](../how-to/ci-integration.md) for caching guidance.                                                 |
| C / C++                 | ✔           | ✔       | Partial | Semgrep coverage limited to focused rules; clang-format handles formatting; reference [Security and Safety posture](../explanation/security-safety.md).            |
| Ruby                    | ✔           | ✖       | ✔       | Relies on Semgrep and Tree-sitter; consider Sorbet integration for deeper analysis.                                                                                |
| Shell                   | ✔           | ✖       | ✔       | Static analysis limited to Semgrep patterns and shellcheck (optional plugin); pair with [Developer experience guardrails](../explanation/developer-experience.md). |

## Codemod engines

| Ecosystem             | Engine                   | Typical use cases                                                 | Safety tier guidance                                                         |
| --------------------- | ------------------------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Python                | LibCST                   | API migrations, string formatting upgrades, import normalization. | `formatting` or `low` by default; raise to `medium` for behavioural changes. |
| JVM (Java/Kotlin)     | OpenRewrite              | Dependency upgrades, Spring migrations, logging refactors.        | `low`–`medium` depending on recipe maturity.                                 |
| JavaScript/TypeScript | TS AST + OpenRewrite JS  | Deprecated API replacements, lint autofixes.                      | `low` when AST transform is deterministic.                                   |
| YAML / XML            | OpenRewrite              | Configuration rewrites (Kubernetes manifests, Maven POM).         | `low` (structure-preserving).                                                |
| Go                    | Custom go/ast transforms | Interface renames, dependency injection wiring.                   | `medium` unless validated by tests.                                          |
| C/C++                 | Clang-Tidy refactors     | Modernization (auto, nullptr), includes reorder.                  | `medium` due to potential macro interactions.                                |

## Formatter integrations

| Language                | Formatter                      | Invocation                                                   |
| ----------------------- | ------------------------------ | ------------------------------------------------------------ |
| Python                  | Ruff / Black                   | `ruff check --fix` (primary) with optional `black` fallback. |
| JavaScript / TypeScript | Prettier                       | `prettier --write` respecting contract-defined settings.     |
| Java                    | google-java-format or Spotless | Configured via contract metadata.                            |
| Go                      | gofmt                          | `gofmt -w` with module-aware path filtering.                 |
| C / C++                 | clang-format                   | Style file generated from contract defaults.                 |
| Markdown / YAML         | mdformat / prettier            | Keeps documentation and config consistent with docs build.   |

## CLI highlights

| Command                | Purpose                                                                               | Notes                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `emperator apply`      | Compile contract, run checks, apply safe fixes, and re-validate.                      | Use `--diff`, `--no-commit`, `--fast`, or `--strict` depending on context. |
| `emperator check`      | Run checks without applying fixes.                                                    | Pair with `--format sarif` for CI uploads.                                 |
| `emperator explain`    | Show provenance of the last run (contract version, applied rules, AI model metadata). | Helpful when auditing AI-assisted changes or exemption usage.              |
| `emperator sbom`       | Generate CycloneDX or SPDX SBOMs from dependency manifests and IR metadata.           | Supports `--format cyclonedx\|spdx` and `--output` path options.           |
| `emperator attest`     | Produce in-toto attestations capturing rule enforcement and tool versions.            | Combine with Sigstore Cosign for signed provenance.                        |
| `emperator ai suggest` | Request AI-generated fixes for a finding set.                                         | Respects rule safety tiers and always triggers the validation loop.        |

## Environment variables

| Variable                  | Effect                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `EMPERATOR_CONTRACT_PATH` | Override default `contract/` directory. Useful for monorepos.                        |
| `EMPERATOR_CACHE_DIR`     | Set location for IR caches (Tree-sitter, CodeQL). Configure in CI for faster reruns. |
| `EMPERATOR_AI_ENABLED`    | Toggle AI-assisted workflows (`0` or `1`).                                           |
| `EMPERATOR_STRICT_MODE`   | Force `--strict` behaviour even if CLI flag omitted (handy in protected branches).   |
| `EMPERATOR_TRACE`         | Enable verbose logging for debugging integration issues.                             |

## Recommended lint and formatter stacks

| Ecosystem                         | Primary tooling                    | Notes                                                                                                                                                                                                          |
| --------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python                            | Ruff (`ruff check`, `ruff format`) | Drop-in for Flake8/Black/isort with 10–100× speedups; see the [AI-assisted refactors how-to](../how-to/ai-assisted-refactors.md#lint-aware-fixes) for Ruff-aware codemods.                                     |
| JavaScript / TypeScript (Track A) | ESLint + Prettier                  | Default pairing across most projects; Prettier also covers JSON, YAML, Markdown; referenced in the [Developer experience overview](../explanation/developer-experience.md).                                    |
| JavaScript / TypeScript (Track B) | Biome                              | Single binary for lint + format with safe/unsafe fix modes; ideal for air-gapped environments described in [System architecture](../explanation/system-architecture.md#offline-operation).                     |
| Go                                | gofmt + golangci-lint              | gofmt enforces canonical style; golangci-lint aggregates fast parallel linters, matching the [CI integration guide](../how-to/ci-integration.md#2-stage-checks-in-ci).                                         |
| Java                              | google-java-format + Error Prone   | Deterministic formatting with compile-time bug pattern checks; add Spotless as wrapper if needed (see [Implementation roadmap](../explanation/implementation-roadmap.md#phase-2-rollout)).                     |
| Kotlin                            | ktlint + detekt                    | ktlint enforces Kotlin style; detekt flags code smells and supports baselining legacy issues—baseline workflow covered in [Governance reference](../reference/governance.md#managing-exemptions).              |
| Rust                              | rustfmt + Clippy                   | Shipping defaults that encode community idioms and over 750 lint rules; evaluate findings via [Security and Safety posture](../explanation/security-safety.md#static-analysis-tiers).                          |
| C / C++                           | clang-format + clang-tidy          | clang-format standardizes layout; clang-tidy provides static analysis and modernization checks, complementing [System architecture](../explanation/system-architecture.md#action-engines-and-safety-envelope). |
| Shell                             | shfmt + ShellCheck                 | shfmt for consistent indentation; ShellCheck for common shell pitfalls; rollout tips in [Implementation roadmap](../explanation/implementation-roadmap.md#phase-3-organization-wide-enforcement).              |
| Protobuf                          | buf format + buf lint              | Ensures consistent style and forward-compatible API design; integrates with [Contract spec reference](../reference/contract-spec.md#protobuf-schemas).                                                         |
| Terraform                         | terraform fmt + TFLint             | Canonical formatting plus provider-aware linting and security checks; see [DevSecOps supply chain](../explanation/devsecops-supply-chain.md#infrastructure-as-code-guardrails).                                |
| Dockerfiles                       | hadolint                           | AST-based linting that also shells through to ShellCheck for `RUN` commands; reference [Security and Safety posture](../explanation/security-safety.md#container-hardening).                                   |
| YAML / JSON / Markdown            | Prettier + yamllint + markdownlint | Prettier handles structure; yamllint and markdownlint enforce semantics; aligns with [Docs governance](../reference/governance.md#documentation-standards).                                                    |
| TOML                              | Taplo                              | Formatter and LSP support for manifests (Cargo, Config); tie into [Developer experience](../explanation/developer-experience.md#language-tooling).                                                             |
| .NET / C#                         | dotnet format + Roslyn analyzers   | Aligns with `.editorconfig`; Roslyn analyzers supply style and quality rules, mapped to [Contract governance](../reference/governance.md#language-owners).                                                     |

## Related playbooks

- Get a hands-on walkthrough in the [Getting Started tutorial](../tutorial/getting-started.md).
- Embed these checks in delivery pipelines with the [CI/CD integration guide](../how-to/ci-integration.md).
- Author new standards using the [Contract authoring guide](../how-to/author-contract.md) and tie them back to this matrix.
- Explore architecture rationale in [System Architecture](../explanation/system-architecture.md) and [Developer Experience](../explanation/developer-experience.md).
- Tune rollout sequencing with the [Implementation roadmap](../explanation/implementation-roadmap.md) and [Governance reference](../reference/governance.md).

## Automation to keep this reference current

- The repository’s [Docs CI workflow](https://github.com/IAmJonoBo/Emperator/blob/main/.github/workflows/docs-ci.yml) now runs `mkdocs build --strict`, `markdownlint-cli2`, and [`lychee`](https://github.com/IAmJonoBo/Emperator/blob/main/.lychee.toml) to catch formatting drift, lint violations, and broken links before merge.
- Configuration lives alongside the docs ([`.markdownlint.jsonc`](https://github.com/IAmJonoBo/Emperator/blob/main/.markdownlint.jsonc), [`.lychee.toml`](https://github.com/IAmJonoBo/Emperator/blob/main/.lychee.toml)) so teams can evolve rules with contract updates and share the same compliance defaults locally via `npx markdownlint-cli2` and `lychee --config .lychee.toml docs`.
- Pair the CI checks with local `pre-commit` hooks (see [CI/CD integration guide](../how-to/ci-integration.md#1-align-local-and-ci-workflows)) so editors, pipelines, and published docs stay synchronized.

Keep this matrix updated as you expand language support or onboard new teams so everyone shares the same expectations about analyser coverage and automation guarantees.

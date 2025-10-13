# Toolchain Matrix

Reference chart for the analyzers, codemods, formatters, and CLI options Emperator orchestrates. Use it to confirm support coverage and choose the right flags for different workflows.

## Static analysis support

| Language | Tree-sitter | CodeQL | Semgrep | Notes |
| --- | --- | --- | --- | --- |
| Python | ✔ | ✔ | ✔ | Full stack with LibCST codemods and Ruff formatter. |
| Java | ✔ | ✔ | ✔ | Leverages OpenRewrite recipes for framework upgrades. |
| JavaScript / TypeScript | ✔ | Partial | ✔ | CodeQL JS pack supports security queries; OpenRewrite JS recipes available. |
| Go | ✔ | ✔ | ✔ | gofmt integration for formatting. |
| C / C++ | ✔ | ✔ | Partial | Semgrep coverage limited to focused rules; clang-format handles formatting. |
| Ruby | ✔ | ✖ | ✔ | Relies on Semgrep and Tree-sitter; consider Sorbet integration for deeper analysis. |
| Shell | ✔ | ✖ | ✔ | Static analysis limited to Semgrep patterns and shellcheck (optional plugin). |

## Codemod engines

| Ecosystem | Engine | Typical use cases | Safety tier guidance |
| --- | --- | --- | --- |
| Python | LibCST | API migrations, string formatting upgrades, import normalization. | `formatting` or `low` by default; raise to `medium` for behavioural changes. |
| JVM (Java/Kotlin) | OpenRewrite | Dependency upgrades, Spring migrations, logging refactors. | `low`–`medium` depending on recipe maturity. |
| JavaScript/TypeScript | TS AST + OpenRewrite JS | Deprecated API replacements, lint autofixes. | `low` when AST transform is deterministic. |
| YAML / XML | OpenRewrite | Configuration rewrites (Kubernetes manifests, Maven POM). | `low` (structure-preserving). |
| Go | Custom go/ast transforms | Interface renames, dependency injection wiring. | `medium` unless validated by tests. |
| C/C++ | Clang-Tidy refactors | Modernization (auto, nullptr), includes reorder. | `medium` due to potential macro interactions. |

## Formatter integrations

| Language | Formatter | Invocation |
| --- | --- | --- |
| Python | Ruff / Black | `ruff check --fix` (primary) with optional `black` fallback. |
| JavaScript / TypeScript | Prettier | `prettier --write` respecting contract-defined settings. |
| Java | google-java-format or Spotless | Configured via contract metadata. |
| Go | gofmt | `gofmt -w` with module-aware path filtering. |
| C / C++ | clang-format | Style file generated from contract defaults. |
| Markdown / YAML | mdformat / prettier | Keeps documentation and config consistent with docs build. |

## CLI highlights

| Command | Purpose | Notes |
| --- | --- | --- |
| `emperor apply` | Compile contract, run checks, apply safe fixes, and re-validate. | Use `--diff`, `--no-commit`, `--fast`, or `--strict` depending on context. |
| `emperor check` | Run checks without applying fixes. | Pair with `--format sarif` for CI uploads. |
| `emperor explain` | Show provenance of the last run (contract version, applied rules, AI model metadata). | Helpful when auditing AI-assisted changes or exemption usage. |
| `emperor sbom` | Generate CycloneDX or SPDX SBOMs from dependency manifests and IR metadata. | Supports `--format cyclonedx\|spdx` and `--output` path options. |
| `emperor attest` | Produce in-toto attestations capturing rule enforcement and tool versions. | Combine with Sigstore Cosign for signed provenance. |
| `emperor ai suggest` | Request AI-generated fixes for a finding set. | Respects rule safety tiers and always triggers the validation loop. |

## Environment variables

| Variable | Effect |
| --- | --- |
| `EMPERATOR_CONTRACT_PATH` | Override default `contract/` directory. Useful for monorepos. |
| `EMPERATOR_CACHE_DIR` | Set location for IR caches (Tree-sitter, CodeQL). Configure in CI for faster reruns. |
| `EMPERATOR_AI_ENABLED` | Toggle AI-assisted workflows (`0` or `1`). |
| `EMPERATOR_STRICT_MODE` | Force `--strict` behaviour even if CLI flag omitted (handy in protected branches). |
| `EMPERATOR_TRACE` | Enable verbose logging for debugging integration issues. |

## Recommended lint and formatter stacks

| Ecosystem | Primary tooling | Notes |
| --- | --- | --- |
| Python | Ruff (`ruff check`, `ruff format`) | Drop-in for Flake8/Black/isort with 10–100× speedups. Keep Black only if its exact formatting is mandated. |
| JavaScript / TypeScript (Track A) | ESLint + Prettier | Default pairing across most projects; Prettier also covers JSON, YAML, Markdown. |
| JavaScript / TypeScript (Track B) | Biome | Single binary for lint + format with safe/unsafe fix modes; ideal for air-gapped environments. |
| Go | gofmt + golangci-lint | gofmt enforces canonical style; golangci-lint aggregates fast parallel linters. |
| Java | google-java-format + Error Prone | Deterministic formatting with compile-time bug pattern checks; add Spotless as wrapper if needed. |
| Kotlin | ktlint + detekt | ktlint enforces Kotlin style; detekt flags code smells and supports baselining legacy issues. |
| Rust | rustfmt + Clippy | Shipping defaults that encode community idioms and over 750 lint rules. |
| C / C++ | clang-format + clang-tidy | clang-format standardizes layout; clang-tidy provides static analysis and modernization checks. |
| Shell | shfmt + ShellCheck | shfmt for consistent indentation; ShellCheck for common shell pitfalls. |
| Protobuf | buf format + buf lint | Ensures consistent style and forward-compatible API design. |
| Terraform | terraform fmt + TFLint | Canonical formatting plus provider-aware linting and security checks. |
| Dockerfiles | hadolint | AST-based linting that also shells through to ShellCheck for `RUN` commands. |
| YAML / JSON / Markdown | Prettier + yamllint + markdownlint | Prettier handles structure; yamllint and markdownlint enforce semantics. |
| TOML | Taplo | Formatter and LSP support for manifests (Cargo, Config). |
| .NET / C# | dotnet format + Roslyn analyzers | Aligns with `.editorconfig`; Roslyn analyzers supply style and quality rules. |

Keep this matrix updated as you expand language support or onboard new teams so everyone shares the same expectations about analyser coverage and automation guarantees.

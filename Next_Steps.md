# Next Steps

## Tasks

> **Status snapshot:** Sprint 4 Weeks 1-3 now complete with IR builder, Semgrep rule generation, and the CodeQL pipeline operational. Week 4 (Correlation) remains pending. Sprint 5 safety envelope work is queued after Sprint 4 completion.

### Sprint 4 – IR & Analysis Integration (per `docs/explanation/sprint-4-ir-analysis.md`)

**Week 1: IR Foundation (T+0 to T+5 days)** ✅ **COMPLETE**

- [x] Implement `IRBuilder` with Tree-sitter integration for Python (Owner: AI, Completed: 2025-10-15)
- [x] Add Python symbol extraction (functions, classes, imports) (Owner: AI, Completed: 2025-10-15)
- [x] Create cache schema and persistence layer in `.emperator/ir-cache/` (Owner: AI, Completed: 2025-10-15)
- [x] Write unit tests for parser service with ≥95% coverage (Owner: AI, Completed: 2025-10-15)
- [x] Document IR cache format in `docs/reference/ir-format.md` (Owner: AI, Completed: 2025-10-15)

**Week 2: Semgrep Integration (T+5 to T+10 days)** ✅ **COMPLETE**

- [x] Implement Semgrep rule generator from contract conventions (Owner: AI, Completed: 2025-10-15)
- [x] Map CUE conventions to Semgrep patterns (Owner: AI, Completed: 2025-10-15)
- [x] Extract security rules from Rego policies (Owner: AI, Completed: 2025-10-15)
- [x] Generate rule packs in `contract/generated/semgrep/` (Owner: AI, Completed: 2025-10-15)
- [x] Integrate with CLI and add validation tests (Owner: AI, Completed: 2025-10-15)

**Week 3: CodeQL Pipeline (T+10 to T+15 days)**

- [x] Implement CodeQL database manager with lifecycle commands (Owner: Maintainers, Completed: Current pass)
- [x] Create query library for security checks in `rules/codeql/` (Owner: Maintainers, Completed: Current pass)
- [x] Add CLI commands: `emperator analysis codeql create/query/list/prune` (Owner: Maintainers, Completed: Current pass)
- [x] Document query development workflow in `docs/how-to/develop-codeql-queries.md` (Owner: Maintainers, Completed: Current pass)

**Week 4: Correlation & Benchmarks (T+15 to T+20 days)**

- [ ] Implement correlation engine linking findings to contract rules (Owner: AI, Due: 2025-10-28)
- [ ] Add remediation guidance extraction from contract metadata (Owner: AI, Due: 2025-10-28)
- [ ] Create benchmark suite in `tests/benchmarks/` (Owner: Maintainers, Due: 2025-10-29)
- [ ] Run performance tests and verify thresholds (Owner: Maintainers, Due: 2025-10-29)
- [ ] Generate performance baseline report in `docs/metrics/sprint-4-baseline.md` (Owner: Maintainers, Due: 2025-10-29)
- [ ] Prepare Sprint 4 demo with artifacts in `examples/sprint-4-demo/` (Owner: Maintainers, Due: 2025-10-29)

**Documentation Updates:**

- [x] Create `docs/explanation/ir-architecture.md` (Owner: AI, Completed: 2025-10-15)
- [x] Create `docs/how-to/use-ir-cache.md` (Owner: AI, Completed: 2025-10-15)
- [x] Update `docs/reference/toolchain.md` with Tree-sitter/CodeQL requirements (Owner: AI, Completed: Current pass)
- [x] Update `docs/explanation/system-architecture.md` with IR layer details (Owner: AI, Completed: Current pass)

### Sprint 5 – Automated Fix & Safety Envelope (per `docs/explanation/sprint-5-safety-envelope.md`)

**Week 1: Risk Classification & LibCST Foundation (T+0 to T+5 days)**

- [ ] Implement risk classifier with four-tier system (0-3) (Owner: AI, Due: 2025-10-31)
- [ ] Create LibCST transformer base classes and registry (Owner: AI, Due: 2025-11-01)
- [ ] Implement RenameTransformer and DeprecatedAPITransformer (Owner: AI, Due: 2025-11-02)
- [ ] Add syntax validation and unified diff generation (Owner: AI, Due: 2025-11-02)
- [ ] Write unit tests for transformers with ≥95% coverage (Owner: AI, Due: 2025-11-03)
- [ ] Document transformer catalog in `docs/reference/fix-transformers.md` (Owner: AI, Due: 2025-11-03)

**Week 2: Validation Pipeline (T+5 to T+10 days)**

- [ ] Implement validation orchestrator with pre/post-check coordination (Owner: Maintainers, Due: 2025-11-04)
- [ ] Add pre-check validation (static analysis, test execution) (Owner: Maintainers, Due: 2025-11-05)
- [ ] Implement post-check validation (syntax, diff scope, re-run tests) (Owner: Maintainers, Due: 2025-11-05)
- [ ] Integrate with Ruff/Mypy/pytest for validation checks (Owner: Maintainers, Due: 2025-11-06)
- [ ] Add test selection logic to reduce validation time (Owner: Maintainers, Due: 2025-11-06)
- [ ] Create CLI command: `emperator fix validate` (Owner: Maintainers, Due: 2025-11-06)

**Week 3: Rollback & Approval Workflows (T+10 to T+15 days)**

- [ ] Implement rollback manager with git stash/commit strategies (Owner: Maintainers, Due: 2025-11-08)
- [ ] Add provenance metadata to commit messages with full audit trail (Owner: Maintainers, Due: 2025-11-09)
- [ ] Create interactive approval CLI for Tier 2+ fixes (Owner: AI, Due: 2025-11-10)
- [ ] Build batch approval workflow for efficient review (Owner: AI, Due: 2025-11-10)
- [ ] Enhance telemetry with fix outcome tracking and rollback events (Owner: Maintainers, Due: 2025-11-11)

**Week 4: OpenRewrite, Property Tests, Documentation (T+15 to T+20 days)**

- [ ] Integrate OpenRewrite for Java/Kotlin transformations (Owner: Maintainers, Due: 2025-11-12)
- [ ] Create OpenRewrite recipe generator from contract rules (Owner: Maintainers, Due: 2025-11-12)
- [ ] Implement property-based tests with Hypothesis (idempotence, syntax preservation) (Owner: AI, Due: 2025-11-13)
- [ ] Write comprehensive documentation in `docs/how-to/apply-fixes-safely.md` (Owner: AI, Due: 2025-11-13)
- [ ] Create operational playbooks for rollback and incident response (Owner: Maintainers, Due: 2025-11-14)
- [ ] Run end-to-end testing on sample repositories (Owner: Maintainers, Due: 2025-11-15)
- [ ] Prepare Sprint 5 demo with fix application scenarios (Owner: Maintainers, Due: 2025-11-15)

**Documentation Updates:**

- [ ] Create `docs/explanation/safety-envelope-design.md` (comprehensive design doc) (Owner: AI, Due: 2025-11-03)
- [ ] Update `docs/how-to/ai-assisted-refactors.md` with fix tier guidance (Owner: AI, Due: 2025-11-05)
- [ ] Update `docs/explanation/security-safety.md` with validation strategies (Owner: AI, Due: 2025-11-06)
- [ ] Create CI integration examples in `docs/how-to/ci-integration.md` (Owner: AI, Due: 2025-11-07)

### Outstanding Platform Hygiene

- [x] Backfill coverage for formatting/tooling helpers (mdformat wrapper, SARIF bundler, cache prune) (Owner: Maintainers, Due: 2025-10-25)
- [x] Document mdformat edge cases and Ruff auto-fix behaviour in troubleshooting guides (Owner: Maintainers, Due: 2025-10-25)
- [x] Investigate pytest-cov gaps for formatting/tooling fixtures highlighted during current pass (Owner: Maintainers, Due: 2025-10-25)
- [x] Establish contract validation as a pre-merge quality gate (Owner: Maintainers, Due: 2025-10-28)
- [x] Explore automated severity gating for analyzer output summarisation (Owner: Maintainers, Due: 2025-10-30)
- [x] Introduce targeted lint lane (`pnpm lint:changed`) to accelerate feedback loops (Owner: Maintainers, Due: Current pass)

### Historical completions

- [x] Adopt Ruff `ALL` baseline, staged linting, and SARIF workflows per IMPLEMENT_THEN_DELETE.md (Owner: AI, Due: Current pass)
- [x] Integrate Markdown formatting and cache environment exports across tooling scripts (Owner: AI, Due: Current pass)
- [x] Repair contract and formatter tests after formatter/lint migration (Owner: AI, Due: Current pass)
- [x] Add contract validation CLI command with structural checks and strict mode (Owner: AI, Due: Current pass)
- [x] Update CLI documentation to cover contract validation workflows (Owner: AI, Due: Current pass)
- [x] Refactor Typer option definitions to satisfy Ruff boolean argument rules while retaining CLI flags (Owner: AI, Due: Current pass)
- [x] Re-run full lint/test/type/build pipeline after Ruff refactor (Owner: AI, Due: Current pass)
- [x] Resolve CLI telemetry summary typing regression and severity deduplication (Owner: AI, Due: Current pass)
- [x] Extend analysis run tests for severity filters, metadata capture, and validation errors (Owner: AI, Due: Current pass)
- [x] Establish scaffolding CLI and environment doctor (Owner: AI, Due: T+0)
- [x] Publish comprehensive delivery and sprint plans to guide implementation (Owner: AI, Due: Current pass)
- [x] Resolve import-order lint failure in `tests/test_doctor.py` (`ruff check --no-fix .`) (Owner: AI, Due: Current pass)
- [x] Install `types-PyYAML` or adjust contract loader to satisfy mypy (Owner: AI, Due: Current pass)
- [x] Investigate pytest coverage warning (`No data was collected`) and ensure reports generate (Owner: AI, Due: Current pass)
- [x] Ship analysis planning CLI (inspect + wizard) with developer hints (Owner: AI, Due: Current pass)
- [x] Extend doctor checks for uv CLI and harden remediation execution failures (Owner: AI, Due: Current pass)
- [x] Prototype Semgrep/CodeQL invocation flow using new analysis scaffolding (Owner: AI, Due: Current pass)
- [x] Harden YAML formatter + formatter check mode (`pnpm fmt -- --check`) to stabilise CI (Owner: AI, Due: Current pass)
- [x] Remove Apple-specific cleanup scripts and GitHub workflow now that git hygiene covers metadata (Owner: AI, Due: Current pass)
- [x] Stand up ADR template + initial decisions for hardening sprint scope (Owner: AI, Due: Current pass)
- [x] Track SPDX license string remediation for `pyproject.toml` (Owner: Maintainers, Due: Current pass)
- [x] Model analyzer execution telemetry + caching strategy for follow-up automation (Owner: AI, Due: Current pass)
- [x] Implement analyzer telemetry persistence once design lands (Owner: Maintainers, Due: Current pass)
- [x] Evaluate automated guardrails for regenerated YAML assets (contract + compose) to prevent accidental churn (Owner: AI, Due: Current pass)
- [x] Prototype JSONL-backed telemetry store and CLI integration flag (Owner: AI, Due: Current pass)
- [x] Thread telemetry capture through analyzer execution once orchestration lands (Owner: Maintainers, Due: Current pass)
- [x] Extend analyzer run UX with richer filtering (severity, dry-run) options (Owner: AI, Due: Current pass)
- [x] Add analyzer command severity metadata and CLI validation for severity filters (Owner: AI, Due: Current pass)
- [x] Record severity filter selections in telemetry + documentation updates (Owner: AI, Due: Current pass)
- [x] Harden telemetry store against corrupted JSONL entries and add atomic writes (Owner: AI, Due: Current pass)
- [x] Surface analyzer runner OSErrors as telemetry events with actionable notes (Owner: AI, Due: Current pass)

## Steps

- Current focus: executing the remediation program (docs/explanation/implementation-roadmap.md#integrated-remediation-plan) starting with IR builder scaffolding, dependency bootstrapping, and CLI entry points.
- In progress: documenting how Semgrep, CodeQL, and IR caches must integrate once the generators and correlation engine exist, using `docs/reference/toolchain.md` and `docs/explanation/system-architecture.md` to steer contributions.
- Completed: restored CodeQL manager + CLI test coverage (≥91% overall) and re-ran full lint/format/test/build/security suite post-additions.
- Planned: codifying Sprint 5 safety envelope requirements (rollback workflow, telemetry, documentation) informed by `emperator_specs/Project_Plan.md` and `docs/explanation/security-safety.md`.
- Completed: shipped `pnpm lint:changed` for quick Ruff/Biome/ESLint passes on changed files to complement the full lint suite.
- Completed: migrated lint/format workflow (Ruff `ALL`, mdformat, staged linting, SARIF bundling, cache exports) and resolved resulting contract/formatter regressions.
- Completed: established contract validation CLI with strict-mode escalation and tabled warnings in output.
- Completed: refactored analysis run summary helpers for deterministic severity rendering and mypy compliance.
- Completed: strengthened CLI severity flows with metadata capture and invalid-option coverage.
- Completed: hardened CLI telemetry path handling (JSONL-only enforcement, relative path resolution).
- Completed: audited documentation, aligned structure with scaffold utilities, and seeded TODO-driven stubs.
- Completed: delivered CLI with scaffold, doctor, and fix commands plus progress visualisation.
- Completed: added analysis inspect/wizard workflows with progress bars and guided hints for IR readiness.
- Completed: produced end-to-end delivery plan and sprint playbook to steer execution.
- Completed: elevated `emperator.contract` helpers with cached OpenAPI loader, typed metadata surface, and doc references.
- Completed: hardened doctor checks (uv detection, remediation error capture) and surfaced analyzer execution plans.
- Completed: expanded formatter pipeline with YAML multi-document support, configurable indentation/width, and `pnpm fmt --check` dry-run.
- Completed: normalised Ruff formatter baseline, added run-format conflict coverage, and documented mdformat troubleshooting guidance.
- Completed: removed legacy Apple cleanup automation after confirming `.gitignore` coverage and workflow redundancy.
- Completed: seeded ADR template (`docs/adr/0000-template.md`) and recorded sprint-driving decisions (ADR-0001/0002).
- Completed: remediated packaging metadata before setuptools deprecates table syntax.
- Completed: designed analyzer telemetry primitives, fingerprinting helper, and ADR to steer persistence work.
- Completed: implemented JSONL telemetry store + CLI banners to unlock cached-run awareness.
- Completed: landed JSONL telemetry store with CLI banner + persistence hooks; awaiting analyzer execution wiring for automatic capture.
- Completed: wired analyzer execution helper and CLI run command to persist telemetry with progress reporting.
- Completed: introduced YAML guardrail digests with CLI verification to prevent unintended churn in contract and compose assets.
- Completed: upgraded `analysis run` UX with severity filtering, dry-run support, and richer telemetry metadata.
- Completed: enforced analyzer command severity metadata, CLI validation errors, and telemetry capture for severity filters.
- Completed: hardened JSONL telemetry store to skip malformed entries and rewrite atomically.
- Completed: improved analyzer execution resilience by capturing missing binary errors in telemetry output.
- Completed: refactored Typer option helpers to appease Ruff `FBT003` while keeping `--apply`/`--dry-run` ergonomics intact and reran validation suite.

## Deliverables

- ✅ Contract validation CLI command with structural validation helpers and strict-mode coverage.
- ✅ Tooling migration artifacts: Ruff `ALL` config, mdformat integration, staged lint + SARIF scripts, cache prune helper, and CI pre-commit job with artifacts.
- ✅ Additional CLI regression tests covering severity aggregation, metadata persistence, and invalid filter handling.
- ✅ Developer CLI (`src/emperator/cli.py`) with scaffold/doctor/fix workflows and 100% coverage.
- ✅ Scaffolding + doctor utility modules with TODO-stub generation and remediation metadata.
- ✅ Documentation updates (`README.md`, `docs/index.md`, `docs/cli.md`) highlighting the workflow.
- ✅ JSONL-backed telemetry store with unit coverage + CLI integration banner for cached runs.
- ✅ Expanded docs (`docs/cli.md`, `docs/explanation/*`) covering analysis planning wizard, run command, and progress feedback.
- ✅ Repository assets populated with TODO placeholders for policy, conventions, rules, and infra blueprints.
- ✅ Delivery blueprint (`emperator_specs/Project_Plan.md`) and sprint playbook (`emperator_specs/Sprint_Playbook.md`).
- ✅ Analyzer execution plans for Semgrep and CodeQL surfaced via CLI (`analysis plan`) with defensive doctor integrations.
- ✅ Analyzer execution helper + `analysis run` command with telemetry persistence, filtering, and Rich progress output.
- ✅ Targeted lint command (`pnpm lint:changed`) to run Ruff, Biome, and ESLint against changed files for faster local loops.
- ✅ Formatter regression tests (`tests/test_formatting.py`) covering YAML multi-docs, environment tuning, and `pnpm fmt --check` flow.
- ✅ ADR log bootstrapped (`docs/adr/` + governance/index references) documenting sprint focus areas.
- ✅ Telemetry design captured in ADR-0003 with accompanying analysis module primitives and unit tests.
- ✅ Guardrail digest tracking (`guardrails/yaml-digests.json`) plus CLI verification command and dedicated tests.
- ✅ Analyzer UX upgrade with severity filters, dry-run simulation, and updated CLI documentation.
- ✅ Analyzer execution now honours severity metadata during runs and records skipped steps in telemetry notes.
- ✅ Severity gating surfaced in analysis summaries with PASS/REVIEW/BLOCK badges, run-level escalation notes, and refreshed docs/tests.
- ✅ CLI telemetry configuration validates JSONL path usage and documents relative resolution behaviour.
- ✅ JSONL telemetry store ignores corrupted lines, rewrites atomically, and retains valid run history with coverage.
- ✅ Analyzer execution handles missing binaries gracefully, emitting exit-code notes and telemetry metadata.
- ✅ **Sprint 4 & 5 comprehensive planning documents:**
  - `docs/explanation/sprint-4-ir-analysis.md` – Detailed IR builder, Semgrep, CodeQL integration plan
  - `docs/explanation/sprint-5-safety-envelope.md` – Comprehensive safety envelope design and implementation plan
- ✅ **Architecture Decision Records:**
  - ADR-0004: IR Builder Architecture and Caching Strategy
  - ADR-0005: Safety Envelope Design for Automated Code Fixes
- ✅ **Sprint 4 Week 1 deliverables (IR Builder):**
  - `src/emperator/ir/` package with IRBuilder, SymbolExtractor, CacheManager
  - CLI commands: `emperator ir parse`, `emperator ir cache`
  - 19 comprehensive tests (100% passing)
  - Documentation: `docs/reference/ir-format.md`, `docs/explanation/ir-architecture.md`, `docs/how-to/use-ir-cache.md`
  - Tree-sitter, LibCST, MessagePack dependencies integrated
- ✅ **Sprint 4 Week 2 deliverables (Semgrep Integration):**
  - `src/emperator/rules/` package with SemgrepRuleGenerator
  - CLI commands: `emperator rules generate`, `emperator rules validate`
  - 7 rules across 3 categories (naming, security, architecture)
  - 14 comprehensive tests (100% passing)
  - Generated rule packs in `contract/generated/semgrep/`
- ⏳ Sprint 4 Week 3-4 (CodeQL pipeline, correlation engine, benchmarks) – implementation pending
- ⏳ Sprint 5 deliverables (safety envelope, rollback playbooks, telemetry uplift) – detailed plan created, implementation pending per `docs/explanation/sprint-5-safety-envelope.md`.

## Quality Gates

- ✅ Tests: `uv run pytest` (153 passed, 94% coverage across source modules including new IR and rules).
- ✅ Format: `pnpm fmt -- --check` (Ruff + mdformat + YAML formatter all succeed on current tree).
- ✅ Lint: `pnpm lint`.
- ✅ Types: `uv run mypy src`.
- ✅ Security: `uv run --with bandit bandit -r src` (no issues).
- ⚠️ Security: `uv run --with pip-audit pip-audit` (fails due to container SSL trust store; requires upstream certificate fix).
- ✅ Build: `uv run --with build python -m build` (setuptools warns about deprecated license table; schedule SPDX string follow-up).
- ✅ Contract: `uv run --extra dev emperator contract validate --strict` enforced via dedicated CI job prior to lint/tests/build.
- ✅ Telemetry caching: Fingerprint helper landed with unit coverage; JSONL persistence prototype implemented with CLI integration.
- ✅ Guardrails: `emperator guardrails verify` succeeds with digests tracked in `guardrails/yaml-digests.json`.

## Links

- CLI reference: `docs/cli.md`.
- Directory blueprint: `directory_structure.md`.
- Delivery artefacts: `emperator_specs/Project_Plan.md`, `emperator_specs/Sprint_Playbook.md`.
- **Sprint planning:**
  - Sprint 4 detailed plan: `docs/explanation/sprint-4-ir-analysis.md`
  - Sprint 5 detailed plan: `docs/explanation/sprint-5-safety-envelope.md`
- **Architecture decisions:**
  - ADR-0004: IR Builder Architecture: `docs/adr/0004-ir-builder-architecture.md`
  - ADR-0005: Safety Envelope Design: `docs/adr/0005-safety-envelope-design.md`
- Analyzer run usage: `emperator analysis run` (telemetry-backed analyzer execution).
- Analyzer plan usage: `emperator analysis plan` (Semgrep/CodeQL command scaffolding).
- Telemetry design: `docs/adr/0003-analyzer-telemetry-architecture.md`, `src/emperator/analysis.py` telemetry helpers.
- Toolchain + safety context: `docs/reference/toolchain.md`, `docs/explanation/system-architecture.md`, `docs/explanation/security-safety.md`, `docs/how-to/ci-integration.md`, `docs/how-to/ai-assisted-refactors.md`.

## Risks/Notes

- IR builder, analyzer correlation, and safety envelope are pending; repository currently lacks Tree-sitter bindings, Semgrep rule packs, CodeQL helpers, LibCST/Hypothesis dependencies, or fix modules required by ADR-0004/0005.
- Formatter stack now enforces Ruff single quotes + mdformat tables; run `pnpm fmt -- --check` before applying fixes to review doc table rewrites and Python quote flips.
- CLI severity guardrails rely on substring matching to associate notes with tools; monitor for future false positives as telemetry volume grows.
- Telemetry path overrides now require the JSONL backend; ensure docs and onboarding scripts stay aligned as new stores land.
- Auto-remediation commands default to dry-run; explicit `--apply` required for mutations.
- CLI commands rely on optional tools (`pnpm`, bash scripts); doctor command surfaces missing dependencies gracefully.
- Contract metadata helpers cache the OpenAPI document; clear the cache (`load_contract_spec.cache_clear()`) if tests need to observe on-disk edits within a single process.
- Monitor future work to expand analyzer execution UX (additional filters, dry-run simulation) without regressing telemetry fidelity.
- Keep `FORMAT_YAML_INCLUDE_LOCKS=1` escape hatch documented before enabling lockfile formatting globally; default skip prevents inadvertent churn.
- Removing platform-specific scripts shifts responsibility to git hygiene; verify future platform issues through ADRs before reintroducing tooling.
- Telemetry events remain local-only by default; document opt-in remote uploads before shipping alternative stores.
- Monitor `.emperator/telemetry` lifecycle (retention, rotation) as analyzer orchestration begins writing runs automatically.
- Severity gating currently skips only tagged steps; evaluate richer filtering and summarisation pipelines before enabling hard failures.
- Telemetry store now drops malformed JSONL entries silently; consider emitting warnings or metrics in future hardening passes.
- Contract validation currently enforces structural checks; integrate full OpenAPI schema validation tooling in future sprints if dependency policy allows.
- Maintain 100% coverage for analysis/CLI modules; tighten review on future changes that introduce untested branches.
- CI now blocks on the contract validation gate; coordinate rollout communications so contributors expect the additional job latency.
- Ruff auto-fix mode is enabled; `pnpm lint` will rewrite Python sources/tests when issues are detected—communicate before running in shared branches.
- `pnpm lint:changed` requires `uv` and pnpm to be on PATH; ensure developer workstations install tooling via `scripts/setup-tooling.sh` before relying on the quick pass.
- mdformat rewrites Markdown structure (lists/tables); audit semantic diffs during follow-up documentation edits.
- `pip-audit` continues to fail in this container due to missing trust anchors; rerun once the SSL root store is corrected or swap to an offline advisory cache.

# Next Steps

## Tasks

### Sprint 4 – IR & Analysis Integration (per `emperator_specs/Sprint_Playbook.md`)

- [ ] Finalise IR builder backlog slice (Tree-sitter ingestion, incremental updates, cache strategy) referencing `docs/explanation/system-architecture.md` (Owner: AI, Due: 2025-10-22)
- [ ] Map Semgrep rule translation workflow from contract conventions to runnable packs and document storage in `docs/how-to/ci-integration.md` (Owner: Maintainers, Due: 2025-10-24)
- [ ] Prototype CodeQL database generation pipeline with cache hints and CLI integration (Owner: Maintainers, Due: 2025-10-27)
- [ ] Design findings-to-contract correlation model aligned with `docs/reference/contract-spec.md` and `docs/reference/toolchain.md` (Owner: AI, Due: 2025-10-27)
- [ ] Record performance benchmarks (IR build time, analyzer execution) and acceptance thresholds for Sprint 4 demo (Owner: Maintainers, Due: 2025-10-29)

### Sprint 5 – Safety Envelope Preparation (per `emperator_specs/Project_Plan.md`)

- [ ] Draft rollback + double-run validation checklist using guidance from `docs/explanation/security-safety.md` (Owner: Maintainers, Due: 2025-11-03)
- [ ] Enumerate codemod safety tiers and gating rules for `emperator apply` with links to `docs/how-to/ai-assisted-refactors.md` (Owner: AI, Due: 2025-11-04)
- [ ] Identify telemetry enhancements required for automated fix audits (pre/post-run data capture, provenance) referencing `docs/adr/0003-analyzer-telemetry-architecture.md` (Owner: Maintainers, Due: 2025-11-05)
- [ ] Align documentation updates (tutorial walkthrough, governance reference) for safety envelope rollout (Owner: AI, Due: 2025-11-06)

### Outstanding Platform Hygiene

- [x] Backfill coverage for formatting/tooling helpers (mdformat wrapper, SARIF bundler, cache prune) (Owner: Maintainers, Due: 2025-10-25)
- [x] Document mdformat edge cases and Ruff auto-fix behaviour in troubleshooting guides (Owner: Maintainers, Due: 2025-10-25)
- [ ] Investigate pytest-cov gaps for formatting/tooling fixtures highlighted during current pass (Owner: Maintainers, Due: 2025-10-25)
- [ ] Establish contract validation as a pre-merge quality gate (Owner: Maintainers, Due: 2025-10-28)
- [ ] Explore automated severity gating for analyzer output summarisation (Owner: Maintainers, Due: 2025-10-30)

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

- Current focus: translating Sprint 4 backlog items into actionable engineering tickets covering IR ingestion, analyzer orchestration, and performance benchmarks (`emperator_specs/Sprint_Playbook.md`).
- In progress: documenting how Semgrep, CodeQL, and IR caches interact using `docs/reference/toolchain.md` and `docs/explanation/system-architecture.md` as shared context for contributors.
- Planned: codifying Sprint 5 safety envelope requirements (rollback workflow, telemetry, documentation) informed by `emperator_specs/Project_Plan.md` and `docs/explanation/security-safety.md`.
- Completed: migrated lint/format workflow (Ruff `ALL`, mdformat, staged linting, SARIF bundling, cache exports) and resolved resulting contract/formatter regressions.
- Completed: established contract validation CLI with strict-mode escalation and tabled warnings in output.
- Completed: refactored analysis run summary helpers for deterministic severity rendering and mypy compliance.
- Completed: strengthened CLI severity flows with metadata capture and invalid-option coverage.
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
- ✅ Formatter regression tests (`tests/test_formatting.py`) covering YAML multi-docs, environment tuning, and `pnpm fmt --check` flow.
- ✅ ADR log bootstrapped (`docs/adr/` + governance/index references) documenting sprint focus areas.
- ✅ Telemetry design captured in ADR-0003 with accompanying analysis module primitives and unit tests.
- ✅ Guardrail digest tracking (`guardrails/yaml-digests.json`) plus CLI verification command and dedicated tests.
- ✅ Analyzer UX upgrade with severity filters, dry-run simulation, and updated CLI documentation.
- ✅ Analyzer execution now honours severity metadata during runs and records skipped steps in telemetry notes.
- ✅ JSONL telemetry store ignores corrupted lines, rewrites atomically, and retains valid run history with coverage.
- ✅ Analyzer execution handles missing binaries gracefully, emitting exit-code notes and telemetry metadata.
- ⏳ Sprint 4 deliverables (IR builder, Semgrep/CodeQL integration, findings correlation, performance benchmarks) – in planning per `docs/explanation/system-architecture.md`, `docs/reference/toolchain.md`, and `emperator_specs/Sprint_Playbook.md`.
- ⏳ Sprint 5 deliverables (safety envelope, rollback playbooks, telemetry uplift) – discovery underway guided by `emperator_specs/Project_Plan.md` and `docs/explanation/security-safety.md`.

## Quality Gates

- ✅ Tests: `uv run --with pytest-cov --with httpx pytest --cov=src/emperator --cov=tests --cov-report=term-missing` (107 passed, 99% coverage; formatting/tooling helper coverage follow-up remains).
- ✅ Format: `pnpm fmt -- --check` (Ruff + mdformat + YAML formatter all succeed on current tree).
- ✅ Lint: `pnpm lint`.
- ✅ Types: `uv run mypy src`.
- ✅ Security: `uv run --with bandit bandit -r src` (no issues).
- ⚠️ Security: `uv run --with pip-audit pip-audit` (fails due to container SSL trust store; requires upstream certificate fix).
- ✅ Build: `uv run --with build python -m build` (setuptools warns about deprecated license table; schedule SPDX string follow-up).
- ✅ Contract: `emperator contract validate --strict` to gate OpenAPI changes.
- ✅ Telemetry caching: Fingerprint helper landed with unit coverage; JSONL persistence prototype implemented with CLI integration.
- ✅ Guardrails: `emperator guardrails verify` succeeds with digests tracked in `guardrails/yaml-digests.json`.

## Links

- CLI reference: `docs/cli.md`.
- Directory blueprint: `directory_structure.md`.
- Delivery artefacts: `emperator_specs/Project_Plan.md`, `emperator_specs/Sprint_Playbook.md`.
- Analyzer run usage: `emperator analysis run` (telemetry-backed analyzer execution).
- Analyzer plan usage: `emperator analysis plan` (Semgrep/CodeQL command scaffolding).
- Telemetry design: `docs/adr/0003-analyzer-telemetry-architecture.md`, `src/emperator/analysis.py` telemetry helpers.
- Toolchain + safety context: `docs/reference/toolchain.md`, `docs/explanation/system-architecture.md`, `docs/explanation/security-safety.md`, `docs/how-to/ci-integration.md`, `docs/how-to/ai-assisted-refactors.md`.

## Risks/Notes

- Formatter stack now enforces Ruff single quotes + mdformat tables; run `pnpm fmt -- --check` before applying fixes to review doc table rewrites and Python quote flips.
- CLI severity guardrails rely on substring matching to associate notes with tools; monitor for future false positives as telemetry volume grows.
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
- Coverage for select formatting/tooling fixture branches remains at 99%; schedule targeted tests or adjust expectations before raising quality gate thresholds.
- Ruff auto-fix mode is enabled; `pnpm lint` will rewrite Python sources/tests when issues are detected—communicate before running in shared branches.
- mdformat rewrites Markdown structure (lists/tables); audit semantic diffs during follow-up documentation edits.
- `pip-audit` continues to fail in this container due to missing trust anchors; rerun once the SSL root store is corrected or swap to an offline advisory cache.

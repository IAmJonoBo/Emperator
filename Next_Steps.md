# Next Steps

## Tasks

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
- [ ] Evaluate automated guardrails for regenerated YAML assets (contract + compose) to prevent accidental churn (Owner: Maintainers, Due: Upcoming sprint)
- [x] Prototype JSONL-backed telemetry store and CLI integration flag (Owner: AI, Due: Current pass)
- [x] Thread telemetry capture through analyzer execution once orchestration lands (Owner: Maintainers, Due: Current pass)
- [ ] Extend analyzer run UX with richer filtering (severity, dry-run) options (Owner: Maintainers, Due: Upcoming sprint)

## Steps

- Completed: audited documentation, aligned structure with scaffold utilities, and seeded TODO-driven stubs.
- Completed: delivered CLI with scaffold, doctor, and fix commands plus progress visualisation.
- Completed: added analysis inspect/wizard workflows with progress bars and guided hints for IR readiness.
- Completed: produced end-to-end delivery plan and sprint playbook to steer execution.
- Completed: elevated `emperator.contract` helpers with cached OpenAPI loader, typed metadata surface, and doc references.
- Completed: hardened doctor checks (uv detection, remediation error capture) and surfaced analyzer execution plans.
- Completed: expanded formatter pipeline with YAML multi-document support, configurable indentation/width, and `pnpm fmt --check` dry-run.
- Completed: removed legacy Apple cleanup automation after confirming `.gitignore` coverage and workflow redundancy.
- Completed: seeded ADR template (`docs/adr/0000-template.md`) and recorded sprint-driving decisions (ADR-0001/0002).
- Completed: remediated packaging metadata before setuptools deprecates table syntax.
- Completed: designed analyzer telemetry primitives, fingerprinting helper, and ADR to steer persistence work.
- Completed: implemented JSONL telemetry store + CLI banners to unlock cached-run awareness.
- Completed: landed JSONL telemetry store with CLI banner + persistence hooks; awaiting analyzer execution wiring for automatic capture.
- Completed: wired analyzer execution helper and CLI run command to persist telemetry with progress reporting.

## Deliverables

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

## Quality Gates

- ✅ Tests: `uv run --with pytest-cov --with httpx pytest --cov=emperator --cov-report=term-missing` (77 passed, 100% coverage).
- ✅ Lint: `uv run ruff check --no-fix .`.
- ✅ Types: `uv run mypy src`.
- ✅ Security: `uv run --with bandit bandit -r src` (no issues).
- ✅ Build: `uv run --with build python -m build` (warning resolved after SPDX remediation).
- ✅ Telemetry caching: Fingerprint helper landed with unit coverage; JSONL persistence prototype implemented with CLI integration.
- ✅ Format check: `pnpm fmt -- --check` (dry-run pipeline clean after YAML tooling hardening).

## Links

- CLI reference: `docs/cli.md`.
- Directory blueprint: `directory_structure.md`.
- Delivery artefacts: `emperator_specs/Project_Plan.md`, `emperator_specs/Sprint_Playbook.md`.
- Analyzer run usage: `emperator analysis run` (telemetry-backed analyzer execution).
- Analyzer plan usage: `emperator analysis plan` (Semgrep/CodeQL command scaffolding).
- Telemetry design: `docs/adr/0003-analyzer-telemetry-architecture.md`, `src/emperator/analysis.py` telemetry helpers.

## Risks/Notes

- Auto-remediation commands default to dry-run; explicit `--apply` required for mutations.
- CLI commands rely on optional tools (`pnpm`, bash scripts); doctor command surfaces missing dependencies gracefully.
- Contract metadata helpers cache the OpenAPI document; clear the cache (`load_contract_spec.cache_clear()`) if tests need to observe on-disk edits within a single process.
- Monitor future work to expand analyzer execution UX (additional filters, dry-run simulation) without regressing telemetry fidelity.
- Keep `FORMAT_YAML_INCLUDE_LOCKS=1` escape hatch documented before enabling lockfile formatting globally; default skip prevents inadvertent churn.
- Removing platform-specific scripts shifts responsibility to git hygiene; verify future platform issues through ADRs before reintroducing tooling.
- Telemetry events remain local-only by default; document opt-in remote uploads before shipping alternative stores.
- Monitor `.emperator/telemetry` lifecycle (retention, rotation) as analyzer orchestration begins writing runs automatically.

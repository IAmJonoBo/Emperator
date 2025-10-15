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
- [ ] Track SPDX license string remediation for `pyproject.toml` (Owner: Maintainers, Due: Future release)
- [ ] Model analyzer execution telemetry + caching strategy for follow-up automation (Owner: AI, Due: Next pass)
- [ ] Evaluate automated guardrails for regenerated YAML assets (contract + compose) to prevent accidental churn (Owner: Maintainers, Due: Upcoming sprint)

## Steps

- Completed: audited documentation, aligned structure with scaffold utilities, and seeded TODO-driven stubs.
- Completed: delivered CLI with scaffold, doctor, and fix commands plus progress visualisation.
- Completed: added analysis inspect/wizard workflows with progress bars and guided hints for IR readiness.
- Completed: produced end-to-end delivery plan and sprint playbook to steer execution.
- Completed: elevated `emperator.contract` helpers with cached OpenAPI loader, typed metadata surface, and doc references.
- Completed: hardened doctor checks (uv detection, remediation error capture) and surfaced analyzer execution plans.
- Completed: expanded formatter pipeline with YAML multi-document support, configurable indentation/width, and `pnpm fmt --check` dry-run.
- Pending: remediate packaging metadata before setuptools deprecates table syntax.
- Pending: capture analyzer run outputs for historical telemetry and CLI caching.

## Deliverables

- ✅ Developer CLI (`src/emperator/cli.py`) with scaffold/doctor/fix workflows and 100% coverage.
- ✅ Scaffolding + doctor utility modules with TODO-stub generation and remediation metadata.
- ✅ Documentation updates (`README.md`, `docs/index.md`, `docs/cli.md`) highlighting the workflow.
- ✅ Expanded docs (`docs/cli.md`, `docs/explanation/*`) covering analysis planning wizard and progress feedback.
- ✅ Repository assets populated with TODO placeholders for policy, conventions, rules, and infra blueprints.
- ✅ Delivery blueprint (`emperator_specs/Project_Plan.md`) and sprint playbook (`emperator_specs/Sprint_Playbook.md`).
- ✅ Analyzer execution plans for Semgrep and CodeQL surfaced via CLI (`analysis plan`) with defensive doctor integrations.
- ✅ Formatter regression tests (`tests/test_formatting.py`) covering YAML multi-docs, environment tuning, and `pnpm fmt --check` flow.

## Quality Gates

- ✅ Tests: `uv run --with pytest-cov --with httpx pytest --cov=emperator --cov-report=term-missing` (54 passed, 100% coverage).
- ✅ Lint: `uv run ruff check --no-fix .`.
- ✅ Types: `uv run mypy src`.
- ✅ Security: `uv run --with bandit bandit -r src` (no issues).
- ⚠ Build: `uv run --with build python -m build` (succeeds with setuptools SPDX license deprecation warning).
- 🔁 Telemetry caching: Pending design for analyzer execution history (target next pass).
- ✅ Format check: `pnpm fmt -- --check` (dry-run pipeline clean after YAML tooling hardening).

## Links

- CLI reference: `docs/cli.md`.
- Directory blueprint: `directory_structure.md`.
- Delivery artefacts: `emperator_specs/Project_Plan.md`, `emperator_specs/Sprint_Playbook.md`.
- Build warning context: `python -m build` output (SPDX reminder).
- Analyzer plan usage: `emperator analysis plan` (Semgrep/CodeQL command scaffolding).

## Risks/Notes

- Auto-remediation commands default to dry-run; explicit `--apply` required for mutations.
- CLI commands rely on optional tools (`pnpm`, bash scripts); doctor command surfaces missing dependencies gracefully.
- Contract metadata helpers cache the OpenAPI document; clear the cache (`load_contract_spec.cache_clear()`) if tests need to observe on-disk edits within a single process.
- Follow up on packaging metadata warning before setuptools deadline.
- Monitor future work to hook Semgrep/CodeQL execution into the new analysis pipeline without regressing UX; next sprint will explore telemetry capture and caching.
- Keep `FORMAT_YAML_INCLUDE_LOCKS=1` escape hatch documented before enabling lockfile formatting globally; default skip prevents inadvertent churn.

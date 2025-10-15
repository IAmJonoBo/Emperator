# Next Steps

## Tasks

- [x] Establish scaffolding CLI and environment doctor (Owner: AI, Due: T+0)
- [x] Publish comprehensive delivery and sprint plans to guide implementation (Owner: AI, Due: Current pass)
- [x] Resolve import-order lint failure in `tests/test_doctor.py` (`ruff check --no-fix .`) (Owner: AI, Due: Current pass)
- [x] Install `types-PyYAML` or adjust contract loader to satisfy mypy (Owner: AI, Due: Current pass)
- [x] Investigate pytest coverage warning (`No data was collected`) and ensure reports generate (Owner: AI, Due: Current pass)
- [ ] Track SPDX license string remediation for `pyproject.toml` (Owner: Maintainers, Due: Future release)

## Steps

- Completed: audited documentation, aligned structure with scaffold utilities, and seeded TODO-driven stubs.
- Completed: delivered CLI with scaffold, doctor, and fix commands plus progress visualisation.
- Completed: produced end-to-end delivery plan and sprint playbook to steer execution.
- Completed: elevated `emperator.contract` helpers with cached OpenAPI loader, typed metadata surface, and doc references.
- Pending: remediate packaging metadata before setuptools deprecates table syntax.

## Deliverables

- ✅ Developer CLI (`src/emperator/cli.py`) with scaffold/doctor/fix workflows and 100% coverage.
- ✅ Scaffolding + doctor utility modules with TODO-stub generation and remediation metadata.
- ✅ Documentation updates (`README.md`, `docs/index.md`, `docs/cli.md`) highlighting the workflow.
- ✅ Repository assets populated with TODO placeholders for policy, conventions, rules, and infra blueprints.
- ✅ Delivery blueprint (`emperator_specs/Project_Plan.md`) and sprint playbook (`emperator_specs/Sprint_Playbook.md`).

## Quality Gates

- ✅ Tests: `uv run --with pytest-cov --with httpx pytest --cov=emperator --cov-report=term-missing` (32 passed, 100% coverage). 
- ✅ Lint: `uv run ruff check --no-fix .`.
- ✅ Types: `uv run mypy src`.
- ✅ Security: `uv run --with bandit bandit -r src` (no issues).
- ⚠ Build: `uv run --with build python -m build` (succeeds with setuptools SPDX license deprecation warning).

## Links

- CLI reference: `docs/cli.md`.
- Directory blueprint: `directory_structure.md`.
- Delivery artefacts: `emperator_specs/Project_Plan.md`, `emperator_specs/Sprint_Playbook.md`.
- Build warning context: `python -m build` output (SPDX reminder).

## Risks/Notes

- Auto-remediation commands default to dry-run; explicit `--apply` required for mutations.
- CLI commands rely on optional tools (`pnpm`, bash scripts); doctor command surfaces missing dependencies gracefully.
- Contract metadata helpers cache the OpenAPI document; clear the cache (`load_contract_spec.cache_clear()`) if tests need to observe on-disk edits within a single process.
- Follow up on packaging metadata warning before setuptools deadline.

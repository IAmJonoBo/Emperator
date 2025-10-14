# Next Steps

## Tasks
- [x] Establish scaffolding CLI and environment doctor (Owner: AI, Due: T+0)
- [ ] Track SPDX license string remediation for `pyproject.toml` (Owner: Maintainers, Due: Future release)

## Steps
- Completed: audited documentation, aligned structure with scaffold utilities, and seeded TODO-driven stubs.
- Completed: delivered CLI with scaffold, doctor, and fix commands plus progress visualisation.
- Pending: update licensing metadata before build tooling deprecates table syntax.

## Deliverables
- ✅ Developer CLI (`emperator/src/emperator/cli.py`) with scaffold/doctor/fix workflows and 100% coverage.
- ✅ Scaffolding + doctor utility modules with TODO-stub generation and remediation metadata.
- ✅ Documentation updates (`README.md`, `emperator/docs/index.md`, `emperator/docs/cli.md`) highlighting the workflow.
- ✅ Repository assets populated with TODO placeholders for policy, conventions, rules, and infra blueprints.

## Quality Gates
- ✅ Tests: `pytest --cov=emperator --cov-report=term-missing` (100% coverage).
- ✅ Lint: `ruff check .`.
- ✅ Format: `ruff format --check .`.
- ✅ Types: `mypy emperator/src/emperator`.
- ✅ Security: `bandit -r emperator/src/emperator`.
- ✅ Build: `python -m build` (note license deprecation warning to resolve later).

## Links
- CLI reference: `emperator/docs/cli.md`.
- Directory blueprint: `directory_structure.md`.
- Build warning context: `python -m build` output (SPDX reminder).

## Risks/Notes
- Auto-remediation commands default to dry-run; explicit `--apply` required for mutations.
- CLI commands rely on optional tools (`pnpm`, bash scripts); doctor command surfaces missing dependencies gracefully.
- Follow up on packaging metadata warning before setuptools deadline.

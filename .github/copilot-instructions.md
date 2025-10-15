# Copilot Instructions for Emperator

## Project Overview
- Emperator is a Python 3.11+ platform scaffolding a FastAPI service, Typer CLI, and contract-driven automation tooling.
- The repo also ships docs (MkDocs + static site), IaC blueprints, and policy contracts. Generated artefacts live in `site/` and `dist/`.

## Repository Layout
- `src/emperator/`: runtime code (FastAPI app, CLI entry point, helpers).
- `contract/`: OpenAPI spec, CUE conventions, Rego policies, generators.
- `docs/`: Markdown sources for MkDocs; HTML in `site/` is prebuilt and should not be edited.
- `compose/`: Docker compose definitions for local API work.
- `infra/`: Kubernetes and Terraform overlays.
- `scripts/`: automation entry points (`setup-tooling.sh`, `run-format.mjs`, etc.).
- Tests live under `tests/` and target the CLI, API contract, and scaffolding helpers.

## Tooling & Environment
- Always bootstrap with `./scripts/setup-tooling.sh` (or `pnpm run setup:tooling`). It installs the Python venv via `uv`, pulls Node toolchains, and wires hooks.
- Prefer `uv run <cmd>` once the environment is synced. Examples: `uv run pytest`, `uv run ruff check .`, `uv run mypy src`.
- Node tasks use pnpm **10.18.3**. Enable corepack (`corepack enable pnpm`) before running `pnpm` commands.
- Pre-commit hooks mirror CI; respect their checks rather than skipping.

## Build, Test, and Lint
- Python: `uv run pytest` for tests, `uv run ruff check .` for lint, `uv run mypy src` for typing.
- JS/JSON/YAML formatting: `pnpm fmt` (or `pnpm fmt:yaml` / `pnpm fmt:biome` for narrower scopes).
- Aggregate lint: `pnpm lint` (ruff + biome + eslint) and `pnpm check` (Biome).
- FastAPI dev server: `uv run uvicorn emperator.api:app --reload`.
- Use `docker compose -f compose/compose.dev.yaml up` for containerized runs when needed.
- Docs preview: `mkdocs serve` from `docs/` after ensuring dependencies via `uv run pip install mkdocs` if not already present.

## Coding Conventions
- Python: Ruff enforces 100-char lines, single quotes, import sorting; keep modules under `src/emperator/` and add tests in `tests/`.
- TypeScript/JavaScript: ESM modules (`type: module`); Biome manages formatting; ESLint with `@eslint/js` + `eslint-plugin-import` is authoritative.
- Do not hand-edit `site/`, `dist/`, or generated metadata under `emperator.egg-info/`—regenerate via the documented scripts instead.
- Documentation is Markdown with MkDocs front-matter; keep tables pipe-aligned and prefer relative links inside `docs/`.

## Guidance for Copilot
- When adding features, update both implementation (`src/emperator/`) and supporting contract/docs (`contract/`, `docs/`) so automation stays in sync.
- Prefer calling existing scripts or CLI commands instead of reimplementing shell pipelines; check `scripts/` for helpers before writing new ones.
- Surface new configuration through the contract where possible rather than hardcoding paths.
- Include validation steps (pytest, `pnpm lint`, relevant script) in suggested workflows so generated PRs pass CI.
- Follow existing naming: CLI commands use lowercase with hyphenated options; environment variables use `EMPERATOR_*` prefixes.
- If uncertain about repo-specific behavior, consult `AGENTS.md` (root) and related instructions files before inventing new conventions.

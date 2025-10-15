# Emperator Monorepo

This repository contains the specification assets under `emperator_specs/` and the implementation scaffold directly in this repository’s root (see `contract/`, `src/`, `infra/`, etc.). The scaffold follows the canonical structure defined in `directory_structure.md` and is ready for application code, infrastructure, and contract artifacts.

## Getting Started

1. Run `./scripts/setup-tooling.sh` (or `pnpm run setup:tooling`) to create the `.venv/` virtual environment, install Python dev extras, fetch Node tooling, and wire up the shared lint hooks. Pass `--ci` when running in automation so the script avoids workspace writes.
2. Activate the virtual environment: `source .venv/bin/activate`.
3. Run the test suite: `pytest tests`.
4. Start the local API: `uvicorn emperator.api:app --reload`.
5. Populate the contract, source, and infrastructure directories with real assets as development progresses.

Refer to the documentation in `docs/` for deeper guidance once authored.

## Developer CLI

Use the bundled `emperator` CLI to audit the scaffold, diagnose local environments, and run auto-remediation helpers:

```bash
# Preview the expected directory tree and TODO placeholders.
emperator scaffold audit

# Materialise missing directories/files defined in the Project Contract.
emperator scaffold ensure

# Run health checks against your workstation without making changes.
emperator doctor env

# List available remediation tasks and execute them (dry-run by default).
emperator fix plan
emperator fix run --apply
```

Pass `--root <path>` if you need to operate on a different checkout (the default is the current working directory).

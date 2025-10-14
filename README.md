# Emperator Monorepo

This repository contains the specification assets under `emperator_specs/` and the implementation scaffold under `emperator/`. The scaffold follows the canonical structure defined in `directory_structure.md` and is ready for application code, infrastructure, and contract artifacts.

## Getting Started

1. Run `./scripts/setup-tooling.sh` (or `pnpm run setup:tooling`) to create the `.venv/` virtual environment, install Python dev extras, fetch Node tooling, and wire up the shared lint hooks. Pass `--ci` when running in automation so the script avoids workspace writes.
2. Activate the virtual environment: `source .venv/bin/activate`.
3. Run the test suite: `pytest emperor/tests`.
4. Start the local API: `uvicorn emperator.api:app --reload`.
5. Populate the contract, source, and infrastructure directories with real assets as development progresses.

Refer to the documentation in `emperor/docs/` for deeper guidance once authored.

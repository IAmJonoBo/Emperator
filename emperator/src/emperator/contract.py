"""Helpers for working with the Emperator API contract artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONTRACT_FILENAME = 'platform.v1.yaml'
CONTRACT_RELATIVE_DIR = Path('contract') / 'api'
CONTRACT_REPOSITORY_PATH = CONTRACT_RELATIVE_DIR / CONTRACT_FILENAME


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_contract_path(relative: bool = False) -> Path:
    """Return the path to the canonical contract file.

    Parameters
    ----------
    relative:
        When True, return the path relative to the repository root. Otherwise return
        an absolute path.
    """
    if relative:
        return CONTRACT_REPOSITORY_PATH
    return _project_root() / CONTRACT_REPOSITORY_PATH


def load_contract_spec() -> dict[str, Any]:
    """Load the OpenAPI contract into a Python dictionary."""
    contract_path = get_contract_path()
    with contract_path.open(encoding='utf-8') as handle:
        return yaml.safe_load(handle)

"""Helpers for working with the Emperator API contract artifacts.

This module exposes utility functions for locating, loading, and interpreting the
canonical OpenAPI document that defines the Emperator runtime surface. The
implementation mirrors the guidance in ``docs/reference/contract-spec.md`` so
that application code can consume contract metadata in a type-safe way.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

yaml = cast(Any, importlib.import_module('yaml'))

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


@dataclass(frozen=True, slots=True)
class ContractInfo:
    """Lightweight view of the contract's :mod:`OpenAPI` metadata section."""

    title: str
    version: str
    summary: str | None
    contact_name: str | None
    contact_url: str | None
    license_name: str | None
    license_url: str | None
    source_path: str


@lru_cache(maxsize=1)
def load_contract_spec() -> Mapping[str, Any]:
    """Load the OpenAPI contract into an immutable mapping.

    The underlying YAML document is parsed once and cached for subsequent calls
    so that higher-level helpers such as :func:`get_contract_info` can reuse the
    data without repeatedly touching the filesystem.
    """
    contract_path = get_contract_path()
    with contract_path.open(encoding='utf-8') as handle:
        raw_spec = yaml.safe_load(handle)
    if not isinstance(raw_spec, dict):  # pragma: no cover - defensive guard
        msg = 'Contract specification must be a mapping at the document root.'
        raise ValueError(msg)
    return MappingProxyType(cast(dict[str, Any], raw_spec))


def _coerce_optional(value: Any) -> str | None:
    """Convert optional YAML scalars into optional strings."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def get_contract_info() -> ContractInfo:
    """Return normalized metadata extracted from the OpenAPI ``info`` section."""

    spec = load_contract_spec()
    info = spec.get('info')
    if not isinstance(info, Mapping):
        msg = 'Contract spec missing ``info`` section.'
        raise ValueError(msg)

    title = _coerce_optional(info.get('title'))
    version = _coerce_optional(info.get('version'))
    if title is None or version is None:
        msg = 'Contract info must define non-empty ``title`` and ``version``.'
        raise ValueError(msg)

    raw_contact = info.get('contact')
    contact = raw_contact if isinstance(raw_contact, Mapping) else {}

    raw_license = info.get('license')
    license_block = raw_license if isinstance(raw_license, Mapping) else {}

    return ContractInfo(
        title=title,
        version=version,
        summary=_coerce_optional(info.get('summary')),
        contact_name=_coerce_optional(contact.get('name')),
        contact_url=_coerce_optional(contact.get('url')),
        license_name=_coerce_optional(license_block.get('name')),
        license_url=_coerce_optional(license_block.get('url')),
        source_path=str(get_contract_path(relative=True).as_posix()),
    )

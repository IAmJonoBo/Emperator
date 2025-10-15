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
from typing import Any, TypeGuard, cast

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


@dataclass(frozen=True, slots=True)
class ContractValidationResult:
    """Structured response describing contract validation issues."""

    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Return ``True`` when no validation errors were recorded."""

        return not self.errors


def _is_mapping(value: Any) -> TypeGuard[Mapping[str, Any]]:
    return isinstance(value, Mapping)


def _check_contract_response_schema(responses: Mapping[str, Any], issues: list[str]) -> None:
    response = responses.get('200')
    if not _is_mapping(response):
        issues.append('`/contract` 200 response must be an object response.')
        return
    response_mapping = cast(Mapping[str, Any], response)
    content = response_mapping.get('content')
    if not _is_mapping(content):
        issues.append('`/contract` 200 response must define a JSON content block.')
        return
    content_mapping = cast(Mapping[str, Any], content)
    json_block = content_mapping.get('application/json')
    if not _is_mapping(json_block):
        issues.append('`/contract` 200 response must describe `application/json` content.')
        return
    json_mapping = cast(Mapping[str, Any], json_block)
    schema = json_mapping.get('schema')
    if not _is_mapping(schema):
        issues.append('`/contract` 200 response must include a schema definition.')
        return
    schema_mapping = cast(Mapping[str, Any], schema)
    properties = schema_mapping.get('properties')
    if not _is_mapping(properties):
        issues.append('`/contract` response schema must describe object properties.')
        return
    required = schema_mapping.get('required')
    required_set = set(required or ()) if isinstance(required, list) else set()
    for field in ('contractVersion', 'sourcePath'):
        if field not in properties:
            issues.append(f'`/contract` response must define the `{field}` property.')
        if field not in required_set:
            issues.append(f'`/contract` response must mark `{field}` as required.')


def _validate_openapi_version(
    spec: Mapping[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    version = spec.get('openapi')
    if not isinstance(version, str):
        errors.append('Contract must declare an OpenAPI version string under `openapi`.')
        return
    if not version.startswith('3.'):
        warnings.append(f'Contract targets OpenAPI 3.x; unexpected version detected ({version}).')


def _validate_info_section(spec: Mapping[str, Any], errors: list[str]) -> None:
    info = spec.get('info')
    if not _is_mapping(info):
        errors.append('Contract must define an `info` object with metadata.')
        return
    for field in ('title', 'version'):
        if _coerce_optional(info.get(field)) is None:
            errors.append(f'Contract info must set a non-empty `{field}` value.')


def _validate_servers(spec: Mapping[str, Any], warnings: list[str]) -> None:
    servers = spec.get('servers')
    if servers is None:
        warnings.append('Contract should declare at least one server entry.')
        return
    if not isinstance(servers, list) or not servers:
        warnings.append('Contract servers must be a non-empty list of server objects.')
        return
    for index, server in enumerate(servers):
        if not _is_mapping(server):
            warnings.append(f'Server entry #{index + 1} must be an object.')


def _validate_paths(spec: Mapping[str, Any], errors: list[str]) -> None:
    paths = spec.get('paths')
    if not _is_mapping(paths) or not paths:
        errors.append('Contract must include at least one path definition under `paths`.')
        return
    for path, path_item in paths.items():
        if not _is_mapping(path_item):
            errors.append(f'Path `{path}` must map HTTP verbs to operation objects.')
            continue
        path_mapping = cast(Mapping[str, Any], path_item)
        for verb, operation in path_mapping.items():
            if not _is_mapping(operation):
                errors.append(f'Operation `{verb}` under `{path}` must be an object.')
                continue
            operation_mapping = cast(Mapping[str, Any], operation)
            responses = operation_mapping.get('responses')
            if not _is_mapping(responses) or not responses:
                errors.append(f'Operation `{verb}` under `{path}` must define responses.')
                continue
            responses_mapping = cast(Mapping[str, Any], responses)
            if '200' not in responses_mapping:
                errors.append(f'Operation `{verb}` under `{path}` must define a 200 response.')
            if path == '/contract':
                _check_contract_response_schema(responses_mapping, errors)


def validate_contract_spec(strict: bool = False) -> ContractValidationResult:
    """Run structural validation against the canonical contract specification."""

    spec = load_contract_spec()
    errors: list[str] = []
    warnings: list[str] = []

    _validate_openapi_version(spec, errors, warnings)
    _validate_info_section(spec, errors)
    _validate_servers(spec, warnings)
    _validate_paths(spec, errors)

    if strict and warnings:
        errors.extend(f'[strict] {message}' for message in warnings)
        warnings = []

    return ContractValidationResult(errors=tuple(errors), warnings=tuple(warnings))

"""Unit tests for :mod:`emperator.contract`."""

from __future__ import annotations

from pathlib import Path

import pytest

import emperator.contract as contract_module
from emperator import ContractInfo, get_contract_info, get_contract_path, load_contract_spec


def test_get_contract_info_returns_expected_metadata() -> None:
    info = get_contract_info()
    assert isinstance(info, ContractInfo)
    assert info.title == 'Emperator Platform Contract'
    assert info.version == '0.1.0'
    assert info.source_path == str(get_contract_path(relative=True).as_posix())
    assert info.contact_name == 'Emperator Platform Team'
    assert info.license_name == 'Apache-2.0'


def test_load_contract_spec_is_cached_and_immutable() -> None:
    spec_first = load_contract_spec()
    spec_second = load_contract_spec()
    assert spec_first is spec_second

    with pytest.raises(TypeError):
        spec_first['info'] = {}  # type: ignore[index]


def _spec_path(tmp_path: Path, content: str) -> Path:
    path = tmp_path / 'contract.yaml'
    path.write_text(content, encoding='utf-8')
    return path


def _patch_contract_path(monkeypatch: pytest.MonkeyPatch, absolute: Path) -> None:
    def fake_get_contract_path(relative: bool = False) -> Path:
        if relative:
            return contract_module.CONTRACT_REPOSITORY_PATH
        return absolute

    monkeypatch.setattr(contract_module, 'get_contract_path', fake_get_contract_path)


def test_get_contract_info_handles_optional_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        'openapi: 3.1.0\ninfo:\n  title: Minimal\n  version: 1.0.0\n',
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    info = contract_module.get_contract_info()
    assert info.summary is None
    assert info.contact_name is None
    assert info.contact_url is None
    assert info.license_name is None
    assert info.license_url is None

    contract_module.load_contract_spec.cache_clear()


def test_get_contract_info_requires_title_and_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(tmp_path, 'openapi: 3.1.0\ninfo:\n  title: \n')
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    with pytest.raises(ValueError, match='title.*version'):
        contract_module.get_contract_info()

    contract_module.load_contract_spec.cache_clear()


def test_get_contract_info_requires_info_section(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(tmp_path, 'openapi: 3.1.0\n')
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    with pytest.raises(ValueError, match='info'):
        contract_module.get_contract_info()

    contract_module.load_contract_spec.cache_clear()

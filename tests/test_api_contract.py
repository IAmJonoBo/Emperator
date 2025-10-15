"""Validate the API runtime against the published contract artifact."""

from __future__ import annotations

from fastapi.testclient import TestClient

from emperator import (
    ContractInfo,
    __version__,
    create_app,
    get_contract_info,
    get_contract_path,
    load_contract_spec,
)


def test_contract_version_matches_package_version() -> None:
    spec = load_contract_spec()
    assert spec['info']['version'] == __version__


def test_healthz_endpoint_reports_ok() -> None:
    client = TestClient(create_app())
    response = client.get('/healthz')
    assert response.status_code == 200
    payload = response.json()
    assert payload == {'status': 'ok', 'version': __version__}


def test_contract_endpoint_reports_path_and_version() -> None:
    client = TestClient(create_app())
    response = client.get('/contract')
    assert response.status_code == 200
    payload = response.json()
    info: ContractInfo = get_contract_info()
    assert payload['contractVersion'] == info.version
    assert payload['sourcePath'] == info.source_path


def test_contract_file_exists_on_disk() -> None:
    contract_path = get_contract_path()
    assert contract_path.exists()
    assert contract_path.read_text(encoding='utf-8').strip().startswith('openapi: 3.1.0')

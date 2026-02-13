"""Unit tests for :mod:`emperator.contract`."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent, indent

import pytest

import emperator.contract as contract_module
from emperator import (
    ContractInfo,
    get_contract_info,
    get_contract_path,
    load_contract_spec,
)
from emperator.contract_rules import (
    ContractRule,
    ExemptionRecord,
    load_contract_rules,
    load_exemptions,
)


def test_get_contract_info_returns_expected_metadata() -> None:
    info = get_contract_info()
    assert isinstance(info, ContractInfo)
    assert info.title == "Emperator Platform Contract"
    assert info.version == "0.1.0"
    assert info.source_path == str(get_contract_path(relative=True).as_posix())
    assert info.contact_name == "Emperator Platform Team"
    assert info.license_name == "Apache-2.0"


def test_load_contract_spec_is_cached_and_immutable() -> None:
    spec_first = load_contract_spec()
    spec_second = load_contract_spec()
    assert spec_first is spec_second

    with pytest.raises(TypeError):
        spec_first["info"] = {}  # type: ignore[index]


def _spec_path(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "contract.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def _patch_contract_path(monkeypatch: pytest.MonkeyPatch, absolute: Path) -> None:
    def fake_get_contract_path(*, relative: bool = False) -> Path:
        if relative:
            return contract_module.CONTRACT_REPOSITORY_PATH
        return absolute

    monkeypatch.setattr(contract_module, "get_contract_path", fake_get_contract_path)


def test_get_contract_info_handles_optional_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\ninfo:\n  title: Minimal\n  version: 1.0.0\n",
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
    spec_path = _spec_path(tmp_path, "openapi: 3.1.0\ninfo:\n  title: \n")
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    with pytest.raises(ValueError, match="title.*version"):
        contract_module.get_contract_info()

    contract_module.load_contract_spec.cache_clear()


def test_get_contract_info_requires_info_section(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(tmp_path, "openapi: 3.1.0\n")
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    with pytest.raises(TypeError, match="info"):
        contract_module.get_contract_info()

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_reports_success() -> None:
    result = contract_module.validate_contract_spec()
    assert result.is_valid
    assert result.errors == ()


def test_validate_contract_spec_detects_missing_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\ninfo:\n  title: Minimal\n  version: 1.0.0\npaths: {}\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("paths" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_strict_escalates_warnings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Strict\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /healthz:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec(strict=True)
    assert not result.is_valid
    assert any(message.startswith("[strict]") for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_warns_on_version_and_servers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 2.0.0\n"
        "info:\n"
        "  title: Legacy\n"
        "  version: 1.0.0\n"
        "servers:\n"
        "  - https://legacy.example\n"
        "paths:\n"
        "  /healthz:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert result.is_valid
    assert any("unexpected version" in message for message in result.warnings)
    assert any("Server entry #1" in message for message in result.warnings)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_contract_endpoint_requirements(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Contract\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /contract:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
        "          content:\n"
        "            application/json:\n"
        "              schema:\n"
        "                type: object\n"
        "                properties:\n"
        "                  sourcePath:\n"
        "                    type: string\n"
        "                required:\n"
        "                  - sourcePath\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("contractVersion" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_requires_openapi(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "info:\n"
        "  title: Missing OpenAPI\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /healthz:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("OpenAPI version" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_requires_info_mapping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info: []\n"
        "paths:\n"
        "  /healthz:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("info" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_flags_non_mapping_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Invalid Path\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /broken: invalid\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("must map HTTP verbs" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_flags_non_mapping_operation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Invalid Operation\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /broken:\n"
        "    get: []\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("must be an object" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_requires_responses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Missing Responses\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /broken:\n"
        "    get:\n"
        "      summary: missing responses\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("must define responses" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_requires_200_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Missing 200\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /broken:\n"
        "    get:\n"
        "      responses:\n"
        "        '201':\n"
        "          description: created\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("must define a 200 response" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_contract_response_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Contract\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /contract:\n"
        "    get:\n"
        "      responses:\n"
        "        '200': broken\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("object response" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def _response_fixture(body: str) -> str:
    return indent(dedent(body).strip("\n"), "        ")


@pytest.mark.parametrize(
    ("response_block", "expected_fragment"),
    [
        (
            _response_fixture("""
                    '200':
                      description: ok
                """),
            "JSON content block",
        ),
        (
            _response_fixture("""
                    '200':
                      description: ok
                      content: {}
                """),
            "`application/json` content",
        ),
        (
            _response_fixture("""
                    '200':
                      description: ok
                      content:
                        application/json: {}
                """),
            "include a schema",
        ),
        (
            _response_fixture("""
                    '200':
                      description: ok
                      content:
                        application/json:
                          schema:
                            type: object
                """),
            "describe object properties",
        ),
    ],
)
def test_validate_contract_spec_contract_response_structure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    response_block: str,
    expected_fragment: str,
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: Contract\n"
        "  version: 1.0.0\n"
        "paths:\n"
        "  /contract:\n"
        "    get:\n"
        "      responses:\n"
        f"{response_block}",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any(expected_fragment in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_requires_info_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        '  title: ""\n'
        "  version: 1.0.0\n"
        "paths:\n"
        "  /healthz:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert not result.is_valid
    assert any("non-empty `title`" in message for message in result.errors)

    contract_module.load_contract_spec.cache_clear()


def test_validate_contract_spec_flags_empty_servers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    spec_path = _spec_path(
        tmp_path,
        "openapi: 3.1.0\n"
        "info:\n"
        "  title: No Servers\n"
        "  version: 1.0.0\n"
        "servers: []\n"
        "paths:\n"
        "  /healthz:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n",
    )
    _patch_contract_path(monkeypatch, spec_path)
    contract_module.load_contract_spec.cache_clear()

    result = contract_module.validate_contract_spec()
    assert result.is_valid
    assert any("non-empty list" in message for message in result.warnings)

    contract_module.load_contract_spec.cache_clear()


def test_load_contract_rules_supports_custom_catalog(tmp_path: Path) -> None:
    catalog = tmp_path / "rules.yaml"
    catalog.write_text(
        dedent("""
            rules:
              - id: sample.rule
                description: Example contract rule
                severity: medium
                source: contract/sample
                tags: [example, demo]
                remediation:
                  summary: Fix the issue.
                  steps:
                    - Step one
                  references:
                    - https://example.test
            """).strip(),
        encoding="utf8",
    )

    rules = load_contract_rules(catalog)
    assert isinstance(rules, tuple)
    assert len(rules) == 1
    rule = rules[0]
    assert isinstance(rule, ContractRule)
    assert rule.id == "sample.rule"
    assert rule.remediation is not None
    assert rule.remediation.references == ("https://example.test",)


def test_load_exemptions_accepts_optional_catalog(tmp_path: Path) -> None:
    exemptions = tmp_path / "exemptions.yaml"
    exemptions.write_text(
        dedent("""
            exemptions:
              - rule: sample.rule
                path: src/demo.py
                line: 12
                owner: demo
                justification: Temporary demo exemption
                expires: 2099-12-31
            """).strip(),
        encoding="utf8",
    )

    records = load_exemptions(exemptions)
    assert isinstance(records, tuple)
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, ExemptionRecord)
    assert record.rule_id == "sample.rule"
    assert record.path == Path("src/demo.py")
    assert record.expires is not None


def test_load_exemptions_returns_empty_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yaml"
    assert load_exemptions(missing) == ()


def test_load_contract_rules_uses_repository_catalog() -> None:
    rules = load_contract_rules()
    identifiers = {rule.id for rule in rules}
    assert "security.ban-eval" in identifiers
    assert "style.naming.pascal-case" in identifiers


def test_load_contract_rules_ignores_incomplete_entries(tmp_path: Path) -> None:
    catalog = tmp_path / "rules.yaml"
    catalog.write_text(
        dedent("""
            rules:
              - id: valid.rule
                description: Describes the rule
                severity: low
                source: contract/sample
                tags: compliance
              - id: missing-fields
                description: ''
                severity: low
                source: ''
            """).strip(),
        encoding="utf8",
    )

    rules = load_contract_rules(catalog)
    assert len(rules) == 1
    assert rules[0].id == "valid.rule"


def test_load_exemptions_handles_invalid_dates(tmp_path: Path) -> None:
    catalog = tmp_path / "exemptions.yaml"
    catalog.write_text(
        dedent("""
            exemptions:
              - rule: example
                path: src/example.py
                expires: not-a-date
            """).strip(),
        encoding="utf8",
    )

    records = load_exemptions(catalog)
    assert len(records) == 1
    assert records[0].expires is None


def test_load_contract_rules_handles_missing_metadata(tmp_path: Path) -> None:
    catalog = tmp_path / "rules.yaml"
    catalog.write_text(
        dedent("""
            rules:
              - 42
              - id: missing.tags
                description: Handles missing tags
                severity: medium
                source: contract/sample
                remediation:
                  summary: ''
                  steps: []
              - id: numeric.tags
                description: Tags stored as number
                severity: low
                source: contract/sample
                tags: 123
            """).strip(),
        encoding="utf8",
    )

    rules = load_contract_rules(catalog)
    assert len(rules) == 2
    first, second = rules
    assert first.tags == () and first.remediation is None
    assert second.tags == ()


def test_load_contract_rules_returns_empty_for_non_mapping(tmp_path: Path) -> None:
    catalog = tmp_path / "rules.yaml"
    catalog.write_text("[]", encoding="utf8")
    assert load_contract_rules(catalog) == ()


def test_load_exemptions_skips_non_mapping_entries(tmp_path: Path) -> None:
    catalog = tmp_path / "exemptions.yaml"
    catalog.write_text(
        dedent("""
            exemptions:
              - 42
              - rule: sample
                path: src/example.py
                expires: ''
              - rule: missing-path
                path: ''
            """).strip(),
        encoding="utf8",
    )

    records = load_exemptions(catalog)
    assert len(records) == 1
    assert records[0].expires is None

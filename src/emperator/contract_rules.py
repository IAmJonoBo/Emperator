"""Helpers for loading contract rule metadata and exemptions."""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

yaml = cast("Any", importlib.import_module("yaml"))

DEFAULT_RULE_CATALOG = Path("contract") / "rules" / "catalog.yaml"
DEFAULT_EXEMPTIONS_PATH = Path("contract") / "exemptions.yaml"


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RemediationGuidance:
    """Structured remediation metadata for a contract rule."""

    summary: str
    steps: tuple[str, ...]
    references: tuple[str, ...]


@dataclass(frozen=True)
class ContractRule:
    """Normalized rule metadata compiled from the project contract."""

    id: str
    description: str
    severity: str
    source: str
    tags: tuple[str, ...]
    auto_apply: bool | None = None
    safety_tier: str | None = None
    remediation: RemediationGuidance | None = None


@dataclass(frozen=True)
class ExemptionRecord:
    """Representation of an approved contract exemption."""

    rule_id: str
    path: Path
    line: int | None
    owner: str | None
    justification: str | None
    expires: date | None


def _normalize_sequence(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, Iterable):
        return tuple(str(item).strip() for item in raw if str(item).strip())
    return ()


def _load_yaml(path: Path) -> Mapping[str, Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf8") as handle:
        data = yaml.safe_load(handle)  # type: ignore[attr-defined]
    if not isinstance(data, Mapping):
        return None
    return data


def _parse_remediation(raw: Mapping[str, Any] | None) -> RemediationGuidance | None:
    if not raw:
        return None
    summary = str(raw.get("summary") or "").strip()
    if not summary:
        return None
    steps = _normalize_sequence(raw.get("steps"))
    references = _normalize_sequence(raw.get("references"))
    return RemediationGuidance(summary=summary, steps=steps, references=references)


def load_contract_rules(path: Path | None = None) -> tuple[ContractRule, ...]:
    """Load contract rules from the catalog YAML file.

    Parameters
    ----------
    path:
        Optional override path. When omitted, the default catalog under
        ``contract/rules/catalog.yaml`` is loaded.

    """
    catalog_path = path or DEFAULT_RULE_CATALOG
    resolved = (
        catalog_path
        if catalog_path.is_absolute()
        else _repository_root() / catalog_path
    )
    payload = _load_yaml(resolved)
    if payload is None:
        return ()

    rules: list[ContractRule] = []
    for entry in payload.get("rules", ()):  # type: ignore[arg-type]
        if not isinstance(entry, Mapping):
            continue
        rule_id = str(entry.get("id") or "").strip()
        description = str(entry.get("description") or "").strip()
        severity = str(entry.get("severity") or "").strip()
        source = str(entry.get("source") or "").strip()
        if not (rule_id and description and severity and source):
            continue
        remediation = _parse_remediation(entry.get("remediation"))  # type: ignore[arg-type]
        tags = _normalize_sequence(entry.get("tags"))
        auto_apply = entry.get("auto_apply")
        safety_tier = entry.get("safety_tier")
        rules.append(
            ContractRule(
                id=rule_id,
                description=description,
                severity=severity,
                source=source,
                tags=tags,
                auto_apply=bool(auto_apply) if isinstance(auto_apply, bool) else None,
                safety_tier=str(safety_tier).strip() if safety_tier else None,
                remediation=remediation,
            )
        )
    return tuple(rules)


def _parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def load_exemptions(path: Path | None = None) -> tuple[ExemptionRecord, ...]:
    """Load approved contract exemptions from YAML."""
    exemptions_path = path or DEFAULT_EXEMPTIONS_PATH
    resolved = (
        exemptions_path
        if exemptions_path.is_absolute()
        else _repository_root() / exemptions_path
    )
    payload = _load_yaml(resolved)
    if payload is None:
        return ()

    records: list[ExemptionRecord] = []
    for entry in payload.get("exemptions", ()):  # type: ignore[arg-type]
        if not isinstance(entry, Mapping):
            continue
        rule_id = str(entry.get("rule") or "").strip()
        path_text = str(entry.get("path") or "").strip()
        if not (rule_id and path_text):
            continue
        line = entry.get("line")
        line_number = int(line) if isinstance(line, int) else None
        owner = str(entry.get("owner") or "").strip() or None
        justification = str(entry.get("justification") or "").strip() or None
        expires = _parse_date(entry.get("expires"))
        records.append(
            ExemptionRecord(
                rule_id=rule_id,
                path=Path(path_text),
                line=line_number,
                owner=owner,
                justification=justification,
                expires=expires,
            )
        )
    return tuple(records)

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from emperator.analysis.correlation import (
    AnalysisFinding,
    CorrelatedFinding,
    CorrelationEngine,
    ExemptionStatus,
    FindingLocation,
)
from emperator.contract_rules import ContractRule, ExemptionRecord, RemediationGuidance


@pytest.fixture(name="sample_rules")
def fixture_sample_rules() -> tuple[ContractRule, ...]:
    return (
        ContractRule(
            id="security.ban-eval",
            description="Disallow eval usage for security hardening.",
            severity="high",
            source="contract/policy/security.rego#ban_eval",
            tags=("security", "injection"),
            remediation=RemediationGuidance(
                summary="Replace eval() with safer parsing helpers.",
                steps=(
                    "Use ast.literal_eval for trusted literals.",
                    "Prefer json.loads for JSON payloads.",
                ),
                references=("https://owasp.org/www-community/attacks/Code_Injection",),
            ),
        ),
        ContractRule(
            id="style.naming.pascal-case",
            description="Public classes must use PascalCase names.",
            severity="medium",
            source="contract/conventions/naming.cue#classes",
            tags=("style", "naming"),
            remediation=RemediationGuidance(
                summary="Rename classes to follow PascalCase.",
                steps=("Update class declarations and references.",),
                references=(),
            ),
        ),
        ContractRule(
            id="compliance.placeholder",
            description="Document temporary compliance placeholders.",
            severity="low",
            source="contract/policy/compliance.rego#placeholder",
            tags=("compliance",),
        ),
    )


@pytest.fixture(name="active_exemption")
def fixture_active_exemption() -> ExemptionRecord:
    return ExemptionRecord(
        rule_id="security.ban-eval",
        path=Path("src/legacy/util.py"),
        line=42,
        owner="platform",
        justification="Legacy parser awaiting refactor.",
        expires=datetime.now(tz=UTC).date() + timedelta(days=30),
    )


def test_correlate_matches_rule_id(sample_rules: tuple[ContractRule, ...]) -> None:
    finding = AnalysisFinding(
        tool="semgrep",
        rule_id="security.ban-eval",
        message="eval() usage found",
        severity="high",
        location=FindingLocation(
            path=Path("src/app.py"), start_line=10, start_column=4
        ),
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules)
    results = engine.correlate((finding,))

    assert len(results) == 1
    correlated = results[0]
    assert isinstance(correlated, CorrelatedFinding)
    assert correlated.contract_rule.id == "security.ban-eval"
    assert correlated.correlation_confidence == pytest.approx(1.0)
    assert correlated.remediation_guidance.summary.startswith("Replace eval")


def test_correlate_falls_back_to_tag_similarity(
    sample_rules: tuple[ContractRule, ...],
) -> None:
    finding = AnalysisFinding(
        tool="semgrep",
        rule_id=None,
        message="Class does not follow naming convention",
        severity="medium",
        location=FindingLocation(path=Path("src/models/order_class.py"), start_line=5),
        tags=("naming", "style"),
    )

    engine = CorrelationEngine(rules=sample_rules)
    results = engine.correlate((finding,))

    assert len(results) == 1
    correlated = results[0]
    assert correlated.contract_rule.id == "style.naming.pascal-case"
    assert 0 < correlated.correlation_confidence < 1
    assert correlated.correlation_confidence == pytest.approx(0.5)


def test_correlate_marks_active_exemptions(
    sample_rules: tuple[ContractRule, ...], active_exemption: ExemptionRecord
) -> None:
    finding = AnalysisFinding(
        tool="codeql",
        rule_id="security.ban-eval",
        message="eval usage inside legacy parser",
        severity="high",
        location=FindingLocation(path=Path("src/legacy/util.py"), start_line=42),
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules, exemptions=(active_exemption,))
    results = engine.correlate((finding,))

    assert len(results) == 1
    correlated = results[0]
    assert correlated.exemption_status is not None
    assert isinstance(correlated.exemption_status, ExemptionStatus)
    assert correlated.exemption_status.active is True
    assert "Legacy parser" in (correlated.exemption_status.reason or "")


def test_correlate_skips_unmatched_findings(
    sample_rules: tuple[ContractRule, ...],
) -> None:
    finding = AnalysisFinding(
        tool="semgrep",
        rule_id=None,
        message="No matching rule",
        severity="low",
        location=None,
        tags=(),
    )

    engine = CorrelationEngine(rules=sample_rules)
    assert engine.correlate((finding,)) == ()


def test_exemption_skips_when_location_missing(
    sample_rules: tuple[ContractRule, ...], active_exemption: ExemptionRecord
) -> None:
    finding = AnalysisFinding(
        tool="codeql",
        rule_id="security.ban-eval",
        message="eval usage without location",
        severity="high",
        location=None,
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules, exemptions=(active_exemption,))
    correlated = engine.correlate((finding,))[0]
    assert correlated.exemption_status is None


def test_exemption_requires_path_match(
    sample_rules: tuple[ContractRule, ...], active_exemption: ExemptionRecord
) -> None:
    finding = AnalysisFinding(
        tool="codeql",
        rule_id="security.ban-eval",
        message="eval usage in different file",
        severity="high",
        location=FindingLocation(path=Path("src/other.py"), start_line=42),
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules, exemptions=(active_exemption,))
    correlated = engine.correlate((finding,))[0]
    assert correlated.exemption_status is None


def test_exemption_skips_line_mismatch(sample_rules: tuple[ContractRule, ...]) -> None:
    exemption = ExemptionRecord(
        rule_id="security.ban-eval",
        path=Path("src/app.py"),
        line=99,
        owner="platform",
        justification="Different line",
        expires=datetime.now(tz=UTC).date() + timedelta(days=10),
    )
    finding = AnalysisFinding(
        tool="semgrep",
        rule_id="security.ban-eval",
        message="line mismatch",
        severity="high",
        location=FindingLocation(path=Path("src/app.py"), start_line=1),
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules, exemptions=(exemption,))
    correlated = engine.correlate((finding,))[0]
    assert correlated.exemption_status is None


def test_suggest_remediation_formats_output(
    sample_rules: tuple[ContractRule, ...],
) -> None:
    finding = AnalysisFinding(
        tool="semgrep",
        rule_id="security.ban-eval",
        message="eval() usage found",
        severity="high",
        location=FindingLocation(
            path=Path("src/app.py"), start_line=10, start_column=4
        ),
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules)
    correlated = engine.correlate((finding,))[0]
    summary = engine.suggest_remediation(correlated)

    assert "Replace eval() with safer parsing helpers." in summary
    assert "ast.literal_eval" in summary
    assert "json.loads" in summary
    assert "https://owasp.org" in summary


def test_suggest_remediation_uses_fallback(
    sample_rules: tuple[ContractRule, ...],
) -> None:
    finding = AnalysisFinding(
        tool="semgrep",
        rule_id="compliance.placeholder",
        message="Placeholder detected",
        severity="low",
        location=FindingLocation(path=Path("docs/todo.md")),
        tags=("compliance",),
    )

    engine = CorrelationEngine(rules=sample_rules)
    correlated = engine.correlate((finding,))[0]
    summary = engine.suggest_remediation(correlated)

    assert "contract rule compliance.placeholder" in summary
    assert "Document temporary compliance placeholders." in summary


def test_expired_exemption_reports_reason(
    sample_rules: tuple[ContractRule, ...],
) -> None:
    expired = ExemptionRecord(
        rule_id="security.ban-eval",
        path=Path("/opt/project/src/legacy/util.py"),
        line=42,
        owner="platform",
        justification="Awaiting removal",
        expires=datetime.now(tz=UTC).date() - timedelta(days=1),
    )
    finding = AnalysisFinding(
        tool="codeql",
        rule_id="security.ban-eval",
        message="legacy eval still present",
        severity="high",
        location=FindingLocation(
            path=Path("/opt/project/src/legacy/util.py"), start_line=42
        ),
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules, exemptions=(expired,))
    correlated = engine.correlate((finding,))[0]
    status = correlated.exemption_status
    assert status is not None and status.active is False
    assert "expired" in (status.reason or "").lower()


def test_exemption_without_expiry_is_active(
    sample_rules: tuple[ContractRule, ...],
) -> None:
    perpetual = ExemptionRecord(
        rule_id="security.ban-eval",
        path=Path("src/app.py"),
        line=None,
        owner=None,
        justification=None,
        expires=None,
    )
    finding = AnalysisFinding(
        tool="semgrep",
        rule_id="security.ban-eval",
        message="global waiver",
        severity="medium",
        location=FindingLocation(path=Path("src/app.py")),
        tags=("security",),
    )

    engine = CorrelationEngine(rules=sample_rules, exemptions=(perpetual,))
    correlated = engine.correlate((finding,))[0]
    assert correlated.exemption_status is not None
    assert correlated.exemption_status.active is True

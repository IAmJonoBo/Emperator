"""Correlate analyzer findings with contract metadata."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from emperator.contract_rules import ContractRule, ExemptionRecord, RemediationGuidance


@dataclass(frozen=True)
class FindingLocation:
    """Location metadata describing where a finding originated."""

    path: Path
    start_line: int | None = None
    start_column: int | None = None


@dataclass(frozen=True)
class AnalysisFinding:
    """Normalized representation of analyzer output."""

    tool: str
    rule_id: str | None
    message: str
    severity: str | None
    location: FindingLocation | None = None
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, str] | None = None


@dataclass(frozen=True)
class ExemptionStatus:
    """Outcome of evaluating an exemption against a correlated finding."""

    active: bool
    reason: str | None
    record: ExemptionRecord | None


@dataclass(frozen=True)
class CorrelatedFinding:
    """Finding linked to a contract rule and optional remediation guidance."""

    finding: AnalysisFinding
    contract_rule: ContractRule
    correlation_confidence: float
    remediation_guidance: RemediationGuidance | None
    exemption_status: ExemptionStatus | None


class CorrelationEngine:
    """Match analyzer findings to contract rules for traceability."""

    def __init__(
        self,
        *,
        rules: Sequence[ContractRule],
        exemptions: Sequence[ExemptionRecord] | None = None,
    ) -> None:
        self._rules = tuple(rules)
        self._rules_by_id = {rule.id: rule for rule in rules}
        self._exemptions = tuple(exemptions or ())
        grouped: dict[str, list[ExemptionRecord]] = {}
        for record in self._exemptions:
            grouped.setdefault(record.rule_id, []).append(record)
        self._exemptions_by_rule = {
            rule_id: tuple(records) for rule_id, records in grouped.items()
        }

    def correlate(
        self,
        findings: Sequence[AnalysisFinding],
    ) -> tuple[CorrelatedFinding, ...]:
        """Return correlated findings for the provided analyzer output."""
        correlated: list[CorrelatedFinding] = []
        for finding in findings:
            match, confidence = self._match_rule(finding)
            if match is None:
                continue
            guidance = match.remediation
            exemption = self._evaluate_exemption(finding, match)
            correlated.append(
                CorrelatedFinding(
                    finding=finding,
                    contract_rule=match,
                    correlation_confidence=round(confidence, 2),
                    remediation_guidance=guidance,
                    exemption_status=exemption,
                )
            )
        return tuple(correlated)

    def suggest_remediation(self, finding: CorrelatedFinding) -> str:
        """Format remediation guidance for developer presentation."""
        guidance = finding.remediation_guidance
        if guidance is None:
            return (
                f"Follow contract rule {finding.contract_rule.id}: "
                f"{finding.contract_rule.description}."
            )
        lines: list[str] = [guidance.summary]
        if guidance.steps:
            lines.append("Recommended steps:")
            lines.extend(f"- {step}" for step in guidance.steps)
        if guidance.references:
            lines.append("References:")
            lines.extend(f"- {reference}" for reference in guidance.references)
        return "\n".join(lines)

    def _match_rule(
        self, finding: AnalysisFinding
    ) -> tuple[ContractRule | None, float]:
        if finding.rule_id:
            direct = self._rules_by_id.get(finding.rule_id)
            if direct is not None:
                return direct, 1.0
        best_rule: ContractRule | None = None
        best_score = 0.0
        for rule in self._rules:
            score = self._tag_similarity(finding.tags, rule.tags)
            if score > best_score:
                best_rule = rule
                best_score = score
        if best_rule is None or best_score == 0.0:
            return None, 0.0
        return best_rule, best_score

    @staticmethod
    def _tag_similarity(finding_tags: Iterable[str], rule_tags: Iterable[str]) -> float:
        finding_set = {tag.lower() for tag in finding_tags if tag}
        rule_set = {tag.lower() for tag in rule_tags if tag}
        if not finding_set or not rule_set:
            return 0.0
        overlap = finding_set.intersection(rule_set)
        if not overlap:
            return 0.0
        ratio = len(overlap) / len(rule_set)
        return max(min(ratio * 0.5, 0.5), 0.0)

    def _evaluate_exemption(
        self, finding: AnalysisFinding, rule: ContractRule
    ) -> ExemptionStatus | None:
        location = finding.location
        if location is None:
            return None
        candidates = self._exemptions_by_rule.get(rule.id, ())
        if not candidates:
            return None
        for record in candidates:
            if not self._paths_match(location.path, record.path):
                continue
            if (
                record.line is not None
                and location.start_line is not None
                and record.line != location.start_line
            ):
                continue
            active = self._is_active(record.expires)
            if active:
                reason = (
                    record.justification or "Active exemption recorded in contract."
                )
            else:
                expiry_text = (
                    record.expires.isoformat() if record.expires else "unknown date"
                )
                reason = f"Exemption expired on {expiry_text}"
            return ExemptionStatus(active=active, reason=reason, record=record)
        return None

    @staticmethod
    def _paths_match(candidate: Path, expected: Path) -> bool:
        candidate_normalized = Path(str(candidate)).as_posix().lstrip("./")
        expected_normalized = Path(str(expected)).as_posix().lstrip("./")
        if candidate_normalized == expected_normalized:
            return True
        return candidate_normalized.endswith(f"/{expected_normalized}")

    @staticmethod
    def _is_active(expiry: date | None) -> bool:
        if expiry is None:
            return True
        return expiry >= datetime.now(tz=UTC).date()

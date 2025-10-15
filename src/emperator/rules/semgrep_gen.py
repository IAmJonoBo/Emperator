"""Semgrep rule generation from contract conventions and policies."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Severity(Enum):
    """Severity levels for rules."""

    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


@dataclass
class SemgrepRule:
    """Semgrep YAML rule definition."""

    id: str
    message: str
    severity: Severity
    pattern: str | dict[str, Any]
    languages: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Semgrep YAML format.

        Returns:
            Dictionary representation for YAML serialization

        """
        rule_dict: dict[str, Any] = {
            'id': self.id,
            'message': self.message,
            'severity': self.severity.value,
            'languages': list(self.languages),
            'metadata': self.metadata,
        }

        # Add pattern (can be string or dict for complex patterns)
        if isinstance(self.pattern, str):
            rule_dict['pattern'] = self.pattern
        else:
            rule_dict.update(self.pattern)

        # Add fix if provided
        if self.fix:
            rule_dict['fix'] = self.fix

        return rule_dict


class SemgrepRuleGenerator:
    """Compile contract conventions into Semgrep rules."""

    def __init__(self) -> None:
        """Initialize the rule generator."""
        self.rules: list[SemgrepRule] = []

    def generate_naming_rules(self) -> tuple[SemgrepRule, ...]:
        """Generate naming convention rules.

        Returns:
            Tuple of Semgrep rules for naming conventions

        """
        rules = []

        # Python function naming (snake_case)
        rules.append(
            SemgrepRule(
                id='naming-function-snake-case',
                message='Function names should use snake_case',
                severity=Severity.WARNING,
                pattern={
                    'pattern': 'def $FUNC(...): ...',
                    'pattern-not-regex': r'def [a-z_][a-z0-9_]*\(',
                },
                languages=('python',),
                metadata={
                    'category': 'naming',
                    'source': 'contract/conventions.cue#naming.functions',
                },
            )
        )

        # Python class naming (PascalCase)
        rules.append(
            SemgrepRule(
                id='naming-class-pascal-case',
                message='Class names should use PascalCase',
                severity=Severity.WARNING,
                pattern={
                    'pattern': 'class $CLASS: ...',
                    'pattern-not-regex': r'class [A-Z][a-zA-Z0-9]*:',
                },
                languages=('python',),
                metadata={
                    'category': 'naming',
                    'source': 'contract/conventions.cue#naming.classes',
                },
            )
        )

        return tuple(rules)

    def generate_security_rules(self) -> tuple[SemgrepRule, ...]:
        """Generate security rules from policies.

        Returns:
            Tuple of Semgrep rules for security checks

        """
        rules = []

        # Ban eval() usage
        rules.append(
            SemgrepRule(
                id='security-ban-eval',
                message=(
                    'Use of eval() is forbidden. ' 'Use ast.literal_eval() or json.loads() instead.'
                ),
                severity=Severity.ERROR,
                pattern='eval(...)',
                languages=('python',),
                metadata={
                    'category': 'security',
                    'source': 'contract/policy/security.rego',
                    'cwe': 'CWE-95',
                    'owasp': 'A03:2021',
                },
                fix='ast.literal_eval(...)',
            )
        )

        # Ban exec() usage
        rules.append(
            SemgrepRule(
                id='security-ban-exec',
                message='Use of exec() is forbidden. Refactor to avoid dynamic code execution.',
                severity=Severity.ERROR,
                pattern='exec(...)',
                languages=('python',),
                metadata={
                    'category': 'security',
                    'source': 'contract/policy/security.rego',
                    'cwe': 'CWE-95',
                    'owasp': 'A03:2021',
                },
            )
        )

        # SQL injection detection
        rules.append(
            SemgrepRule(
                id='security-sql-injection',
                message='Potential SQL injection. Use parameterized queries instead.',
                severity=Severity.ERROR,
                pattern={
                    'pattern-either': [
                        {'pattern': 'cursor.execute(f"...", ...)'},
                        {'pattern': 'cursor.execute("..." + $X, ...)'},
                        {'pattern': 'cursor.execute("..." % ...)'},
                    ]
                },
                languages=('python',),
                metadata={
                    'category': 'security',
                    'source': 'contract/policy/security.rego',
                    'cwe': 'CWE-89',
                    'owasp': 'A03:2021',
                },
            )
        )

        # Hardcoded secrets
        rules.append(
            SemgrepRule(
                id='security-hardcoded-secret',
                message=(
                    'Potential hardcoded secret. ' 'Use environment variables or secret management.'
                ),
                severity=Severity.ERROR,
                pattern={
                    'pattern-regex': r'(password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
                },
                languages=('python',),
                metadata={
                    'category': 'security',
                    'source': 'contract/policy/security.rego',
                    'cwe': 'CWE-798',
                },
            )
        )

        return tuple(rules)

    def generate_architectural_rules(self) -> tuple[SemgrepRule, ...]:
        """Generate architectural constraint rules.

        Returns:
            Tuple of Semgrep rules for architecture enforcement

        """
        rules = []

        # Prevent circular imports
        rules.append(
            SemgrepRule(
                id='architecture-no-circular-import',
                message='Potential circular import detected',
                severity=Severity.WARNING,
                pattern={
                    'pattern': 'import $MODULE',
                    'metavariable-regex': {
                        'metavariable': '$MODULE',
                        'regex': r'emperator\.(.*)',
                    },
                },
                languages=('python',),
                metadata={
                    'category': 'architecture',
                    'source': 'contract/policy/architecture.rego',
                },
            )
        )

        return tuple(rules)

    def generate_all_rules(self) -> tuple[SemgrepRule, ...]:
        """Generate all rules from contracts.

        Returns:
            Tuple of all generated Semgrep rules

        """
        all_rules = []
        all_rules.extend(self.generate_naming_rules())
        all_rules.extend(self.generate_security_rules())
        all_rules.extend(self.generate_architectural_rules())
        return tuple(all_rules)

    def write_rule_pack(self, rules: tuple[SemgrepRule, ...], output: Path) -> None:
        """Serialize rules to Semgrep YAML format.

        Args:
            rules: Tuple of Semgrep rules to write
            output: Output file path for the rule pack

        """
        output.parent.mkdir(parents=True, exist_ok=True)

        rule_pack = {'rules': [rule.to_dict() for rule in rules]}

        with output.open('w') as f:
            yaml.dump(rule_pack, f, default_flow_style=False, sort_keys=False)

    def write_category_packs(
        self,
        rules: tuple[SemgrepRule, ...],
        output_dir: Path,
    ) -> dict[str, Path]:
        """Write rules organized by category.

        Args:
            rules: Tuple of Semgrep rules
            output_dir: Output directory for rule packs

        Returns:
            Dictionary mapping category names to output file paths

        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Group rules by category
        by_category: dict[str, list[SemgrepRule]] = {}
        for rule in rules:
            category = rule.metadata.get('category', 'general')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(rule)

        # Write each category pack
        written = {}
        for category, category_rules in by_category.items():
            output_file = output_dir / f'{category}.yaml'
            self.write_rule_pack(tuple(category_rules), output_file)
            written[category] = output_file

        return written

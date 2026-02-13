"""Tests for Semgrep rule generation."""

from pathlib import Path

import yaml

from emperator.rules import SemgrepRule, SemgrepRuleGenerator, Severity


def test_semgrep_rule_creation() -> None:
    """Test creating a Semgrep rule."""
    rule = SemgrepRule(
        id="test-rule",
        message="Test message",
        severity=Severity.WARNING,
        pattern="test_pattern",
        languages=("python",),
    )

    assert rule.id == "test-rule"
    assert rule.message == "Test message"
    assert rule.severity == Severity.WARNING
    assert rule.pattern == "test_pattern"
    assert rule.languages == ("python",)


def test_semgrep_rule_to_dict_simple_pattern() -> None:
    """Test converting rule to dict with simple pattern."""
    rule = SemgrepRule(
        id="test-rule",
        message="Test message",
        severity=Severity.ERROR,
        pattern="eval(...)",
        languages=("python",),
    )

    rule_dict = rule.to_dict()

    assert rule_dict["id"] == "test-rule"
    assert rule_dict["message"] == "Test message"
    assert rule_dict["severity"] == "ERROR"
    assert rule_dict["pattern"] == "eval(...)"
    assert rule_dict["languages"] == ["python"]


def test_semgrep_rule_to_dict_complex_pattern() -> None:
    """Test converting rule to dict with complex pattern."""
    rule = SemgrepRule(
        id="test-rule",
        message="Test message",
        severity=Severity.WARNING,
        pattern={
            "pattern-either": [
                {"pattern": "eval(...)"},
                {"pattern": "exec(...)"},
            ]
        },
        languages=("python",),
    )

    rule_dict = rule.to_dict()

    assert "pattern-either" in rule_dict
    assert len(rule_dict["pattern-either"]) == 2


def test_semgrep_rule_with_fix() -> None:
    """Test rule with fix suggestion."""
    rule = SemgrepRule(
        id="test-rule",
        message="Use better function",
        severity=Severity.INFO,
        pattern="old_func(...)",
        languages=("python",),
        fix="new_func(...)",
    )

    rule_dict = rule.to_dict()
    assert rule_dict["fix"] == "new_func(...)"


def test_generator_naming_rules() -> None:
    """Test generating naming convention rules."""
    generator = SemgrepRuleGenerator()
    rules = generator.generate_naming_rules()

    assert len(rules) > 0
    assert any(r.id == "naming-function-snake-case" for r in rules)
    assert any(r.id == "naming-class-pascal-case" for r in rules)

    # Check function naming rule
    func_rule = next(r for r in rules if r.id == "naming-function-snake-case")
    assert func_rule.severity == Severity.WARNING
    assert "python" in func_rule.languages
    assert func_rule.metadata["category"] == "naming"


def test_generator_security_rules() -> None:
    """Test generating security rules."""
    generator = SemgrepRuleGenerator()
    rules = generator.generate_security_rules()

    assert len(rules) > 0
    assert any(r.id == "security-ban-eval" for r in rules)
    assert any(r.id == "security-ban-exec" for r in rules)
    assert any(r.id == "security-sql-injection" for r in rules)
    assert any(r.id == "security-hardcoded-secret" for r in rules)

    # Check eval ban rule
    eval_rule = next(r for r in rules if r.id == "security-ban-eval")
    assert eval_rule.severity == Severity.ERROR
    assert "python" in eval_rule.languages
    assert eval_rule.metadata["category"] == "security"
    assert "cwe" in eval_rule.metadata


def test_generator_architectural_rules() -> None:
    """Test generating architectural rules."""
    generator = SemgrepRuleGenerator()
    rules = generator.generate_architectural_rules()

    assert len(rules) > 0
    assert any(r.id == "architecture-no-circular-import" for r in rules)

    # Check circular import rule
    circ_rule = next(r for r in rules if r.id == "architecture-no-circular-import")
    assert circ_rule.severity == Severity.WARNING
    assert "python" in circ_rule.languages
    assert circ_rule.metadata["category"] == "architecture"


def test_generator_all_rules() -> None:
    """Test generating all rules."""
    generator = SemgrepRuleGenerator()
    all_rules = generator.generate_all_rules()

    # Should have rules from all categories
    categories = {r.metadata.get("category") for r in all_rules}
    assert "naming" in categories
    assert "security" in categories
    assert "architecture" in categories

    # Check total count
    assert len(all_rules) >= 7  # At least 7 rules across all categories


def test_write_rule_pack(tmp_path: Path) -> None:
    """Test writing rules to YAML file."""
    generator = SemgrepRuleGenerator()
    rules = generator.generate_security_rules()

    output_file = tmp_path / "security-rules.yaml"
    generator.write_rule_pack(rules, output_file)

    assert output_file.exists()

    # Validate YAML structure
    with output_file.open() as f:
        data = yaml.safe_load(f)

    assert "rules" in data
    assert len(data["rules"]) == len(rules)

    # Check first rule structure
    first_rule = data["rules"][0]
    assert "id" in first_rule
    assert "message" in first_rule
    assert "severity" in first_rule
    assert "languages" in first_rule


def test_write_category_packs(tmp_path: Path) -> None:
    """Test writing rules organized by category."""
    generator = SemgrepRuleGenerator()
    all_rules = generator.generate_all_rules()

    output_dir = tmp_path / "rules"
    written = generator.write_category_packs(all_rules, output_dir)

    # Should have written multiple categories
    assert len(written) >= 3
    assert "naming" in written
    assert "security" in written
    assert "architecture" in written

    # Check each category file exists and is valid
    for category, path in written.items():
        assert path.exists()
        assert path.parent == output_dir

        with path.open() as f:
            data = yaml.safe_load(f)
            assert "rules" in data
            # All rules should be from the same category
            for rule in data["rules"]:
                assert rule["metadata"]["category"] == category


def test_rule_pack_parent_directory_creation(tmp_path: Path) -> None:
    """Test that parent directories are created when writing rules."""
    generator = SemgrepRuleGenerator()
    rules = (
        SemgrepRule(
            id="test-rule",
            message="Test",
            severity=Severity.INFO,
            pattern="test",
            languages=("python",),
        ),
    )

    # Create nested path that doesn't exist
    output_file = tmp_path / "a" / "b" / "c" / "rules.yaml"
    generator.write_rule_pack(rules, output_file)

    assert output_file.exists()
    assert output_file.parent.exists()


def test_severity_enum() -> None:
    """Test severity enum values."""
    assert Severity.INFO.value == "INFO"
    assert Severity.WARNING.value == "WARNING"
    assert Severity.ERROR.value == "ERROR"


def test_rule_metadata() -> None:
    """Test rule metadata handling."""
    metadata = {
        "category": "security",
        "source": "contract/policy/security.rego",
        "cwe": "CWE-95",
        "owasp": "A03:2021",
    }

    rule = SemgrepRule(
        id="test-rule",
        message="Test",
        severity=Severity.ERROR,
        pattern="test",
        languages=("python",),
        metadata=metadata,
    )

    rule_dict = rule.to_dict()
    assert rule_dict["metadata"] == metadata


def test_multiple_languages() -> None:
    """Test rule with multiple target languages."""
    rule = SemgrepRule(
        id="test-rule",
        message="Test",
        severity=Severity.WARNING,
        pattern="console.log(...)",
        languages=("javascript", "typescript"),
    )

    rule_dict = rule.to_dict()
    assert "javascript" in rule_dict["languages"]
    assert "typescript" in rule_dict["languages"]

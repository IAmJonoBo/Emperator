"""Integration tests for the developer CLI."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

try:
    from emperator import cli as cli_module
    from emperator.analysis import (
        AnalysisHint,
        AnalysisReport,
        AnalyzerCommand,
        AnalyzerPlan,
        CodeQLDatabase,
        CodeQLFinding,
        CodeQLManagerError,
        CodeQLUnavailableError,
        JSONLTelemetryStore,
        TelemetryEvent,
        TelemetryRun,
        fingerprint_analysis,
    )
    from emperator.cli import app
    from emperator.contract import ContractValidationResult
    from emperator.doctor import RemediationAction
except ModuleNotFoundError:  # pragma: no cover - allow running tests without install
    sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
    from emperator import cli as cli_module
    from emperator.analysis import (
        AnalysisHint,
        AnalysisReport,
        AnalyzerCommand,
        AnalyzerPlan,
        CodeQLDatabase,
        CodeQLFinding,
        CodeQLManagerError,
        CodeQLUnavailableError,
        JSONLTelemetryStore,
        TelemetryEvent,
        TelemetryRun,
        fingerprint_analysis,
    )
    from emperator.cli import app
    from emperator.contract import ContractValidationResult
    from emperator.doctor import RemediationAction

runner = CliRunner()


def test_cli_scaffold_ensure_creates_structure(tmp_path: Path) -> None:
    """Scaffold ensure should create the expected policy file."""
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "scaffold", "ensure"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    policy_path = tmp_path / "contract" / "policy" / "policy.rego"
    assert policy_path.exists()
    assert "TODO" in policy_path.read_text(encoding="utf-8")


def test_cli_scaffold_audit_reports_missing(tmp_path: Path) -> None:
    """Scaffold audit should report missing assets."""
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "scaffold", "audit"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "policy.rego" in result.stdout


def test_cli_scaffold_ensure_dry_run(tmp_path: Path) -> None:
    """Dry-run ensure should not write to disk."""
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "scaffold", "ensure", "--dry-run"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Dry run complete" in result.stdout
    assert not (tmp_path / "contract").exists()


def test_cli_doctor_env_reports_status(tmp_path: Path) -> None:
    """Doctor env should report bootstrap status."""
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "doctor", "env"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Environment Checks" in result.stdout
    assert "Tooling bootstrap" in result.stdout


def test_cli_contract_validate_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract validate should report success and surface warnings."""
    monkeypatch.setattr(
        cli_module,
        "validate_contract_spec",
        lambda strict=False: ContractValidationResult(
            errors=(), warnings=("Missing server",)
        ),
    )
    result = runner.invoke(app, ["contract", "validate"], env={"NO_COLOR": "1"})
    assert result.exit_code == 0, result.stdout
    assert "Contract validation passed" in result.stdout
    assert "Missing server" in result.stdout


def test_cli_contract_validate_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract validate should print errors and exit with status 1."""

    def fake(strict: bool = False) -> ContractValidationResult:
        del strict
        return ContractValidationResult(
            errors=("Missing openapi",), warnings=("Missing server",)
        )

    monkeypatch.setattr(cli_module, "validate_contract_spec", fake)
    result = runner.invoke(app, ["contract", "validate"], env={"NO_COLOR": "1"})
    assert result.exit_code == 1
    assert "Missing openapi" in result.stdout
    assert "Missing server" in result.stdout


def test_cli_contract_validate_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strict mode should forward the flag and hide warnings."""
    calls: list[bool] = []

    def fake(strict: bool = False) -> ContractValidationResult:
        calls.append(strict)
        return ContractValidationResult(errors=("Strict failure",), warnings=())

    monkeypatch.setattr(cli_module, "validate_contract_spec", fake)
    result = runner.invoke(
        app, ["contract", "validate", "--strict"], env={"NO_COLOR": "1"}
    )
    assert result.exit_code == 1
    assert calls == [True]
    assert "Strict failure" in result.stdout
    assert "Missing server" not in result.stdout


def test_cli_fix_plan_lists_actions() -> None:
    """Fix plan should list available remediation actions."""
    result = runner.invoke(app, ["fix", "plan"], env={"NO_COLOR": "1"})
    assert result.exit_code == 0, result.stdout
    assert "Auto-remediation Plan" in result.stdout
    assert "Sync Python tooling" in result.stdout


def test_cli_doctor_env_apply_runs_remediations(monkeypatch, tmp_path: Path) -> None:
    """Doctor env apply should execute remediation actions."""
    actions = (RemediationAction("Sample", ("echo", "sample"), "desc"),)
    executed: list[tuple[RemediationAction, bool, Path | None]] = []

    monkeypatch.setattr(cli_module, "iter_actions", lambda: actions)

    def fake_run(
        action: RemediationAction, dry_run: bool = True, cwd: Path | None = None
    ):
        executed.append((action, dry_run, cwd))
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(cli_module, "run_remediation", fake_run)
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "doctor", "env", "--apply"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert executed and executed[0][1] is False


def test_cli_doctor_env_apply_handles_failure(monkeypatch, tmp_path: Path) -> None:
    """Doctor env apply should surface remediation failures."""
    action = RemediationAction("Fail", ("echo", "fail"), "desc")
    monkeypatch.setattr(cli_module, "iter_actions", lambda: (action,))

    def fake_run(
        action: RemediationAction, dry_run: bool = True, cwd: Path | None = None
    ):
        del action, dry_run, cwd
        return SimpleNamespace(returncode=1, stderr="boom")

    monkeypatch.setattr(cli_module, "run_remediation", fake_run)
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "doctor", "env", "--apply"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "exited with code 1" in result.stdout
    assert "boom" in result.stdout


def test_cli_fix_run_handles_filters(monkeypatch, tmp_path: Path) -> None:
    """Fix run should respect the --only filter when applying."""
    actions = (
        RemediationAction("A", ("echo", "a"), "desc"),
        RemediationAction("B", ("echo", "b"), "desc"),
    )
    outputs: list[str] = []

    monkeypatch.setattr(cli_module, "iter_actions", lambda: actions)

    def fake_run(
        action: RemediationAction, dry_run: bool = True, cwd: Path | None = None
    ):
        del dry_run, cwd
        outputs.append(action.name)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(cli_module, "run_remediation", fake_run)
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "fix", "run", "--only", "B", "--apply"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert outputs == ["B"]


def test_cli_fix_run_reports_no_match(monkeypatch, tmp_path: Path) -> None:
    """Fix run should report when no actions match filters."""
    monkeypatch.setattr(cli_module, "iter_actions", lambda: ())
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "fix", "run", "--only", "missing"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "No remediation actions matched" in result.stdout


def test_cli_fix_run_handles_failure(monkeypatch, tmp_path: Path) -> None:
    """Fix run should report remediation command failures."""
    action = RemediationAction("Broken", ("echo", "broken"), "desc")
    monkeypatch.setattr(cli_module, "iter_actions", lambda: (action,))

    def fake_run(
        action: RemediationAction, dry_run: bool = True, cwd: Path | None = None
    ):
        del action, dry_run, cwd
        return SimpleNamespace(returncode=2, stderr="fail whale")

    monkeypatch.setattr(cli_module, "run_remediation", fake_run)
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "fix", "run", "--apply"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "exited with 2" in result.stdout
    assert "fail whale" in result.stdout


def test_cli_fix_run_dry_run_message(monkeypatch, tmp_path: Path) -> None:
    """Fix run dry-run should explain no commands were executed."""
    action = RemediationAction("Dry", ("echo", "dry"), "desc")
    monkeypatch.setattr(cli_module, "iter_actions", lambda: (action,))

    def fake_run(
        action: RemediationAction, dry_run: bool = True, cwd: Path | None = None
    ):
        del action, dry_run, cwd
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(cli_module, "run_remediation", fake_run)
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "fix", "run"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Dry run complete" in result.stdout


def test_cli_analysis_inspect_renders_report(monkeypatch, tmp_path: Path) -> None:
    """Analysis inspect should render language and tooling information."""
    from emperator.analysis import LanguageSummary, ToolStatus

    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=2, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="CodeQL",
                available=False,
                location=None,
                hint="Install CodeQL CLI",
            ),
        ),
        hints=(
            AnalysisHint(
                topic="CodeQL",
                guidance="Install CodeQL CLI to enable semantic checks.",
            ),
        ),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "inspect"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Analysis Overview" in result.stdout
    assert "Python" in result.stdout
    assert "CodeQL" in result.stdout
    assert "Install CodeQL CLI" in result.stdout


def test_cli_analysis_inspect_handles_empty_languages(
    monkeypatch, tmp_path: Path
) -> None:
    """Analysis inspect should fall back gracefully when nothing is detected."""
    from emperator.analysis import ToolStatus

    report = AnalysisReport(
        languages=(),
        tool_statuses=(
            ToolStatus(
                name="Semgrep", available=False, location=None, hint="Install Semgrep"
            ),
        ),
        hints=(AnalysisHint(topic="Sources", guidance="Add code."),),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "inspect"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "No supported languages detected" in result.stdout
    assert "Hints" in result.stdout


def test_cli_analysis_wizard_surfaces_hints(monkeypatch, tmp_path: Path) -> None:
    """Analysis wizard should surface actionable hints for missing tooling."""
    from emperator.analysis import ToolStatus

    report = AnalysisReport(
        languages=(),
        tool_statuses=(
            ToolStatus(
                name="Semgrep",
                available=False,
                location=None,
                hint="Install Semgrep",
            ),
            ToolStatus(
                name="CodeQL",
                available=True,
                location="/opt/codeql",
                hint="Available at /opt/codeql",
            ),
        ),
        hints=(
            AnalysisHint(
                topic="Semgrep",
                guidance="Install Semgrep for contract-driven scans.",
            ),
        ),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "wizard"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Interactive Analysis Wizard" in result.stdout
    assert "Semgrep" in result.stdout
    assert "Install Semgrep" in result.stdout


def test_cli_analysis_wizard_reports_languages(monkeypatch, tmp_path: Path) -> None:
    """Analysis wizard should celebrate detected languages."""
    from emperator.analysis import LanguageSummary, ToolStatus

    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=2, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="Tree-sitter CLI",
                available=True,
                location="/usr/bin/tree-sitter",
                hint="Available at /usr/bin/tree-sitter",
            ),
        ),
        hints=(),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "wizard"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Review detected languages" in result.stdout
    assert "Python" in result.stdout


def test_cli_analysis_plan_renders_steps(monkeypatch, tmp_path: Path) -> None:
    """Analysis plan should display execution steps for analyzers."""
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plans = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Semgrep ready",
            steps=(
                AnalyzerCommand(
                    command=(
                        "semgrep",
                        "scan",
                        "--config=auto",
                        "--metrics=off",
                        str(tmp_path),
                    ),
                    description="Run Semgrep with the auto configuration.",
                ),
            ),
        ),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: plans)
    monkeypatch.setattr(
        cli_module,
        "fingerprint_analysis",
        lambda report, plans, metadata=None: "demo-fingerprint",
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "plan"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Analysis Execution Plan" in result.stdout
    assert "Semgrep" in result.stdout
    # Command parts may be wrapped across lines, check individually
    assert "semgrep" in result.stdout
    assert "scan" in result.stdout
    assert "--config=auto" in result.stdout
    assert "--metrics=off" in result.stdout
    assert "Telemetry fingerprint" in result.stdout
    assert "demo-fingerprint" in result.stdout
    assert "No telemetry recorded for this plan yet." in result.stdout


def test_cli_analysis_plan_handles_empty_steps(monkeypatch, tmp_path: Path) -> None:
    """Plan rendering should handle analyzers without explicit steps."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plans = (
        AnalyzerPlan(
            tool="CodeQL",
            ready=False,
            reason="No CodeQL-supported languages detected.",
            steps=(),
        ),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: plans)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "plan"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "No CodeQL-supported languages" in result.stdout


def test_cli_analysis_plan_handles_no_plans(monkeypatch, tmp_path: Path) -> None:
    """Plan command should explain when no analyzers are configured."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: ())

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "plan"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "No analyzer plans available yet" in result.stdout


def test_cli_analysis_plan_reports_cached_telemetry(
    monkeypatch, tmp_path: Path
) -> None:
    """Telemetry banner should surface details about the most recent run."""
    store_path = tmp_path / "telemetry"
    store = JSONLTelemetryStore(store_path, max_history=5)
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plans = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(
                AnalyzerCommand(
                    command=(
                        "semgrep",
                        "scan",
                        "--config=auto",
                        "--metrics=off",
                        str(tmp_path),
                    ),
                    description="Run Semgrep with auto config.",
                ),
            ),
        ),
    )
    fingerprint = fingerprint_analysis(report, plans)
    start = datetime.now(UTC)
    event = TelemetryEvent(
        tool="Semgrep",
        command=plans[0].steps[0].command,
        exit_code=0,
        duration_seconds=3.2,
        timestamp=start,
        metadata={"config": "auto"},
    )
    run = TelemetryRun(
        fingerprint=fingerprint,
        project_root=tmp_path,
        started_at=start,
        completed_at=start + timedelta(seconds=3),
        events=(event,),
        notes=("cached",),
    )
    store.persist(run)

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: plans)
    monkeypatch.setattr(
        cli_module,
        "fingerprint_analysis",
        lambda report, plans, metadata=None: fingerprint,
    )

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--telemetry-store",
            "jsonl",
            "--telemetry-path",
            str(store_path),
            "analysis",
            "plan",
        ],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Telemetry fingerprint" in result.stdout
    assert str(run.completed_at.isoformat()) in result.stdout
    assert "success" in result.stdout.lower()


def test_cli_analysis_plan_disables_telemetry(monkeypatch, tmp_path: Path) -> None:
    """CLI should respect the --telemetry-store off flag."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plans = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(),
        ),
    )
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: plans)
    monkeypatch.setattr(
        cli_module,
        "fingerprint_analysis",
        lambda report, plans, metadata=None: "disabled-fingerprint",
    )

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--telemetry-store",
            "off",
            "analysis",
            "plan",
        ],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.stdout
    assert "Telemetry disabled for this session." in result.stdout


def test_cli_analysis_plan_uses_default_telemetry_dir(
    monkeypatch, tmp_path: Path
) -> None:
    """Default telemetry storage should live under .emperator/telemetry."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plans = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(),
        ),
    )
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: plans)
    monkeypatch.setattr(
        cli_module,
        "fingerprint_analysis",
        lambda report, plans, metadata=None: "default-fingerprint",
    )

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--telemetry-store",
            "jsonl",
            "analysis",
            "plan",
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    expected_path = (tmp_path / ".emperator" / "telemetry").resolve()
    assert str(expected_path) in result.stdout
    assert "Telemetry directory:" in result.stdout


def test_cli_analysis_plan_resolves_relative_telemetry_path(
    monkeypatch, tmp_path: Path
) -> None:
    """Relative telemetry paths should resolve beneath the configured project root."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plans = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(),
        ),
    )
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: plans)
    monkeypatch.setattr(
        cli_module,
        "fingerprint_analysis",
        lambda report, plans, metadata=None: "resolved-fingerprint",
    )

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--telemetry-store",
            "jsonl",
            "--telemetry-path",
            "telemetry-data",
            "analysis",
            "plan",
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    expected_path = (tmp_path / "telemetry-data").resolve()
    assert str(expected_path) in result.stdout
    assert "Telemetry directory:" in result.stdout


def test_cli_analysis_run_executes_plans(monkeypatch, tmp_path: Path) -> None:
    """Analysis run should execute filtered plans and display a summary."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "--config=auto", str(tmp_path)),
                description="Run Semgrep with auto configuration.",
            ),
        ),
    )
    start = datetime.now(UTC)
    run = TelemetryRun(
        fingerprint="run-fingerprint",
        project_root=tmp_path,
        started_at=start,
        completed_at=start,
        events=(
            TelemetryEvent(
                tool="Semgrep",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=2.5,
                timestamp=start,
                metadata={"description": plan.steps[0].description},
            ),
        ),
        notes=(),
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))

    def fake_execute(report_arg, plans_arg, **kwargs) -> TelemetryRun:
        captured["report"] = report_arg
        captured["plans"] = tuple(plans_arg)
        captured["kwargs"] = kwargs
        if kwargs.get("on_step_start") is not None:
            kwargs["on_step_start"](plans_arg[0], plans_arg[0].steps[0])
        if kwargs.get("on_step_complete") is not None:
            kwargs["on_step_complete"](plans_arg[0], plans_arg[0].steps[0], 0, 2.5)
        return run

    monkeypatch.setattr(cli_module, "execute_analysis_plan", fake_execute)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "Analysis Run Summary" in result.stdout
    assert "run-fingerprint" in result.stdout
    assert "Semgrep" in result.stdout and "Success" in result.stdout
    assert captured["plans"] == (plan,)
    kwargs = captured["kwargs"]
    assert kwargs["include_unready"] is False
    assert kwargs["metadata"]["command"] == "analysis-run"


def test_cli_analysis_run_renders_unique_severities(
    monkeypatch, tmp_path: Path
) -> None:
    """The analysis run summary should render unique severities and notes."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "--config=auto", str(tmp_path / "src")),
                description="Run Semgrep with auto configuration.",
            ),
        ),
    )
    start = datetime.now(UTC)
    run = TelemetryRun(
        fingerprint="severity-run",
        project_root=tmp_path,
        started_at=start,
        completed_at=start,
        events=(
            TelemetryEvent(
                tool="Semgrep",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=start,
                metadata={"severity": "critical"},
            ),
            TelemetryEvent(
                tool="Semgrep",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=start,
                metadata={"severity": "high"},
            ),
            TelemetryEvent(
                tool="Semgrep",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=start,
                metadata=None,
            ),
            TelemetryEvent(
                tool="Semgrep",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=start,
                metadata={"description": "No severity recorded"},
            ),
        ),
        notes=(
            "General guidance for the execution summary",
            "Semgrep: review findings for high severity",
        ),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(
        cli_module, "execute_analysis_plan", lambda *args, **kwargs: run
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "critical, high" in result.stdout
    assert "Gate" in result.stdout
    assert "BLOCK" in result.stdout
    assert "General guidance for the execution summary" in result.stdout
    # Message may be wrapped across lines, check key components
    assert "Severity gate triggered for Semgrep" in result.stdout
    assert "highest severity critical" in result.stdout
    assert "blocking remediation" in result.stdout
    # Tool note may also be wrapped, check key parts
    assert "Semgrep:" in result.stdout
    assert "review" in result.stdout
    assert "findings" in result.stdout
    assert "high" in result.stdout
    assert "severity" in result.stdout


def test_cli_analysis_run_marks_medium_severity_for_review(
    monkeypatch, tmp_path: Path
) -> None:
    """Medium severity findings should trigger a review gate."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="CodeQL",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("codeql", "analyze"),
                description="Run CodeQL",
            ),
        ),
    )
    start = datetime.now(UTC)
    run = TelemetryRun(
        fingerprint="medium-severity",
        project_root=tmp_path,
        started_at=start,
        completed_at=start,
        events=(
            TelemetryEvent(
                tool="CodeQL",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=start,
                metadata={"severity": "medium"},
            ),
        ),
        notes=(),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(
        cli_module, "execute_analysis_plan", lambda *args, **kwargs: run
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "REVIEW" in result.stdout
    # Message may be wrapped across lines, check key components
    assert "Severity gate triggered for CodeQL" in result.stdout
    assert "highest severity medium" in result.stdout
    assert "manual" in result.stdout
    assert "review" in result.stdout


def test_cli_analysis_run_handles_unknown_severity(monkeypatch, tmp_path: Path) -> None:
    """Unknown severities should trigger a review gate and surface a note."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "--config=auto", str(tmp_path)),
                description="Run Semgrep with auto configuration.",
            ),
        ),
    )
    start = datetime.now(UTC)
    run = TelemetryRun(
        fingerprint="unknown-severity",
        project_root=tmp_path,
        started_at=start,
        completed_at=start,
        events=(
            TelemetryEvent(
                tool="Semgrep",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=start,
                metadata={"severity": "urgent"},
            ),
        ),
        notes=(),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(
        cli_module, "execute_analysis_plan", lambda *args, **kwargs: run
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "REVIEW" in result.stdout
    assert "urgent" in result.stdout
    # Message may be wrapped across lines, check key components
    assert "Severity gate triggered for Semgrep" in result.stdout
    assert "unknown severity 'urgent'" in result.stdout
    assert "manual review required" in result.stdout


def test_cli_analysis_run_passes_for_low_severity(monkeypatch, tmp_path: Path) -> None:
    """Low severity findings should retain a passing gate."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Tree-sitter CLI",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("tree-sitter", "scan"),
                description="Scan with Tree-sitter",
            ),
        ),
    )
    start = datetime.now(UTC)
    run = TelemetryRun(
        fingerprint="low-severity",
        project_root=tmp_path,
        started_at=start,
        completed_at=start,
        events=(
            TelemetryEvent(
                tool="Tree-sitter CLI",
                command=plan.steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=start,
                metadata={"severity": "low"},
            ),
        ),
        notes=(),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(
        cli_module, "execute_analysis_plan", lambda *args, **kwargs: run
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout
    assert "low" in result.stdout
    assert "Severity gate triggered" not in result.stdout


def test_cli_analysis_run_rejects_invalid_severity(monkeypatch, tmp_path: Path) -> None:
    """Invalid severity selections should raise a helpful validation error."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "--config=auto", str(tmp_path / "src")),
                description="Run Semgrep with auto configuration.",
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))

    monkeypatch.setattr(
        cli_module,
        "execute_analysis_plan",
        lambda *args, **kwargs: pytest.fail(
            "execute_analysis_plan should not be invoked for invalid severities"
        ),
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run", "--severity", "unknown"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code != 0
    assert "Unsupported severity level(s): unknown" in result.stderr


def test_cli_analysis_run_filters_tools(monkeypatch, tmp_path: Path) -> None:
    """Tool filters should restrict which plans are executed."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plans = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(),
        ),
        AnalyzerPlan(
            tool="CodeQL",
            ready=True,
            reason="Ready",
            steps=(),
        ),
    )
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: plans)

    called: dict[str, object] = {}

    def fake_execute(report_arg, plans_arg, **kwargs) -> TelemetryRun:
        called["plans"] = tuple(plans_arg)
        return TelemetryRun(
            fingerprint="filtered",
            project_root=tmp_path,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            events=(),
            notes=("Filtered execution",),
        )

    monkeypatch.setattr(cli_module, "execute_analysis_plan", fake_execute)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run", "--tool", "CodeQL"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert called["plans"] == (plans[1],)
    assert "CodeQL" in result.stdout
    assert "Semgrep" not in result.stdout


def test_cli_analysis_run_records_severity_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    """Severity filters should be captured in the telemetry metadata."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "--config=auto", str(tmp_path)),
                description="Run Semgrep with auto configuration.",
                severity="high",
            ),
        ),
    )
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))

    captured: dict[str, object] = {}

    def fake_execute(report_arg, plans_arg, **kwargs) -> TelemetryRun:
        captured["metadata"] = kwargs.get("metadata")
        return TelemetryRun(
            fingerprint="severity-filter",
            project_root=tmp_path,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            events=(),
            notes=(),
        )

    monkeypatch.setattr(cli_module, "execute_analysis_plan", fake_execute)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run", "--severity", "high"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    metadata = captured["metadata"]
    assert metadata is not None
    assert metadata["severity_filter"] == ["high"]


def test_cli_analysis_run_handles_no_plans(monkeypatch, tmp_path: Path) -> None:
    """Run command should explain when no analyzers are configured."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: ())

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "No analyzer plans available yet" in result.stdout


def test_cli_analysis_run_reports_failures(monkeypatch, tmp_path: Path) -> None:
    """Failures should be highlighted in the run summary."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=True,
        reason="Ready",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "--config=auto", str(tmp_path)),
                description="Run Semgrep with auto config.",
            ),
        ),
    )
    timestamp = datetime.now(UTC)
    run = TelemetryRun(
        fingerprint="failure-fingerprint",
        project_root=tmp_path,
        started_at=timestamp,
        completed_at=timestamp,
        events=(
            TelemetryEvent(
                tool="Semgrep",
                command=plan.steps[0].command,
                exit_code=3,
                duration_seconds=1.0,
                timestamp=timestamp,
                metadata={"description": plan.steps[0].description},
            ),
        ),
        notes=("Semgrep exited with code 3",),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(
        cli_module, "execute_analysis_plan", lambda *args, **kwargs: run
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout
    assert "FAILED" in result.stdout or "failed" in result.stdout.lower()
    assert "code 3" in result.stdout


def test_cli_analysis_run_includes_unready(monkeypatch, tmp_path: Path) -> None:
    """The --include-unready flag should forward to the executor."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(tool="Semgrep", ready=False, reason="Missing deps", steps=())
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))

    forwarded: dict[str, object] = {}

    def fake_execute(report_arg, plans_arg, **kwargs) -> TelemetryRun:
        forwarded["include_unready"] = kwargs["include_unready"]
        return TelemetryRun(
            fingerprint="forced",
            project_root=tmp_path,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            events=(),
            notes=("Forced execution",),
        )

    monkeypatch.setattr(cli_module, "execute_analysis_plan", fake_execute)

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run", "--include-unready"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert forwarded["include_unready"] is True


def test_cli_analysis_run_disables_telemetry(monkeypatch, tmp_path: Path) -> None:
    """Telemetry disabled via CLI flag should be reported in the output."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(tool="Semgrep", ready=True, reason="Ready", steps=())
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(
        cli_module,
        "execute_analysis_plan",
        lambda *args, **kwargs: TelemetryRun(
            fingerprint="disabled",
            project_root=tmp_path,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            events=(),
            notes=("No steps defined for Semgrep.",),
        ),
    )

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--telemetry-store",
            "off",
            "analysis",
            "run",
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "Telemetry disabled for this session." in result.stdout


def test_cli_analysis_run_reports_directory(monkeypatch, tmp_path: Path) -> None:
    """Telemetry directory should be surfaced when using the JSONL backend."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(tool="Semgrep", ready=True, reason="Ready", steps=())
    store_path = tmp_path / "telemetry"

    def fake_execute(report_arg, plans_arg, **kwargs) -> TelemetryRun:
        return TelemetryRun(
            fingerprint="jsonl",
            project_root=tmp_path,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            events=(),
            notes=("No steps defined for Semgrep.",),
        )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(cli_module, "execute_analysis_plan", fake_execute)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--telemetry-store",
            "jsonl",
            "--telemetry-path",
            str(store_path),
            "analysis",
            "run",
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert str(store_path) in result.stdout
    assert "Telemetry directory" in result.stdout


def test_cli_analysis_run_reports_filter_miss(monkeypatch, tmp_path: Path) -> None:
    """Missing tool filters should surface a helpful warning."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(tool="Semgrep", ready=True, reason="Ready", steps=())
    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run", "--tool", "CodeQL"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "No analyzer plans matched the provided filters" in result.stdout


def test_cli_analysis_run_reports_skipped_tool(monkeypatch, tmp_path: Path) -> None:
    """Skipped analyzers should be reflected in the run summary."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=False,
        reason="Missing Semgrep CLI",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "--config=auto", str(tmp_path)),
                description="Run Semgrep.",
            ),
        ),
    )

    run = TelemetryRun(
        fingerprint="skipped",
        project_root=tmp_path,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        events=(),
        notes=("Skipped Semgrep: Missing Semgrep CLI",),
    )

    monkeypatch.setattr(cli_module, "gather_analysis", lambda root: report)
    monkeypatch.setattr(cli_module, "plan_tool_invocations", lambda report: (plan,))
    monkeypatch.setattr(
        cli_module, "execute_analysis_plan", lambda *args, **kwargs: run
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "run"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    # Details may be wrapped across lines, check key components
    assert "Skipped" in result.stdout
    assert "Semgrep" in result.stdout
    assert "Missing" in result.stdout
    assert "CLI" in result.stdout


def test_cli_rejects_unknown_telemetry_backend(tmp_path: Path) -> None:
    """Main callback should surface a helpful error for unknown telemetry stores."""
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "--telemetry-store", "invalid", "analysis", "plan"],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code != 0
    assert "Unsupported telemetry store" in result.stderr


def test_cli_rejects_telemetry_path_without_jsonl(tmp_path: Path) -> None:
    """Providing --telemetry-path without the jsonl backend should error."""
    target = tmp_path / "telemetry"
    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--telemetry-path",
            str(target),
            "analysis",
            "plan",
        ],
        env={"NO_COLOR": "1"},
    )
    assert result.exit_code != 0
    assert "requires the jsonl telemetry store" in result.stderr


def test_cli_run_entry_point_invokes_app(monkeypatch) -> None:
    """CLI module run function should invoke Typer app."""
    called: dict[str, bool] = {}

    def fake_app() -> None:
        called["invoked"] = True

    monkeypatch.setattr(cli_module, "app", fake_app)
    cli_module.run()
    assert called.get("invoked") is True


def test_cli_version_flag_shows_version() -> None:
    """Version flag should display the version and exit."""
    result = runner.invoke(app, ["--version"], env={"NO_COLOR": "1"})
    assert result.exit_code == 0, result.stdout
    assert "Emperator CLI version" in result.stdout
    assert "0.1.0" in result.stdout


def test_cli_version_flag_short_form() -> None:
    """Short version flag (-v) should also work."""
    result = runner.invoke(app, ["-v"], env={"NO_COLOR": "1"})
    assert result.exit_code == 0, result.stdout
    assert "Emperator CLI version" in result.stdout


def test_cli_no_command_shows_message() -> None:
    """Invoking CLI without command should show helpful message."""
    result = runner.invoke(app, [], env={"NO_COLOR": "1"})
    assert result.exit_code == 0, result.stdout
    assert "No command specified" in result.stdout
    assert "Use --help" in result.stdout


def test_cli_analysis_codeql_list_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Listing databases should handle empty caches gracefully."""
    monkeypatch.setattr(
        cli_module,
        "_get_codeql_manager",
        lambda state: SimpleNamespace(list_databases=lambda: ()),
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "list"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert "No cached CodeQL databases" in result.stdout


def test_cli_analysis_codeql_list_populated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Listing databases should render metadata for cached entries."""
    databases = (
        CodeQLDatabase(
            language="python",
            path=tmp_path / ".emperator" / "codeql-cache" / "python-1",
            source_root=tmp_path,
            created_at=datetime.now(tz=UTC),
            size_bytes=512,
            fingerprint="fingerprint1",
        ),
        CodeQLDatabase(
            language="javascript",
            path=tmp_path / ".emperator" / "codeql-cache" / "js-1",
            source_root=tmp_path,
            created_at=datetime.now(tz=UTC),
            size_bytes=1024,
            fingerprint="fingerprint2",
        ),
    )

    monkeypatch.setattr(
        cli_module,
        "_get_codeql_manager",
        lambda state: SimpleNamespace(list_databases=lambda: databases),
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "list"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert "Cached CodeQL Databases" in result.stdout
    assert "python" in result.stdout
    assert "javascript" in result.stdout


def test_cli_analysis_codeql_create_reports_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """CodeQL database creation should surface success metadata."""
    db_path = tmp_path / ".emperator" / "codeql-cache" / "python-test"
    db_path.mkdir(parents=True)

    async def fake_create_database(**_: object) -> CodeQLDatabase:
        return CodeQLDatabase(
            language="python",
            path=db_path,
            source_root=tmp_path,
            created_at=datetime.now(tz=UTC),
            size_bytes=1024,
            fingerprint="testfingerprint",
        )

    monkeypatch.setattr(
        cli_module,
        "_get_codeql_manager",
        lambda state: SimpleNamespace(create_database=fake_create_database),
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "create"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert "Database ready" in result.stdout
    assert "testfingerprint" in result.stdout


def test_cli_analysis_codeql_create_with_source_and_force(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom_root = tmp_path / "custom"
    custom_root.mkdir()

    observed: dict[str, object] = {}

    async def fake_create_database(
        *,
        source_root: Path,
        language: str,
        force: bool,
        extra_args: tuple[str, ...] = (),
        **_: object,
    ) -> CodeQLDatabase:
        observed["source_root"] = source_root
        observed["language"] = language
        observed["force"] = force
        observed["extra_args"] = extra_args
        return CodeQLDatabase(
            language=language,
            path=tmp_path / ".emperator" / "codeql-cache" / "python-test",
            source_root=source_root,
            created_at=datetime.now(tz=UTC),
            size_bytes=256,
            fingerprint="forcefingerprint",
        )

    monkeypatch.setattr(
        cli_module,
        "_get_codeql_manager",
        lambda state: SimpleNamespace(create_database=fake_create_database),
    )

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "analysis",
            "codeql",
            "create",
            "--source",
            str(custom_root.relative_to(tmp_path)),
            "--language",
            "python",
            "--force",
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert observed["source_root"] == custom_root
    assert observed["language"] == "python"
    assert observed["force"] is True


def test_cli_analysis_codeql_create_handles_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def fake_create_database(**_: object) -> CodeQLDatabase:
        raise CodeQLManagerError("create failed")

    monkeypatch.setattr(
        cli_module,
        "_get_codeql_manager",
        lambda state: SimpleNamespace(create_database=fake_create_database),
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "create"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 1
    assert "create failed" in result.stdout


def test_cli_analysis_codeql_query_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Query execution should discover default queries when none provided."""
    queries_dir = tmp_path / "rules" / "codeql"
    queries_dir.mkdir(parents=True)
    default_query = queries_dir / "security.ql"
    default_query.write_text("predicate dummy() { true }", encoding="utf-8")

    database_dir = tmp_path / ".emperator" / "codeql-cache" / "python-db"
    database_dir.mkdir(parents=True)
    database = CodeQLDatabase(
        language="python",
        path=database_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=128,
        fingerprint="db",
    )

    def fake_load_database(path: Path) -> CodeQLDatabase:
        assert path == database_dir
        return database

    async def fake_run_queries(
        database: CodeQLDatabase,
        queries: tuple[Path, ...],
        sarif_output: Path | None = None,
        **_: object,
    ) -> tuple[CodeQLFinding, ...]:
        assert default_query.resolve() in queries
        return (
            CodeQLFinding(
                rule_id="security.test",
                message="Issue",
                severity="error",
                file_path=tmp_path / "module.py",
                start_line=5,
                start_column=1,
                sarif={},
            ),
        )

    manager = SimpleNamespace(
        load_database=fake_load_database, run_queries=fake_run_queries
    )
    monkeypatch.setattr(cli_module, "_get_codeql_manager", lambda state: manager)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "analysis",
            "codeql",
            "query",
            "--database",
            str(database_dir),
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0, result.stdout
    assert "security.test" in result.stdout
    assert "module.py" in result.stdout


def test_cli_analysis_codeql_query_custom_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_dir = tmp_path / ".emperator" / "codeql-cache" / "python-db"
    database_dir.mkdir(parents=True)
    database = CodeQLDatabase(
        language="python",
        path=database_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=128,
        fingerprint="db",
    )

    def fake_load_database(path: Path) -> CodeQLDatabase:
        assert path == database_dir
        return database

    async def fake_run_queries(
        database: CodeQLDatabase,
        queries: tuple[Path, ...],
        sarif_output: Path | None = None,
        **_: object,
    ) -> tuple[CodeQLFinding, ...]:
        assert sarif_output == tmp_path / "reports" / "custom.sarif"
        return ()

    queries_dir = tmp_path / "rules" / "codeql"
    queries_dir.mkdir(parents=True)
    query_path = queries_dir / "security.ql"
    query_path.write_text("predicate dummy() { true }", encoding="utf-8")

    manager = SimpleNamespace(
        load_database=fake_load_database, run_queries=fake_run_queries
    )
    monkeypatch.setattr(cli_module, "_get_codeql_manager", lambda state: manager)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "analysis",
            "codeql",
            "query",
            "--database",
            str(database_dir),
            "--query",
            str(query_path),
            "--output",
            str(Path("reports") / "custom.sarif"),
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert "SARIF output" in result.stdout
    assert "reports/custom.sarif" in result.stdout


def test_cli_analysis_codeql_query_requires_database(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "query"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 2
    output = result.stdout + (result.stderr or "")
    assert "A database path is required." in output


def test_cli_analysis_codeql_query_handles_load_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_dir = tmp_path / ".emperator" / "codeql-cache" / "python-db"

    def fake_load_database(path: Path) -> CodeQLDatabase:
        del path
        raise CodeQLManagerError("load failed")

    manager = SimpleNamespace(load_database=fake_load_database)
    monkeypatch.setattr(cli_module, "_get_codeql_manager", lambda state: manager)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "analysis",
            "codeql",
            "query",
            "--database",
            str(database_dir),
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 1
    assert "load failed" in result.stdout


def test_cli_analysis_codeql_query_handles_missing_queries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_dir = tmp_path / ".emperator" / "codeql-cache" / "python-db"
    database_dir.mkdir(parents=True)
    database = CodeQLDatabase(
        language="python",
        path=database_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=128,
        fingerprint="db",
    )

    manager = SimpleNamespace(load_database=lambda path: database)
    monkeypatch.setattr(cli_module, "_get_codeql_manager", lambda state: manager)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "analysis",
            "codeql",
            "query",
            "--database",
            str(database_dir),
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 1
    assert "No queries specified" in result.stdout


def test_cli_analysis_codeql_query_handles_execution_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    queries_dir = tmp_path / "rules" / "codeql"
    queries_dir.mkdir(parents=True)
    query_path = queries_dir / "rule.ql"
    query_path.write_text("predicate dummy() { true }", encoding="utf-8")

    database_dir = tmp_path / ".emperator" / "codeql-cache" / "python-db"
    database_dir.mkdir(parents=True)
    database = CodeQLDatabase(
        language="python",
        path=database_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=128,
        fingerprint="db",
    )

    def fake_load_database(path: Path) -> CodeQLDatabase:
        assert path == database_dir
        return database

    async def fake_run_queries(
        database: CodeQLDatabase,
        queries: tuple[Path, ...],
        sarif_output: Path | None = None,
        **_: object,
    ) -> tuple[CodeQLFinding, ...]:
        del database, queries, sarif_output
        raise CodeQLUnavailableError("missing binary")

    manager = SimpleNamespace(
        load_database=fake_load_database,
        run_queries=fake_run_queries,
    )
    monkeypatch.setattr(cli_module, "_get_codeql_manager", lambda state: manager)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "analysis",
            "codeql",
            "query",
            "--database",
            str(database_dir),
            "--query",
            str(query_path),
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 1
    assert "missing binary" in result.stdout


def test_cli_analysis_codeql_query_reports_no_findings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    queries_dir = tmp_path / "rules" / "codeql"
    queries_dir.mkdir(parents=True)
    query_path = queries_dir / "rule.ql"
    query_path.write_text("predicate dummy() { true }", encoding="utf-8")

    database_dir = tmp_path / ".emperator" / "codeql-cache" / "python-db"
    database_dir.mkdir(parents=True)
    database = CodeQLDatabase(
        language="python",
        path=database_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=128,
        fingerprint="db",
    )

    async def fake_run_queries(*args, **kwargs) -> tuple[CodeQLFinding, ...]:  # type: ignore[no-untyped-def]
        del args, kwargs
        return ()

    manager = SimpleNamespace(
        load_database=lambda path: database, run_queries=fake_run_queries
    )
    monkeypatch.setattr(cli_module, "_get_codeql_manager", lambda state: manager)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "analysis",
            "codeql",
            "query",
            "--database",
            str(database_dir),
            "--query",
            str(query_path),
        ],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert "did not report any findings" in result.stdout


def test_cli_analysis_codeql_prune_reports(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Prune command should display removed databases."""
    removed_path = tmp_path / ".emperator" / "codeql-cache" / "python-old"

    monkeypatch.setattr(
        cli_module,
        "_get_codeql_manager",
        lambda state: SimpleNamespace(prune=lambda **_: (removed_path,)),
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "prune", "--older-than", "1"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert str(removed_path) in result.stdout


def test_cli_analysis_codeql_prune_when_no_matches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        cli_module,
        "_get_codeql_manager",
        lambda state: SimpleNamespace(prune=lambda **_: ()),
    )

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "prune", "--older-than", "1"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 0
    assert "No cached databases matched the prune criteria" in result.stdout


def test_cli_analysis_codeql_prune_requires_arguments(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "prune"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 2
    output = result.stdout + (result.stderr or "")
    assert "Provide --older-than or --max-bytes" in output


def test_cli_analysis_codeql_prune_validates_negative_values(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "analysis", "codeql", "prune", "--older-than", "-1"],
        env={"NO_COLOR": "1"},
    )

    assert result.exit_code == 2
    output = result.stdout + (result.stderr or "")
    assert "older-than must be non-negative" in output

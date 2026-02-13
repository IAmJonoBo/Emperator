"""Tests for the analysis and IR planning helpers."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

try:
    from emperator.analysis import (
        AnalysisHint,
        AnalysisReport,
        AnalyzerCommand,
        AnalyzerPlan,
        InMemoryTelemetryStore,
        JSONLTelemetryStore,
        LanguageSummary,
        TelemetryEvent,
        TelemetryRun,
        ToolStatus,
        detect_languages,
        execute_analysis_plan,
        fingerprint_analysis,
        gather_analysis,
        plan_tool_invocations,
    )
except ModuleNotFoundError:  # pragma: no cover - allow running tests without install
    sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
    from emperator.analysis import (
        AnalysisHint,
        AnalysisReport,
        AnalyzerCommand,
        AnalyzerPlan,
        InMemoryTelemetryStore,
        JSONLTelemetryStore,
        LanguageSummary,
        TelemetryEvent,
        TelemetryRun,
        ToolStatus,
        detect_languages,
        execute_analysis_plan,
        fingerprint_analysis,
        gather_analysis,
        plan_tool_invocations,
    )


def _touch(path: Path, content: str = "pass") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_detect_languages_counts_and_samples(tmp_path: Path) -> None:
    """Language detection should count files per language and capture samples."""
    _touch(tmp_path / "src" / "app.py", 'print("hello")')
    _touch(tmp_path / "src" / "module" / "domain.py", "class Thing: ...")
    _touch(tmp_path / "docs" / "guide.md", "# Usage")
    _touch(tmp_path / "config" / "settings.yaml", "key: value")
    _touch(tmp_path / "notes.txt", "skip me")  # unknown extension to cover fallback
    _touch(
        tmp_path / "node_modules" / "ignore.js", 'console.log("skip")'
    )  # skipped directory

    summaries = detect_languages(tmp_path)
    counts = {summary.language: summary.file_count for summary in summaries}
    assert counts["Python"] == 2
    assert counts["Markdown"] == 1
    assert counts["YAML"] == 1

    python_summary = next(
        summary for summary in summaries if summary.language == "Python"
    )
    assert "src/app.py" in python_summary.sample_files
    assert python_summary.file_count == 2


def test_gather_analysis_reports_tool_availability(monkeypatch, tmp_path: Path) -> None:
    """Gathered analysis report should include tool availability status."""
    module = sys.modules["emperator.analysis"]
    _touch(tmp_path / "src" / "service.py", "def run(): ...")

    def fake_which(name: str) -> str | None:
        if name == "codeql":
            return None
        return f"/opt/tools/{name}"

    monkeypatch.setattr(module.shutil, "which", fake_which)

    report = gather_analysis(tmp_path)
    assert isinstance(report, AnalysisReport)

    availability = {status.name: status.available for status in report.tool_statuses}
    assert availability["Semgrep"] is True
    assert availability["Tree-sitter CLI"] is True
    assert availability["CodeQL"] is False


def test_gather_analysis_produces_actionable_hints(monkeypatch, tmp_path: Path) -> None:
    """Missing tooling should yield hints that point at remediation steps."""
    module = sys.modules["emperator.analysis"]
    _touch(tmp_path / "src" / "app.py", 'print("hello")')

    monkeypatch.setattr(module.shutil, "which", lambda name: None)

    report = gather_analysis(tmp_path)
    assert any(isinstance(hint, AnalysisHint) for hint in report.hints)
    combined = " ".join(hint.guidance for hint in report.hints)
    assert "CodeQL" in combined
    assert "Semgrep" in combined
    assert "Tree-sitter" in combined


def test_gather_analysis_handles_empty_repository(tmp_path: Path) -> None:
    """Empty repositories should produce a guidance hint."""
    report = gather_analysis(tmp_path)
    assert report.languages == ()
    assert any(hint.topic == "Sources" for hint in report.hints)


def test_plan_tool_invocations_semgrep_ready(tmp_path: Path) -> None:
    """Semgrep should produce a ready plan when the tool is available."""
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=2, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="Semgrep",
                available=True,
                location="/usr/bin/semgrep",
                hint="Available at /usr/bin/semgrep",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    semgrep_plan = next(plan for plan in plans if plan.tool == "Semgrep")
    assert semgrep_plan.ready is True
    assert semgrep_plan.steps
    assert semgrep_plan.steps[0].command[-1] == str(tmp_path)


def test_plan_tool_invocations_codeql_languages(tmp_path: Path) -> None:
    """CodeQL plans should include language flags and SARIF outputs."""
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=1, sample_files=("src/app.py",)
            ),
            LanguageSummary(
                language="TypeScript", file_count=1, sample_files=("ui/app.tsx",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="CodeQL",
                available=True,
                location="/opt/codeql",
                hint="Available at /opt/codeql",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    codeql_plan = next(plan for plan in plans if plan.tool == "CodeQL")
    assert codeql_plan.ready is True
    create_command = codeql_plan.steps[0].command
    assert "--language=python" in create_command
    assert "--language=javascript" in create_command
    analyze_steps = [
        step
        for step in codeql_plan.steps
        if "codeql/javascript-queries" in step.command
    ]
    assert analyze_steps
    output_flag = str(Path("artifacts") / "codeql-javascript.sarif")
    assert any(output_flag in step.command for step in analyze_steps)


def test_plan_tool_invocations_handles_missing_tool(tmp_path: Path) -> None:
    """Plans should surface hints when analyzers are unavailable."""
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=1, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="CodeQL",
                available=False,
                location=None,
                hint="Install the CodeQL CLI.",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    codeql_plan = next(plan for plan in plans if plan.tool == "CodeQL")
    assert codeql_plan.ready is False
    assert "Install the CodeQL CLI." in codeql_plan.reason
    assert codeql_plan.steps


def test_plan_tool_invocations_handles_no_supported_languages(tmp_path: Path) -> None:
    """CodeQL plans should reflect when no supported languages are present."""
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Markdown", file_count=2, sample_files=("docs/guide.md",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="CodeQL",
                available=True,
                location="/opt/codeql",
                hint="Available at /opt/codeql",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    codeql_plan = next(plan for plan in plans if plan.tool == "CodeQL")
    assert codeql_plan.ready is False
    assert "No CodeQL-supported languages" in codeql_plan.reason
    assert codeql_plan.steps == ()


def test_fingerprint_analysis_reflects_plan_changes(tmp_path: Path) -> None:
    """Changing analyzer plans should result in a distinct fingerprint."""
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=2, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="Semgrep",
                available=True,
                location="/usr/bin/semgrep",
                hint="Available at /usr/bin/semgrep",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    base_plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Semgrep ready at /usr/bin/semgrep.",
            steps=(
                AnalyzerCommand(
                    command=(
                        "semgrep",
                        "scan",
                        "--config=auto",
                        "--metrics=off",
                        str(tmp_path),
                    ),
                    description="Run Semgrep with the selected configuration over the repository.",
                ),
            ),
        ),
    )
    alternate_plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Semgrep ready at /usr/bin/semgrep.",
            steps=(
                AnalyzerCommand(
                    command=(
                        "semgrep",
                        "scan",
                        "--config=p/ci",
                        "--metrics=off",
                        str(tmp_path),
                    ),
                    description="Run Semgrep with the selected configuration over the repository.",
                ),
            ),
        ),
    )

    digest_default = fingerprint_analysis(report, base_plan)
    digest_alternate = fingerprint_analysis(report, alternate_plan)
    assert digest_default != digest_alternate


def test_in_memory_store_persists_runs(tmp_path: Path) -> None:
    """In-memory telemetry store should persist and expose run history."""
    store = InMemoryTelemetryStore()
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=1, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="Semgrep",
                available=True,
                location="/usr/bin/semgrep",
                hint="Available at /usr/bin/semgrep",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Semgrep ready at /usr/bin/semgrep.",
            steps=(
                AnalyzerCommand(
                    command=(
                        "semgrep",
                        "scan",
                        "--config=auto",
                        "--metrics=off",
                        str(tmp_path),
                    ),
                    description="Run Semgrep with the selected configuration over the repository.",
                ),
            ),
        ),
    )
    fingerprint = fingerprint_analysis(report, plan)
    started_at = datetime.now(UTC)
    event = TelemetryEvent(
        tool="Semgrep",
        command=plan[0].steps[0].command,
        exit_code=0,
        duration_seconds=1.2,
        timestamp=started_at,
        metadata={"config": "auto"},
    )
    payload = event.to_payload()
    assert payload["tool"] == "Semgrep"
    assert payload["command"][-1] == str(tmp_path)
    assert payload["metadata"]["config"] == "auto"
    run = TelemetryRun(
        fingerprint=fingerprint,
        project_root=tmp_path,
        started_at=started_at,
        completed_at=started_at,
        events=(event,),
        notes=("cached",),
    )

    assert store.latest("missing") is None
    store.persist(run)
    assert store.latest(fingerprint) == run
    assert store.history(fingerprint) == (run,)
    assert run.successful is True
    assert run.duration_seconds == 0.0


def test_jsonl_store_persists_history(tmp_path: Path) -> None:
    """JSONL telemetry store should persist runs and enforce history limits."""
    store = JSONLTelemetryStore(tmp_path / "telemetry", max_history=2)
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=1, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="Semgrep",
                available=True,
                location="/usr/bin/semgrep",
                hint="Available at /usr/bin/semgrep",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Semgrep ready at /usr/bin/semgrep.",
            steps=(
                AnalyzerCommand(
                    command=(
                        "semgrep",
                        "scan",
                        "--config=auto",
                        "--metrics=off",
                        str(tmp_path),
                    ),
                    description="Run Semgrep with the selected configuration over the repository.",
                ),
            ),
        ),
    )
    fingerprint = fingerprint_analysis(report, plan)
    telemetry_file = tmp_path / "telemetry" / f"{fingerprint}.jsonl"

    timestamps = [datetime.now(UTC), datetime.now(UTC), datetime.now(UTC)]
    for idx, timestamp in enumerate(timestamps, start=1):
        event = TelemetryEvent(
            tool="Semgrep",
            command=plan[0].steps[0].command,
            exit_code=0,
            duration_seconds=idx * 1.5,
            timestamp=timestamp,
            metadata={"config": f"auto-{idx}"},
        )
        run = TelemetryRun(
            fingerprint=fingerprint,
            project_root=tmp_path,
            started_at=timestamp,
            completed_at=timestamp,
            events=(event,),
            notes=(f"run-{idx}",),
        )
        store.persist(run)

    assert telemetry_file.exists()

    # Append an empty line to validate parser resilience.
    with telemetry_file.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    assert store.latest("missing-fingerprint") is None
    history = store.history(fingerprint)
    assert len(history) == 2
    assert history[-1].notes == ("run-3",)
    assert store.latest(fingerprint) == history[-1]


def test_execute_analysis_plan_applies_severity_filter(tmp_path: Path) -> None:
    """Severity filters should skip unmatched steps and emit explanatory notes."""
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = AnalyzerPlan(
        tool="Semgrep",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("semgrep", "scan", str(tmp_path)),
                description="Run Semgrep scan",
                severity="low",
            ),
        ),
    )

    run = execute_analysis_plan(
        report,
        (plan,),
        severity_filter=("high",),
        runner=lambda command, cwd: SimpleNamespace(returncode=0, stdout="", stderr=""),
        time_source=lambda: datetime.now(UTC),
    )

    assert run.events == ()
    assert any("Skipped Semgrep step" in note for note in run.notes)
    assert any("All steps skipped for Semgrep" in note for note in run.notes)


def test_execute_analysis_plan_warns_on_missing_severity(tmp_path: Path) -> None:
    """Steps lacking severity metadata should emit notes when filters are active."""
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = AnalyzerPlan(
        tool="CodeQL",
        ready=True,
        reason="Ready to scan",
        steps=(
            AnalyzerCommand(
                command=("codeql", "analyze"),
                description="Run CodeQL analysis",
                severity=None,
            ),
        ),
    )

    runner_calls: list[tuple[tuple[str, ...], Path]] = []

    def fake_runner(command: tuple[str, ...], cwd: Path) -> SimpleNamespace:
        runner_calls.append((command, cwd))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    run = execute_analysis_plan(
        report,
        (plan,),
        severity_filter=("low",),
        runner=fake_runner,
        time_source=lambda: datetime.now(UTC),
    )

    assert len(runner_calls) == 1
    assert any("lacks severity metadata" in note for note in run.notes)
    assert (
        run.events[0].metadata is not None
        and run.events[0].metadata.get("severity") is None
    )


def test_jsonl_store_recovers_from_corrupted_lines(tmp_path: Path) -> None:
    """Telemetry store should ignore corrupted JSONL entries when reading history."""
    store = JSONLTelemetryStore(tmp_path / "telemetry")
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=1, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="Semgrep",
                available=True,
                location="/usr/bin/semgrep",
                hint="Available at /usr/bin/semgrep",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Semgrep ready at /usr/bin/semgrep.",
            steps=(
                AnalyzerCommand(
                    command=(
                        "semgrep",
                        "scan",
                        "--config=auto",
                        "--metrics=off",
                        str(tmp_path),
                    ),
                    description="Run Semgrep with the selected configuration over the repository.",
                ),
            ),
        ),
    )
    fingerprint = fingerprint_analysis(report, plan)
    telemetry_file = tmp_path / "telemetry" / f"{fingerprint}.jsonl"

    base_timestamp = datetime.now(UTC)
    first_run = TelemetryRun(
        fingerprint=fingerprint,
        project_root=tmp_path,
        started_at=base_timestamp,
        completed_at=base_timestamp,
        events=(
            TelemetryEvent(
                tool="Semgrep",
                command=plan[0].steps[0].command,
                exit_code=0,
                duration_seconds=1.0,
                timestamp=base_timestamp,
                metadata={"config": "auto"},
            ),
        ),
        notes=("baseline",),
    )
    store.persist(first_run)

    # Inject a corrupted JSON line to emulate partial writes or manual edits.
    with telemetry_file.open("a", encoding="utf-8") as handle:
        handle.write("{corrupt-json\n")
        handle.write("{}\n")

    second_timestamp = datetime.now(UTC)
    second_run = TelemetryRun(
        fingerprint=fingerprint,
        project_root=tmp_path,
        started_at=second_timestamp,
        completed_at=second_timestamp,
        events=(
            TelemetryEvent(
                tool="Semgrep",
                command=plan[0].steps[0].command,
                exit_code=0,
                duration_seconds=2.0,
                timestamp=second_timestamp,
                metadata={"config": "strict"},
            ),
        ),
        notes=("recovered",),
    )
    store.persist(second_run)

    history = store.history(fingerprint)
    assert history == (first_run, second_run)

    # Ensure the corrupted entry is not preserved.
    lines = [
        line for line in telemetry_file.read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(lines) == 2
    for line in lines:
        json.loads(line)


def test_execute_analysis_plan_records_events(tmp_path: Path) -> None:
    """Executor should run ready steps, persist telemetry, and capture metadata."""
    start = datetime(2025, 1, 1, tzinfo=UTC)
    step_start = datetime(2025, 1, 1, 0, 0, 5, tzinfo=UTC)
    step_end = datetime(2025, 1, 1, 0, 0, 9, tzinfo=UTC)
    ticks = iter((start, step_start, step_end))

    def fake_time() -> datetime:
        return next(ticks)

    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=1, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready to scan.",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep with the auto configuration.",
                    severity="medium",
                ),
            ),
        ),
    )
    store = InMemoryTelemetryStore()
    executed: list[tuple[tuple[str, ...], Path | None]] = []

    def fake_runner(
        command: tuple[str, ...], *, cwd: Path | None = None
    ) -> SimpleNamespace:
        executed.append((command, cwd))
        return SimpleNamespace(returncode=0)

    run = execute_analysis_plan(
        report,
        plan,
        telemetry_store=store,
        metadata={"command": "unit-test"},
        runner=fake_runner,
        time_source=fake_time,
        severity_filter=("medium",),
    )

    fingerprint = fingerprint_analysis(report, plan, metadata={"command": "unit-test"})
    assert run.fingerprint == fingerprint
    latest = store.latest(fingerprint)
    assert latest is not None and latest.events == run.events
    assert executed == [(plan[0].steps[0].command, tmp_path)]
    assert run.events[0].duration_seconds == 4.0
    assert run.events[0].metadata == {
        "description": plan[0].steps[0].description,
        "severity": "medium",
    }


def test_execute_analysis_plan_handles_missing_binary(tmp_path: Path) -> None:
    """Runner exceptions should be converted into telemetry events and notes."""
    report = AnalysisReport(
        languages=(
            LanguageSummary(
                language="Python", file_count=1, sample_files=("src/app.py",)
            ),
        ),
        tool_statuses=(
            ToolStatus(
                name="Semgrep",
                available=True,
                location="/usr/bin/semgrep",
                hint="Available at /usr/bin/semgrep",
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Semgrep ready at /usr/bin/semgrep.",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--version"),
                    description="Probe Semgrep version.",
                    severity="medium",
                ),
            ),
        ),
    )

    def failing_runner(command: tuple[str, ...], *, cwd: Path | None = None) -> None:
        raise FileNotFoundError("semgrep binary not found")

    run = execute_analysis_plan(
        report,
        plan,
        telemetry_store=None,
        include_unready=False,
        severity_filter=None,
        runner=failing_runner,
    )

    assert len(run.events) == 1
    event = run.events[0]
    assert event.exit_code == 127
    assert event.metadata and event.metadata["severity"] == "medium"
    assert event.metadata.get("error") == "semgrep binary not found"
    assert any("semgrep binary not found" in note for note in run.notes)
    assert any("exit code 127" in note for note in run.notes)


def test_execute_analysis_plan_skips_unready(tmp_path: Path) -> None:
    """Unready analyzers should be skipped unless explicitly forced."""
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="CodeQL",
            ready=False,
            reason="Missing CodeQL CLI.",
            steps=(
                AnalyzerCommand(
                    command=("codeql", "database", "create"),
                    description="Prepare CodeQL database.",
                ),
            ),
        ),
    )
    run = execute_analysis_plan(
        report,
        plan,
        runner=lambda *args, **kwargs: pytest.fail(
            "Runner should not be invoked for unready plans"
        ),
        time_source=lambda: datetime(2025, 1, 1, tzinfo=UTC),
    )

    assert run.events == ()
    assert any("CodeQL" in note and "Skipped" in note for note in run.notes)


def test_execute_analysis_plan_notes_missing_severity_metadata(tmp_path: Path) -> None:
    """Severity filters should note when steps lack severity metadata."""
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready to scan.",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep with the auto configuration.",
                ),
            ),
        ),
    )

    run = execute_analysis_plan(
        report,
        plan,
        runner=lambda *args, **kwargs: SimpleNamespace(returncode=0),
        severity_filter=("high",),
        time_source=lambda: datetime.now(UTC),
    )

    assert run.events, "Step lacking severity metadata should still execute."
    assert any("lacks severity metadata" in note for note in run.notes)


def test_execute_analysis_plan_skips_steps_via_severity_filter(tmp_path: Path) -> None:
    """Severity filters should prevent execution of non-matching steps."""
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready to scan.",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep with the auto configuration.",
                    severity="low",
                ),
            ),
        ),
    )
    run = execute_analysis_plan(
        report,
        plan,
        runner=lambda *args, **kwargs: pytest.fail(
            "Runner should not be called when all steps are filtered"
        ),
        severity_filter=("high",),
        time_source=lambda: datetime.now(UTC),
    )

    assert run.events == ()
    assert any("Skipped" in note for note in run.notes)
    assert any("All steps skipped" in note for note in run.notes)


def test_execute_analysis_plan_honours_callbacks(tmp_path: Path) -> None:
    """Callbacks should fire with execution metadata and capture failures."""
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=False,
            reason="Dry run",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep.",
                ),
            ),
        ),
    )
    times = iter(
        (
            datetime(2025, 2, 1, tzinfo=UTC),
            datetime(2025, 2, 1, 0, 0, 3, tzinfo=UTC),
            datetime(2025, 2, 1, 0, 0, 4, tzinfo=UTC),
        )
    )
    started: list[tuple[str, tuple[str, ...]]] = []
    completed: list[tuple[str, tuple[str, ...], int, float]] = []

    def fake_runner(
        command: tuple[str, ...], *, cwd: Path | None = None
    ) -> SimpleNamespace:
        assert cwd == tmp_path
        return SimpleNamespace(returncode=2)

    def on_start(current_plan: AnalyzerPlan, command: AnalyzerCommand) -> None:
        started.append((current_plan.tool, command.command))

    def on_complete(
        current_plan: AnalyzerPlan,
        command: AnalyzerCommand,
        exit_code: int,
        duration: float,
    ) -> None:
        completed.append((current_plan.tool, command.command, exit_code, duration))

    run = execute_analysis_plan(
        report,
        plan,
        include_unready=True,
        runner=fake_runner,
        time_source=lambda: next(times),
        on_step_start=on_start,
        on_step_complete=on_complete,
    )

    assert started == [("Semgrep", plan[0].steps[0].command)]
    assert completed == [("Semgrep", plan[0].steps[0].command, 2, 1.0)]
    assert run.events and run.events[0].exit_code == 2
    assert any("Semgrep" in note and "exit code 2" in note for note in run.notes)


def test_execute_analysis_plan_uses_default_runner(monkeypatch, tmp_path: Path) -> None:
    """Default runner should invoke subprocess.run with expected arguments."""
    module = sys.modules["emperator.analysis"]
    report = AnalysisReport(
        languages=(),
        tool_statuses=(),
        hints=(),
        project_root=tmp_path,
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep.",
                ),
            ),
        ),
    )
    calls: list[tuple[tuple[str, ...], Path | None, bool, bool, bool]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path | None = None,
        check: bool,
        text: bool,
        capture_output: bool,
    ) -> SimpleNamespace:
        calls.append((command, cwd, check, text, capture_output))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    timestamps = iter(
        (
            datetime(2025, 3, 1, tzinfo=UTC),
            datetime(2025, 3, 1, 0, 0, 2, tzinfo=UTC),
            datetime(2025, 3, 1, 0, 0, 4, tzinfo=UTC),
        )
    )

    run = execute_analysis_plan(report, plan, time_source=lambda: next(timestamps))

    assert calls == [(plan[0].steps[0].command, tmp_path.resolve(), False, True, True)]
    assert run.events and run.events[0].exit_code == 0


def test_execute_analysis_plan_supports_exit_code_attribute(tmp_path: Path) -> None:
    """Runner results exposing exit_code should be accepted."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep.",
                ),
            ),
        ),
    )

    run = execute_analysis_plan(
        report,
        plan,
        runner=lambda command, *, cwd=None: SimpleNamespace(exit_code=5),
        time_source=lambda: datetime(2025, 4, 1, tzinfo=UTC),
    )

    assert run.events and run.events[0].exit_code == 5


def test_execute_analysis_plan_accepts_integer_exit_code(tmp_path: Path) -> None:
    """Plain integer runner results should be normalised to exit codes."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep.",
                ),
            ),
        ),
    )

    run = execute_analysis_plan(
        report,
        plan,
        runner=lambda command, *, cwd=None: 0,
        time_source=lambda: datetime(2025, 4, 2, tzinfo=UTC),
    )

    assert run.events and run.events[0].exit_code == 0


def test_execute_analysis_plan_raises_when_exit_code_missing(tmp_path: Path) -> None:
    """Missing exit code information should raise a helpful TypeError."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = (
        AnalyzerPlan(
            tool="Semgrep",
            ready=True,
            reason="Ready",
            steps=(
                AnalyzerCommand(
                    command=("semgrep", "--config=auto", str(tmp_path)),
                    description="Run Semgrep.",
                ),
            ),
        ),
    )

    with pytest.raises(TypeError):
        execute_analysis_plan(
            report,
            plan,
            runner=lambda command, *, cwd=None: object(),
            time_source=lambda: datetime(2025, 5, 1, tzinfo=UTC),
        )


def test_execute_analysis_plan_notes_missing_steps(tmp_path: Path) -> None:
    """Plans without steps should record a descriptive note."""
    report = AnalysisReport(
        languages=(), tool_statuses=(), hints=(), project_root=tmp_path
    )
    plan = (AnalyzerPlan(tool="CodeQL", ready=True, reason="Ready", steps=()),)

    run = execute_analysis_plan(
        report,
        plan,
        time_source=lambda: datetime(2025, 6, 1, tzinfo=UTC),
    )

    assert run.events == ()
    assert run.notes == ("No steps defined for CodeQL.",)

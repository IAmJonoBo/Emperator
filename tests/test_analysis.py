"""Tests for the analysis and IR planning helpers."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from emperator.analysis import (
        AnalysisHint,
        AnalysisReport,
        LanguageSummary,
        ToolStatus,
        detect_languages,
        gather_analysis,
        plan_tool_invocations,
    )
except ModuleNotFoundError:  # pragma: no cover - allow running tests without install
    sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
    from emperator.analysis import (
        AnalysisHint,
        AnalysisReport,
        LanguageSummary,
        ToolStatus,
        detect_languages,
        gather_analysis,
        plan_tool_invocations,
    )


def _touch(path: Path, content: str = 'pass') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def test_detect_languages_counts_and_samples(tmp_path: Path) -> None:
    """Language detection should count files per language and capture samples."""

    _touch(tmp_path / 'src' / 'app.py', 'print("hello")')
    _touch(tmp_path / 'src' / 'module' / 'domain.py', 'class Thing: ...')
    _touch(tmp_path / 'docs' / 'guide.md', '# Usage')
    _touch(tmp_path / 'config' / 'settings.yaml', 'key: value')
    _touch(tmp_path / 'notes.txt', 'skip me')  # unknown extension to cover fallback
    _touch(tmp_path / 'node_modules' / 'ignore.js', 'console.log("skip")')  # skipped directory

    summaries = detect_languages(tmp_path)
    counts = {summary.language: summary.file_count for summary in summaries}
    assert counts['Python'] == 2
    assert counts['Markdown'] == 1
    assert counts['YAML'] == 1

    python_summary = next(summary for summary in summaries if summary.language == 'Python')
    assert 'src/app.py' in python_summary.sample_files
    assert python_summary.file_count == 2


def test_gather_analysis_reports_tool_availability(monkeypatch, tmp_path: Path) -> None:
    """Gathered analysis report should include tool availability status."""

    module = sys.modules['emperator.analysis']
    _touch(tmp_path / 'src' / 'service.py', 'def run(): ...')

    def fake_which(name: str) -> str | None:
        if name == 'codeql':
            return None
        return f'/opt/tools/{name}'

    monkeypatch.setattr(module.shutil, 'which', fake_which)

    report = gather_analysis(tmp_path)
    assert isinstance(report, AnalysisReport)

    availability = {status.name: status.available for status in report.tool_statuses}
    assert availability['Semgrep'] is True
    assert availability['Tree-sitter CLI'] is True
    assert availability['CodeQL'] is False


def test_gather_analysis_produces_actionable_hints(monkeypatch, tmp_path: Path) -> None:
    """Missing tooling should yield hints that point at remediation steps."""

    module = sys.modules['emperator.analysis']
    _touch(tmp_path / 'src' / 'app.py', 'print("hello")')

    monkeypatch.setattr(module.shutil, 'which', lambda name: None)

    report = gather_analysis(tmp_path)
    assert any(isinstance(hint, AnalysisHint) for hint in report.hints)
    combined = ' '.join(hint.guidance for hint in report.hints)
    assert 'CodeQL' in combined
    assert 'Semgrep' in combined
    assert 'Tree-sitter' in combined


def test_gather_analysis_handles_empty_repository(tmp_path: Path) -> None:
    """Empty repositories should produce a guidance hint."""

    report = gather_analysis(tmp_path)
    assert report.languages == ()
    assert any(hint.topic == 'Sources' for hint in report.hints)


def test_plan_tool_invocations_semgrep_ready(tmp_path: Path) -> None:
    """Semgrep should produce a ready plan when the tool is available."""

    report = AnalysisReport(
        languages=(
            LanguageSummary(language='Python', file_count=2, sample_files=('src/app.py',)),
        ),
        tool_statuses=(
            ToolStatus(
                name='Semgrep',
                available=True,
                location='/usr/bin/semgrep',
                hint='Available at /usr/bin/semgrep',
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    semgrep_plan = next(plan for plan in plans if plan.tool == 'Semgrep')
    assert semgrep_plan.ready is True
    assert semgrep_plan.steps
    assert semgrep_plan.steps[0].command[-1] == str(tmp_path)


def test_plan_tool_invocations_codeql_languages(tmp_path: Path) -> None:
    """CodeQL plans should include language flags and SARIF outputs."""

    report = AnalysisReport(
        languages=(
            LanguageSummary(language='Python', file_count=1, sample_files=('src/app.py',)),
            LanguageSummary(language='TypeScript', file_count=1, sample_files=('ui/app.tsx',)),
        ),
        tool_statuses=(
            ToolStatus(
                name='CodeQL',
                available=True,
                location='/opt/codeql',
                hint='Available at /opt/codeql',
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    codeql_plan = next(plan for plan in plans if plan.tool == 'CodeQL')
    assert codeql_plan.ready is True
    create_command = codeql_plan.steps[0].command
    assert '--language=python' in create_command
    assert '--language=javascript' in create_command
    analyze_steps = [
        step
        for step in codeql_plan.steps
        if 'codeql/javascript-queries' in step.command
    ]
    assert analyze_steps
    output_flag = str(Path('artifacts') / 'codeql-javascript.sarif')
    assert any(output_flag in step.command for step in analyze_steps)


def test_plan_tool_invocations_handles_missing_tool(tmp_path: Path) -> None:
    """Plans should surface hints when analyzers are unavailable."""

    report = AnalysisReport(
        languages=(
            LanguageSummary(language='Python', file_count=1, sample_files=('src/app.py',)),
        ),
        tool_statuses=(
            ToolStatus(
                name='CodeQL',
                available=False,
                location=None,
                hint='Install the CodeQL CLI.',
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    codeql_plan = next(plan for plan in plans if plan.tool == 'CodeQL')
    assert codeql_plan.ready is False
    assert 'Install the CodeQL CLI.' in codeql_plan.reason
    assert codeql_plan.steps


def test_plan_tool_invocations_handles_no_supported_languages(tmp_path: Path) -> None:
    """CodeQL plans should reflect when no supported languages are present."""

    report = AnalysisReport(
        languages=(
            LanguageSummary(language='Markdown', file_count=2, sample_files=('docs/guide.md',)),
        ),
        tool_statuses=(
            ToolStatus(
                name='CodeQL',
                available=True,
                location='/opt/codeql',
                hint='Available at /opt/codeql',
            ),
        ),
        hints=(),
        project_root=tmp_path,
    )

    plans = plan_tool_invocations(report)
    codeql_plan = next(plan for plan in plans if plan.tool == 'CodeQL')
    assert codeql_plan.ready is False
    assert 'No CodeQL-supported languages' in codeql_plan.reason
    assert codeql_plan.steps == ()

"""Tests for the analysis and IR planning helpers."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from emperator.analysis import AnalysisHint, AnalysisReport, detect_languages, gather_analysis
except ModuleNotFoundError:  # pragma: no cover - allow running tests without install
    sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
    from emperator.analysis import AnalysisHint, AnalysisReport, detect_languages, gather_analysis


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

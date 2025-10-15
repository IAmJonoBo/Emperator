"""Repository analysis helpers for IR and tooling readiness."""

from __future__ import annotations

import shutil
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    'AnalysisHint',
    'AnalysisReport',
    'LanguageSummary',
    'AnalyzerCommand',
    'AnalyzerPlan',
    'ToolStatus',
    'detect_languages',
    'gather_analysis',
    'plan_tool_invocations',
]


@dataclass(frozen=True)
class LanguageSummary:
    """Summary of source files detected for a language."""

    language: str
    file_count: int
    sample_files: tuple[str, ...]


@dataclass(frozen=True)
class ToolStatus:
    """Availability of an analyzer or supporting CLI tool."""

    name: str
    available: bool
    location: str | None
    hint: str


@dataclass(frozen=True)
class AnalysisHint:
    """Actionable recommendation produced during analysis planning."""

    topic: str
    guidance: str


@dataclass(frozen=True)
class AnalysisReport:
    """Aggregated view of language coverage and analyzer readiness."""

    languages: tuple[LanguageSummary, ...]
    tool_statuses: tuple[ToolStatus, ...]
    hints: tuple[AnalysisHint, ...]
    project_root: Path | None = None


@dataclass(frozen=True)
class AnalyzerCommand:
    """Concrete command developers can execute for an analyzer."""

    command: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class AnalyzerPlan:
    """Execution plan for a specific analyzer tool."""

    tool: str
    ready: bool
    reason: str
    steps: tuple[AnalyzerCommand, ...]


_LANGUAGE_MAP: dict[str, str] = {
    '.py': 'Python',
    '.pyi': 'Python',
    '.md': 'Markdown',
    '.markdown': 'Markdown',
    '.yaml': 'YAML',
    '.yml': 'YAML',
    '.json': 'JSON',
    '.js': 'JavaScript',
    '.cjs': 'JavaScript',
    '.mjs': 'JavaScript',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
}

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        '.git',
        '.mypy_cache',
        '.ruff_cache',
        '.pytest_cache',
        '.venv',
        'node_modules',
        'dist',
        'build',
        '__pycache__',
        '.tox',
    }
)


@dataclass(frozen=True)
class _ToolRequirement:
    """Configuration for a required analyzer tool."""

    name: str
    binaries: tuple[str, ...]
    guidance: str


_TOOL_REQUIREMENTS: tuple[_ToolRequirement, ...] = (
    _ToolRequirement(
        name='Semgrep',
        binaries=('semgrep',),
        guidance='Install Semgrep to run contract-driven pattern scans (pipx install semgrep).',
    ),
    _ToolRequirement(
        name='CodeQL',
        binaries=('codeql',),
        guidance='Install the CodeQL CLI to enable semantic security analysis.',
    ),
    _ToolRequirement(
        name='Tree-sitter CLI',
        binaries=('tree-sitter',),
        guidance='Install the Tree-sitter CLI to compile grammars for incremental parsing.',
    ),
)

_CODEQL_LANGUAGE_SLUGS: dict[str, str] = {
    'Python': 'python',
    'JavaScript': 'javascript',
    'TypeScript': 'javascript',
}


def _iter_files(project_root: Path) -> Iterable[Path]:
    """Yield project files that should participate in language detection."""

    for path in project_root.rglob('*'):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        yield path


def detect_languages(project_root: Path) -> tuple[LanguageSummary, ...]:
    """Detect languages present in the repository by file extension."""

    counts: dict[str, int] = defaultdict(int)
    samples: dict[str, list[str]] = defaultdict(list)
    for file_path in _iter_files(project_root):
        language = _LANGUAGE_MAP.get(file_path.suffix.lower())
        if not language:
            continue
        counts[language] += 1
        sample_store = samples[language]
        if len(sample_store) < 3:
            sample_store.append(file_path.relative_to(project_root).as_posix())
    summaries = [
        LanguageSummary(
            language=language,
            file_count=counts[language],
            sample_files=tuple(samples[language]),
        )
        for language in sorted(counts)
    ]
    return tuple(summaries)


def _tool_status(requirement: _ToolRequirement) -> ToolStatus:
    """Resolve the availability of a tooling requirement."""

    location: str | None = None
    for binary in requirement.binaries:
        location = shutil.which(binary)
        if location:
            break
    available = location is not None
    hint = requirement.guidance if not available else f'Available at {location}'
    return ToolStatus(
        name=requirement.name,
        available=available,
        location=location,
        hint=hint,
    )


def gather_analysis(project_root: Path) -> AnalysisReport:
    """Build a high-level analysis plan for the repository."""

    languages = detect_languages(project_root)
    tool_statuses = tuple(_tool_status(requirement) for requirement in _TOOL_REQUIREMENTS)

    hints: list[AnalysisHint] = []
    if not languages:
        hints.append(
            AnalysisHint(
                topic='Sources',
                guidance=(
                    'No supported source files detected. Add code or update language mappings.'
                ),
            )
        )
    else:
        detected = ', '.join(summary.language for summary in languages)
        hints.append(
            AnalysisHint(
                topic='IR readiness',
                guidance=f'Languages detected: {detected}',
            )
        )

    for status in tool_statuses:
        if not status.available:
            hints.append(AnalysisHint(topic=status.name, guidance=status.hint))

    return AnalysisReport(
        languages=languages,
        tool_statuses=tool_statuses,
        hints=tuple(hints),
        project_root=project_root,
    )


def _get_tool_status(report: AnalysisReport, tool_name: str) -> ToolStatus | None:
    for status in report.tool_statuses:
        if status.name.lower() == tool_name.lower():
            return status
    return None


def plan_tool_invocations(
    report: AnalysisReport,
    *,
    semgrep_config: str = 'auto',
    codeql_database: Path | str = Path('artifacts') / 'codeql-db',
    codeql_output_dir: Path | str = Path('artifacts'),
) -> tuple[AnalyzerPlan, ...]:
    """Construct a recommended execution plan for supported analyzers."""

    plans: list[AnalyzerPlan] = []
    root = (report.project_root or Path('.')).resolve()

    semgrep_status = _get_tool_status(report, 'Semgrep')
    if semgrep_status is not None:
        location = semgrep_status.location or 'system PATH'
        reason = (
            semgrep_status.hint if not semgrep_status.available else f'Semgrep ready at {location}.'
        )
        semgrep_command = (
            'semgrep',
            'scan',
            f'--config={semgrep_config}',
            '--metrics=off',
            str(root),
        )
        plans.append(
            AnalyzerPlan(
                tool='Semgrep',
                ready=semgrep_status.available,
                reason=reason,
                steps=(
                    AnalyzerCommand(
                        command=semgrep_command,
                        description=(
                            'Run Semgrep with the selected configuration over the repository.'
                        ),
                    ),
                ),
            )
        )

    codeql_status = _get_tool_status(report, 'CodeQL')
    if codeql_status is not None:
        languages = sorted(
            {
                _CODEQL_LANGUAGE_SLUGS[summary.language]
                for summary in report.languages
                if summary.language in _CODEQL_LANGUAGE_SLUGS
            }
        )
        db_path = Path(codeql_database)
        output_dir = Path(codeql_output_dir)
        steps: list[AnalyzerCommand] = []
        if languages:
            create_command: list[str] = [
                'codeql',
                'database',
                'create',
                str(db_path),
                '--source-root',
                str(root),
            ]
            create_command.extend(f'--language={language}' for language in languages)
            steps.append(
                AnalyzerCommand(
                    command=tuple(create_command),
                    description='Create or update the CodeQL database for the detected languages.',
                )
            )
            for language in languages:
                query_pack = f'codeql/{language}-queries'
                output_path = output_dir / f'codeql-{language}.sarif'
                steps.append(
                    AnalyzerCommand(
                        command=(
                            'codeql',
                            'database',
                            'analyze',
                            str(db_path),
                            query_pack,
                            '--format=sarifv2.1.0',
                            '--output',
                            str(output_path),
                        ),
                        description=(
                            'Analyze the CodeQL database with the '
                            f'{language} query pack and emit a SARIF report.'
                        ),
                    )
                )
        ready = codeql_status.available and bool(languages)
        if not codeql_status.available:
            reason = codeql_status.hint
        elif not languages:
            reason = 'No CodeQL-supported languages detected. Add code or adjust mappings.'
        else:
            location = codeql_status.location or 'system PATH'
            reason = f'CodeQL ready at {location}.'
        plans.append(
            AnalyzerPlan(
                tool='CodeQL',
                ready=ready,
                reason=reason,
                steps=tuple(steps),
            )
        )

    return tuple(plans)

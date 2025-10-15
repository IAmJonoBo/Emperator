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
    'ToolStatus',
    'detect_languages',
    'gather_analysis',
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

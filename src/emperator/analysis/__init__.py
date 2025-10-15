"""Repository analysis helpers for IR and tooling readiness."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess  # nosec B404 - subprocess usage limited to analyzer commands
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .codeql import (
    CodeQLDatabase,
    CodeQLFinding,
    CodeQLManager,
    CodeQLManagerError,
    CodeQLUnavailableError,
)
from .correlation import (
    AnalysisFinding,
    CorrelatedFinding,
    CorrelationEngine,
    ExemptionStatus,
    FindingLocation,
)

__all__ = [
    'AnalysisHint',
    'AnalysisReport',
    'LanguageSummary',
    'AnalyzerCommand',
    'AnalyzerPlan',
    'ToolStatus',
    'TelemetryEvent',
    'TelemetryRun',
    'TelemetryStore',
    'InMemoryTelemetryStore',
    'JSONLTelemetryStore',
    'execute_analysis_plan',
    'fingerprint_analysis',
    'detect_languages',
    'gather_analysis',
    'plan_tool_invocations',
    'CodeQLDatabase',
    'CodeQLFinding',
    'CodeQLManager',
    'CodeQLManagerError',
    'CodeQLUnavailableError',
    'AnalysisFinding',
    'FindingLocation',
    'CorrelationEngine',
    'CorrelatedFinding',
    'ExemptionStatus',
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
    severity: str | None = None


@dataclass(frozen=True)
class AnalyzerPlan:
    """Execution plan for a specific analyzer tool."""

    tool: str
    ready: bool
    reason: str
    steps: tuple[AnalyzerCommand, ...]


@dataclass(frozen=True)
class TelemetryEvent:
    """Telemetry emitted for a single analyzer command execution."""

    tool: str
    command: tuple[str, ...]
    exit_code: int
    duration_seconds: float
    timestamp: datetime
    metadata: Mapping[str, str] | None = None

    def to_payload(self) -> dict[str, Any]:
        """Represent the event as a JSON-serialisable payload."""
        return {
            'tool': self.tool,
            'command': list(self.command),
            'exit_code': self.exit_code,
            'duration_seconds': self.duration_seconds,
            'timestamp': self.timestamp.isoformat(),
            'metadata': dict(self.metadata or {}),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> TelemetryEvent:
        """Rehydrate telemetry event metadata from a payload."""
        metadata = payload.get('metadata') or None
        normalized_metadata = None
        if metadata is not None:
            normalized_metadata = {str(key): str(value) for key, value in dict(metadata).items()}
        return cls(
            tool=str(payload['tool']),
            command=tuple(str(part) for part in payload.get('command', ())),
            exit_code=int(payload.get('exit_code', 0)),
            duration_seconds=float(payload.get('duration_seconds', 0.0)),
            timestamp=datetime.fromisoformat(str(payload['timestamp'])),
            metadata=normalized_metadata,
        )


@dataclass(frozen=True)
class TelemetryRun:
    """Aggregated telemetry for a full analyzer execution plan."""

    fingerprint: str
    project_root: Path
    started_at: datetime
    completed_at: datetime
    events: tuple[TelemetryEvent, ...]
    notes: tuple[str, ...] = ()

    @property
    def duration_seconds(self) -> float:
        """Total wall-clock duration for the run."""
        return max(self.completed_at.timestamp() - self.started_at.timestamp(), 0.0)

    @property
    def successful(self) -> bool:
        """Whether all recorded events completed successfully."""
        return all(event.exit_code == 0 for event in self.events)

    def to_payload(self) -> dict[str, Any]:
        """Serialise the telemetry run for persistence."""
        return {
            'fingerprint': self.fingerprint,
            'project_root': str(self.project_root),
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat(),
            'events': [event.to_payload() for event in self.events],
            'notes': list(self.notes),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> TelemetryRun:
        """Reconstruct a telemetry run from a JSON payload."""
        events = tuple(
            TelemetryEvent.from_payload(raw_event) for raw_event in payload.get('events', ())
        )
        return cls(
            fingerprint=str(payload['fingerprint']),
            project_root=Path(str(payload['project_root'])),
            started_at=datetime.fromisoformat(str(payload['started_at'])),
            completed_at=datetime.fromisoformat(str(payload['completed_at'])),
            events=events,
            notes=tuple(str(note) for note in payload.get('notes', ())),
        )


@runtime_checkable
class TelemetryStore(Protocol):
    """Persistence contract for analyzer telemetry runs."""

    def persist(self, run: TelemetryRun) -> None:
        """Persist a telemetry run, making it available for later inspection."""

    def latest(self, fingerprint: str) -> TelemetryRun | None:
        """Return the most recent telemetry run for a fingerprint, if any."""

    def history(self, fingerprint: str) -> tuple[TelemetryRun, ...]:
        """Return the chronological history for a fingerprint."""


class InMemoryTelemetryStore:
    """Simple telemetry persistence suitable for tests and prototyping."""

    def __init__(self) -> None:
        self._runs: dict[str, list[TelemetryRun]] = defaultdict(list)

    def persist(self, run: TelemetryRun) -> None:
        self._runs[run.fingerprint].append(run)

    def latest(self, fingerprint: str) -> TelemetryRun | None:
        history = self._runs.get(fingerprint)
        if not history:
            return None
        return history[-1]

    def history(self, fingerprint: str) -> tuple[TelemetryRun, ...]:
        return tuple(self._runs.get(fingerprint, ()))


class JSONLTelemetryStore:
    """Persist telemetry runs to JSON Lines files on disk."""

    def __init__(self, directory: Path | str, *, max_history: int | None = None) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._max_history = max_history

    def _path_for(self, fingerprint: str) -> Path:
        return self.directory / f'{fingerprint}.jsonl'

    def _read_runs(self, fingerprint: str) -> list[TelemetryRun]:
        path = self._path_for(fingerprint)
        if not path.exists():
            return []
        runs: list[TelemetryRun] = []
        with path.open('r', encoding='utf-8') as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    runs.append(TelemetryRun.from_payload(payload))
                except (KeyError, TypeError, ValueError):
                    continue
        return runs

    def _write_runs(self, fingerprint: str, runs: Iterable[TelemetryRun]) -> None:
        path = self._path_for(fingerprint)
        temp_path = path.with_suffix(path.suffix + '.tmp')
        with temp_path.open('w', encoding='utf-8') as handle:
            for run in runs:
                json.dump(run.to_payload(), handle, sort_keys=True)
                handle.write('\n')
        temp_path.replace(path)

    def persist(self, run: TelemetryRun) -> None:
        history = self._read_runs(run.fingerprint)
        history.append(run)
        if self._max_history is not None:
            history = history[-self._max_history :]
        self._write_runs(run.fingerprint, history)

    def latest(self, fingerprint: str) -> TelemetryRun | None:
        history = self._read_runs(fingerprint)
        if not history:
            return None
        return history[-1]

    def history(self, fingerprint: str) -> tuple[TelemetryRun, ...]:
        return tuple(self._read_runs(fingerprint))


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
    '.jsx': 'JavaScript',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.go': 'Go',
    '.rs': 'Rust',
    '.java': 'Java',
    '.c': 'C',
    '.h': 'C',
    '.cpp': 'C++',
    '.cc': 'C++',
    '.cxx': 'C++',
    '.hpp': 'C++',
    '.hxx': 'C++',
    '.cs': 'C#',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.swift': 'Swift',
    '.kt': 'Kotlin',
    '.kts': 'Kotlin',
    '.sh': 'Shell',
    '.bash': 'Shell',
    '.zsh': 'Shell',
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
        'site',
        '.cache',
        '.sarif',
        '.emperator',
        '.pnpm-store',
        'htmlcov',
        '.hypothesis',
    }
)

RUNNER_EXIT_CODE_ERROR = 'Runner result must expose an exit code via returncode or exit_code.'


def fingerprint_analysis(
    report: AnalysisReport,
    plans: Iterable[AnalyzerPlan],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> str:
    """Compute a deterministic fingerprint for caching analyzer telemetry."""
    metadata = metadata or {}
    root = (report.project_root or Path()).resolve()
    languages = [
        {
            'language': summary.language,
            'file_count': summary.file_count,
            'sample_files': list(summary.sample_files),
        }
        for summary in sorted(report.languages, key=lambda summary: summary.language)
    ]
    tool_statuses = [
        {
            'name': status.name,
            'available': status.available,
            'location': status.location,
        }
        for status in sorted(report.tool_statuses, key=lambda status: status.name)
    ]
    serialized_plans = [
        {
            'tool': plan.tool,
            'ready': plan.ready,
            'reason': plan.reason,
            'steps': [
                {
                    'command': list(step.command),
                    'description': step.description,
                    'severity': step.severity,
                }
                for step in plan.steps
            ],
        }
        for plan in sorted(plans, key=lambda plan: plan.tool)
    ]
    payload = {
        'project_root': str(root),
        'languages': languages,
        'tool_statuses': tool_statuses,
        'plans': serialized_plans,
        'metadata': dict(metadata),
    }
    data = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


@runtime_checkable
class AnalyzerRunner(Protocol):
    """Protocol describing how analyzer commands are executed."""

    def __call__(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None = None,
    ) -> object:
        """Execute a command and return an object exposing an exit code."""


def _default_runner(
    command: tuple[str, ...],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute analyzer commands via subprocess without raising on failure."""
    return subprocess.run(  # nosec B603 - analyzer commands run in controlled contexts  # noqa: S603
        command,
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )


def _extract_exit_code(result: object) -> int:
    """Normalise exit codes from subprocess results or custom runners."""
    if isinstance(result, int):
        return int(result)
    if hasattr(result, 'returncode'):
        return int(result.returncode)
    if hasattr(result, 'exit_code'):
        return int(result.exit_code)
    raise TypeError(RUNNER_EXIT_CODE_ERROR)


def _invoke_runner(
    runner: AnalyzerRunner,
    command: tuple[str, ...],
    *,
    cwd: Path,
) -> tuple[Any, str | None]:
    """Execute a command and capture OSError failures as exit code 127."""
    try:
        return runner(command, cwd=cwd), None
    except OSError as exc:
        message = str(exc)
        result = subprocess.CompletedProcess(
            command,
            returncode=127,
            stdout='',
            stderr=message,
        )
        return result, message


def _run_plan_step(  # noqa: PLR0913
    plan: AnalyzerPlan,
    step: AnalyzerCommand,
    *,
    runner: AnalyzerRunner,
    root: Path,
    time_fn: Callable[[], datetime],
    on_step_start: Callable[[AnalyzerPlan, AnalyzerCommand], None] | None,
    on_step_complete: Callable[[AnalyzerPlan, AnalyzerCommand, int, float], None] | None,
) -> tuple[TelemetryEvent, tuple[str, ...]]:
    """Execute a single analyzer step and return telemetry with notes."""
    if on_step_start is not None:
        on_step_start(plan, step)
    started_at = time_fn()
    result, error_message = _invoke_runner(runner, step.command, cwd=root)
    completed_at = time_fn()
    duration = max((completed_at - started_at).total_seconds(), 0.0)
    exit_code = _extract_exit_code(result)
    event_metadata: dict[str, str] = {'description': step.description}
    if step.severity is not None:
        event_metadata['severity'] = step.severity
    if error_message is not None:
        event_metadata['error'] = error_message
    event = TelemetryEvent(
        tool=plan.tool,
        command=step.command,
        exit_code=exit_code,
        duration_seconds=duration,
        timestamp=completed_at,
        metadata=event_metadata,
    )
    if on_step_complete is not None:
        on_step_complete(plan, step, exit_code, duration)
    notes: list[str] = []
    command_text = ' '.join(step.command)
    if error_message is not None:
        notes.append(f"Failed to launch {plan.tool} command '{command_text}': {error_message}.")
    if exit_code != 0:
        notes.append(f"{plan.tool} command '{command_text}' encountered exit code {exit_code}.")
    return event, tuple(notes)


def _severity_execution_decision(
    step: AnalyzerCommand,
    severity_filter: tuple[str, ...] | None,
    tool: str,
) -> tuple[bool, str | None]:
    """Determine whether a step should be skipped under the severity filter."""
    if not severity_filter:
        return False, None
    severity = step.severity
    if severity is None:
        return False, f"{tool} step '{step.description}' lacks severity metadata; executed."
    if severity.lower() not in severity_filter:
        return True, f"Skipped {tool} step '{step.description}' due to severity filter."
    return False, None


def _prepare_plan_steps(
    plan: AnalyzerPlan,
    *,
    include_unready: bool,
    severity_filter: tuple[str, ...] | None,
) -> tuple[tuple[AnalyzerCommand, ...], tuple[str, ...]]:
    """Return executable steps for a plan along with explanatory notes."""
    notes: list[str] = []
    if not plan.ready:
        if include_unready:
            notes.append(f'Forced execution for {plan.tool}: {plan.reason}')
        else:
            notes.append(f'Skipped {plan.tool}: {plan.reason}')
            return (), tuple(notes)
    if not plan.steps:
        notes.append(f'No steps defined for {plan.tool}.')
        return (), tuple(notes)

    executable: list[AnalyzerCommand] = []
    for step in plan.steps:
        skip_step, severity_note = _severity_execution_decision(step, severity_filter, plan.tool)
        if severity_note is not None:
            notes.append(severity_note)
        if skip_step:
            continue
        executable.append(step)

    if not executable:
        notes.append(f'All steps skipped for {plan.tool} after applying filters.')
    return tuple(executable), tuple(notes)


def execute_analysis_plan(  # noqa: PLR0913
    report: AnalysisReport,
    plans: Iterable[AnalyzerPlan],
    *,
    telemetry_store: TelemetryStore | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_unready: bool = False,
    severity_filter: Iterable[str] | None = None,
    runner: AnalyzerRunner | None = None,
    time_source: Callable[[], datetime] | None = None,
    on_step_start: Callable[[AnalyzerPlan, AnalyzerCommand], None] | None = None,
    on_step_complete: Callable[[AnalyzerPlan, AnalyzerCommand, int, float], None] | None = None,
) -> TelemetryRun:
    """Execute analyzer plans, capture telemetry, and persist run metadata."""
    materialised = tuple(plans)
    time_fn = time_source or (lambda: datetime.now(UTC))
    root = (report.project_root or Path.cwd()).resolve()
    fingerprint = fingerprint_analysis(report, materialised, metadata=metadata)
    runner_fn: AnalyzerRunner = runner or _default_runner
    events: list[TelemetryEvent] = []
    notes: list[str] = []
    started_at = time_fn()

    normalised_filter = (
        tuple(level.lower() for level in severity_filter) if severity_filter is not None else None
    )

    for plan in materialised:
        steps_to_run, plan_notes = _prepare_plan_steps(
            plan,
            include_unready=include_unready,
            severity_filter=normalised_filter,
        )
        notes.extend(plan_notes)
        if not steps_to_run:
            continue
        for step in steps_to_run:
            event, step_notes = _run_plan_step(
                plan,
                step,
                runner=runner_fn,
                root=root,
                time_fn=time_fn,
                on_step_start=on_step_start,
                on_step_complete=on_step_complete,
            )
            events.append(event)
            notes.extend(step_notes)

    completed_at = events[-1].timestamp if events else started_at
    run = TelemetryRun(
        fingerprint=fingerprint,
        project_root=root,
        started_at=started_at,
        completed_at=completed_at,
        events=tuple(events),
        notes=tuple(notes),
    )
    if telemetry_store is not None:
        telemetry_store.persist(run)
    return run


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
    'Java': 'java',
    'C': 'cpp',
    'C++': 'cpp',
    'C#': 'csharp',
    'Go': 'go',
    'Ruby': 'ruby',
    'Swift': 'swift',
    'Kotlin': 'java',
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

    hints.extend(
        AnalysisHint(topic=status.name, guidance=status.hint)
        for status in tool_statuses
        if not status.available
    )

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
    root = (report.project_root or Path()).resolve()

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

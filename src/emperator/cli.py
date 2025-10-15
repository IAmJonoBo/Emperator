"""Developer-focused command line interface for the Emperator workspace."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from . import __version__
from .analysis import (
    AnalysisReport,
    AnalyzerCommand,
    AnalyzerPlan,
    CodeQLManager,
    CodeQLManagerError,
    CodeQLUnavailableError,
    InMemoryTelemetryStore,
    JSONLTelemetryStore,
    TelemetryEvent,
    TelemetryRun,
    TelemetryStore,
    execute_analysis_plan,
    fingerprint_analysis,
    gather_analysis,
    plan_tool_invocations,
)
from .contract import ContractValidationResult, validate_contract_spec
from .doctor import (
    CheckStatus,
    DoctorCheckResult,
    iter_actions,
    run_checks,
    run_remediation,
)
from .scaffolding import ScaffoldAction, ScaffoldStatus, audit_structure, ensure_structure

app = typer.Typer(
    help='Swiss-army knife for Emperator developers and AI copilots.',
    no_args_is_help=False,
)
scaffold_app = typer.Typer(help='Inspect and enforce the documented project layout.')
doctor_app = typer.Typer(help='Diagnose environment health and suggest fixes.')
analysis_app = typer.Typer(help='Plan IR generation and analyzer readiness.')
fix_app = typer.Typer(help='Auto-remediation helpers for common issues.')
contract_app = typer.Typer(help='Inspect and validate the Project Contract assets.')
ir_app = typer.Typer(help='Intermediate Representation (IR) operations for code analysis.')
rules_app = typer.Typer(help='Generate and manage Semgrep and CodeQL rules.')
codeql_app = typer.Typer(help='Manage CodeQL databases and query execution.')

app.add_typer(scaffold_app, name='scaffold')
app.add_typer(doctor_app, name='doctor')
app.add_typer(analysis_app, name='analysis')
app.add_typer(fix_app, name='fix')
app.add_typer(contract_app, name='contract')
app.add_typer(ir_app, name='ir')
app.add_typer(rules_app, name='rules')
analysis_app.add_typer(codeql_app, name='codeql')


_SUPPORTED_SEVERITIES: tuple[str, ...] = (
    'info',
    'low',
    'medium',
    'high',
    'critical',
)

UNSUPPORTED_STORE_MESSAGE = "Unsupported telemetry store. Choose from 'memory', 'jsonl', or 'off'."


ROOT_OPTION = typer.Option(
    None,
    '--root',
    help='Override the project root (defaults to the current working directory).',
    dir_okay=True,
    file_okay=False,
)

TELEMETRY_STORE_OPTION = typer.Option(
    'memory',
    '--telemetry-store',
    help='Telemetry backend to use: memory, jsonl, or off.',
    show_default=False,
)

TELEMETRY_PATH_OPTION = typer.Option(
    None,
    '--telemetry-path',
    help='Directory for telemetry persistence when using the jsonl backend.',
    dir_okay=True,
    file_okay=False,
)

ANALYSIS_TOOL_OPTION = typer.Option(
    None,
    '--tool',
    '-t',
    help='Execute only the specified analyzer (option can be repeated).',
)

ANALYSIS_SEVERITY_OPTION = typer.Option(
    None,
    '--severity',
    '-s',
    help=(
        'Limit execution to analyzer steps that match the selected severities '
        '(option can be repeated).'
    ),
)

INCLUDE_UNREADY_ANALYZERS_OPTION = typer.Option(
    default=False,
    help='Attempt to run analyzers even if prerequisites are missing.',
)
INCLUDE_UNREADY_ANALYZERS_OPTION.param_decls = ('--include-unready',)

SCAFFOLD_DRY_RUN_OPTION = typer.Option(
    default=False,
    help='Preview actions without writing to disk.',
)
SCAFFOLD_DRY_RUN_OPTION.param_decls = ('--dry-run',)

APPLY_OPTION = typer.Option(
    default=False,
    help='Execute recommended remediation commands after the checks.',
)
APPLY_OPTION.param_decls = ('--apply',)

FIX_ONLY_OPTION = typer.Option(
    None,
    '--only',
    help='Name(s) of remediation actions to run; omit to execute the full plan.',
)

FIX_RUN_MODE_OPTION = typer.Option(
    default=True,
    help='Preview the remediation steps; pass --apply to execute them.',
)
FIX_RUN_MODE_OPTION.param_decls = ('--dry-run', '--apply')

STRICT_OPTION = typer.Option(
    default=False,
    help='Treat contract validation warnings as errors.',
)
STRICT_OPTION.param_decls = ('--strict',)

VERSION_OPTION = typer.Option(
    default=False,
    help='Show version and exit.',
)
VERSION_OPTION.param_decls = ('--version', '-v')

CODEQL_LANGUAGE_OPTION = typer.Option(
    'python',
    '--language',
    '-l',
    help='Language for the CodeQL database.',
)

CODEQL_SOURCE_OPTION = typer.Option(
    None,
    '--source',
    '-s',
    help='Source root to index (defaults to the project root).',
    dir_okay=True,
    file_okay=False,
)

CODEQL_FORCE_OPTION = typer.Option(
    default=False,
    help='Overwrite any existing database at the target location.',
)
CODEQL_FORCE_OPTION.param_decls = ('--force',)

CODEQL_DATABASE_OPTION = typer.Option(
    None,
    '--database',
    '-d',
    help='Path to an existing CodeQL database directory.',
    dir_okay=True,
    file_okay=False,
)

CODEQL_QUERIES_OPTION = typer.Option(
    None,
    '--query',
    '-q',
    help='CodeQL query file(s) to execute (option can be repeated).',
    dir_okay=False,
    file_okay=True,
    exists=False,
    show_default=False,
)

CODEQL_OUTPUT_OPTION = typer.Option(
    None,
    '--output',
    '-o',
    help='Optional SARIF output path for query results.',
    dir_okay=True,
    file_okay=True,
)

CODEQL_OLDER_THAN_OPTION = typer.Option(
    None,
    '--older-than',
    help='Remove cached databases older than the provided number of days.',
)

CODEQL_MAX_BYTES_OPTION = typer.Option(
    None,
    '--max-bytes',
    help='Maximum total size of cached databases (bytes) after pruning.',
)

CODEQL_DEFAULT_SARIF = 'analysis.sarif'

RULES_CATEGORY_OPTION = typer.Option(
    None,
    '--category',
    '-c',
    help='Generate rules for a specific category (naming, security, architecture).',
)

RULES_OUTPUT_OPTION = typer.Option(
    None,
    '--output',
    '-o',
    help='Output directory for generated rules.',
    dir_okay=True,
    file_okay=False,
)

RULES_PATH_ARGUMENT = typer.Argument(
    ..., help='Path to Semgrep rules file or directory for validation.'
)


@dataclass
class CLIState:
    """Holds CLI context including project root, console, and telemetry configuration."""

    project_root: Path
    console: Console
    telemetry_store: TelemetryStore | None
    telemetry_path: Path | None


def _get_state(ctx: typer.Context) -> CLIState:
    return ctx.ensure_object(CLIState)


def _resolve_telemetry_path(project_root: Path, target: Path | None) -> Path:
    """Resolve telemetry storage relative to the configured project root."""
    if target is None:
        return (project_root / '.emperator' / 'telemetry').resolve()
    if target.is_absolute():
        return target.resolve()
    return (project_root / target).resolve()


def _resolve_project_path(project_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def _get_codeql_manager(state: CLIState) -> CodeQLManager:
    cache_dir = state.project_root / '.emperator' / 'codeql-cache'
    return CodeQLManager(cache_dir=cache_dir)


def _handle_codeql_error(console: Console, error: Exception) -> None:
    console.print(f'[red]{error}[/]')
    raise typer.Exit(1) from error


def _discover_default_queries(project_root: Path) -> tuple[Path, ...]:
    queries_dir = project_root / 'rules' / 'codeql'
    if not queries_dir.exists():
        return ()
    return tuple(sorted(path.resolve() for path in queries_dir.glob('*.ql')))


def _status_style(status: CheckStatus) -> str:
    return {
        CheckStatus.PASS: 'green',
        CheckStatus.WARN: 'yellow',
        CheckStatus.FAIL: 'red',
    }[status]


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    root: Path | None = ROOT_OPTION,
    telemetry_store: str = TELEMETRY_STORE_OPTION,
    telemetry_path: Path | None = TELEMETRY_PATH_OPTION,
    version: bool = VERSION_OPTION,  # noqa: FBT001
) -> None:
    """Initialise CLI context and greet the user."""
    console = Console()
    if version:
        console.print(f'Emperator CLI version {__version__}')
        raise typer.Exit(0)

    # If invoked without a command, show help
    if ctx.invoked_subcommand is None:
        console.print('[yellow]No command specified. Use --help to see available commands.[/]')
        raise typer.Exit(0)

    project_root = (root or Path.cwd()).resolve()
    store_choice = telemetry_store.lower()
    store: TelemetryStore | None
    resolved_path: Path | None = None
    if telemetry_path is not None and store_choice != 'jsonl':
        message = 'The --telemetry-path option requires the jsonl telemetry store.'
        raise typer.BadParameter(message, param_hint='--telemetry-path')
    if store_choice == 'off':
        store = None
    elif store_choice == 'jsonl':
        resolved_path = _resolve_telemetry_path(project_root, telemetry_path)
        store = JSONLTelemetryStore(resolved_path)
    elif store_choice == 'memory':
        store = InMemoryTelemetryStore()
    else:
        raise typer.BadParameter(UNSUPPORTED_STORE_MESSAGE, param_hint='--telemetry-store')
    ctx.obj = CLIState(
        project_root=project_root,
        console=console,
        telemetry_store=store,
        telemetry_path=resolved_path,
    )
    console.print(
        f'[bold cyan]Emperator CLI[/] v{__version__} — root: [bold]{project_root}[/]',
    )


def _render_scaffold_table(console: Console, statuses: Iterable[ScaffoldStatus]) -> None:
    table = Table(title='Scaffold Status', show_lines=False)
    table.add_column('Path', style='cyan', overflow='fold')
    table.add_column('Description', style='white')
    table.add_column('Exists', justify='center')
    table.add_column('Action', justify='center')
    for status in statuses:
        table.add_row(
            str(status.item.relative_path),
            status.item.description,
            '✅' if status.exists else '❌',
            {
                ScaffoldAction.NONE: '—',
                ScaffoldAction.CREATED: '✨ created',
                ScaffoldAction.PLANNED: '📝 planned',
            }[status.action],
        )
    console.print(table)


@scaffold_app.command('audit')
def scaffold_audit(ctx: typer.Context) -> None:
    """Display which scaffold items still need attention."""
    state = _get_state(ctx)
    statuses = audit_structure(state.project_root)
    _render_scaffold_table(state.console, statuses)


@scaffold_app.command('ensure')
def scaffold_ensure(
    ctx: typer.Context,
    *,
    dry_run: bool = SCAFFOLD_DRY_RUN_OPTION,
) -> None:
    """Create missing directories/files with helpful TODO stubs."""
    state = _get_state(ctx)
    statuses = ensure_structure(state.project_root, dry_run=dry_run)
    planned = [status for status in statuses if status.action is not ScaffoldAction.NONE]
    progress = Progress(
        SpinnerColumn(),
        TextColumn('{task.description}'),
        console=state.console,
    )
    with progress:
        task_id = progress.add_task('Reconciling scaffold', total=len(planned) or None)
        for status in planned:
            progress.update(task_id, description=f'Preparing {status.item.relative_path}')
            progress.advance(task_id)
    _render_scaffold_table(state.console, statuses)
    if dry_run:
        state.console.print(
            '[yellow]Dry run complete. Re-run without --dry-run to materialise the plan.[/]'
        )


def _render_check_table(console: Console, results: Iterable[DoctorCheckResult]) -> None:
    table = Table(title='Environment Checks')
    table.add_column('Check', style='cyan')
    table.add_column('Status', justify='center')
    table.add_column('Message', style='white')
    table.add_column('Remediation', style='magenta')
    for result in results:
        style = _status_style(result.status)
        table.add_row(
            result.name,
            f'[{style}]{result.status.value.upper()}[/]',
            result.message,
            result.remediation or '—',
        )
    console.print(table)


def _render_analysis_report(console: Console, report: AnalysisReport) -> None:
    language_table = Table(title='Analysis Overview', show_lines=False)
    language_table.add_column('Language', style='cyan')
    language_table.add_column('Files', justify='right')
    language_table.add_column('Samples', style='white')
    for summary in report.languages:
        samples = '\n'.join(summary.sample_files) or '—'
        language_table.add_row(summary.language, str(summary.file_count), samples)
    if not report.languages:
        language_table.add_row('—', '0', 'No supported languages detected.')
    console.print(language_table)

    tooling_table = Table(title='Analyzer Tooling', show_lines=False)
    tooling_table.add_column('Tool', style='cyan')
    tooling_table.add_column('Status', justify='center')
    tooling_table.add_column('Details', style='white')
    for status in report.tool_statuses:
        icon = '✅' if status.available else '⚠️'
        style = 'green' if status.available else 'yellow'
        tooling_table.add_row(status.name, f'[{style}]{icon}[/]', status.hint)
    console.print(tooling_table)

    if report.hints:
        hints = '\n'.join(f'- **{hint.topic}:** {hint.guidance}' for hint in report.hints)
        console.print(Panel(Markdown(hints), title='Hints', border_style='cyan'))


def _render_analysis_plan(
    console: Console,
    plans: Iterable[AnalyzerPlan],
    *,
    fingerprint: str,
    telemetry_store: TelemetryStore | None,
    telemetry_path: Path | None,
) -> None:
    materialised = tuple(plans)
    console.print(f'[bold cyan]Telemetry fingerprint:[/] {fingerprint}')
    if telemetry_store is None:
        console.print('[yellow]Telemetry disabled for this session.[/]')
    else:
        latest = telemetry_store.latest(fingerprint)
        if latest is None:
            console.print('[yellow]No telemetry recorded for this plan yet.[/]')
        else:
            status = 'success' if latest.successful else 'issues detected'
            console.print(
                '[cyan]Last run:[/] '
                f'{latest.completed_at.isoformat()} '
                f'({status}, {len(latest.events)} events, {latest.duration_seconds:.2f}s)'
            )
    if telemetry_path is not None:
        console.print(f'[green]Telemetry directory:[/] {telemetry_path}')

    table = Table(title='Analysis Execution Plan', show_lines=False)
    table.add_column('Tool', style='cyan')
    table.add_column('Ready', justify='center')
    table.add_column('Summary', style='white')
    for plan in materialised:
        icon = '✅' if plan.ready else '⚠️'
        style = 'green' if plan.ready else 'yellow'
        table.add_row(plan.tool, f'[{style}]{icon}[/]', plan.reason)
    console.print(table)

    for plan in materialised:
        if not plan.steps:
            continue
        steps_table = Table(title=f'{plan.tool} Steps', show_lines=False)
        steps_table.add_column('Description', style='white')
        steps_table.add_column('Command', style='magenta')
        for step in plan.steps:
            steps_table.add_row(step.description, ' '.join(step.command))
        console.print(steps_table)


def _render_run_telemetry(
    console: Console,
    run: TelemetryRun,
    *,
    telemetry_store: TelemetryStore | None,
    telemetry_path: Path | None,
) -> None:
    """Display telemetry metadata for a completed analysis run."""
    console.print(f'[bold cyan]Telemetry fingerprint:[/] {run.fingerprint}')
    if telemetry_store is None:
        console.print('[yellow]Telemetry disabled for this session.[/]')
    else:
        status = 'success' if run.successful else 'issues detected'
        console.print(
            '[cyan]Run recorded:[/] '
            f'{run.completed_at.isoformat()} '
            f'({len(run.events)} events, {run.duration_seconds:.2f}s, {status})'
        )
    if telemetry_path is not None:
        console.print(f'[green]Telemetry directory:[/] {telemetry_path}')


def _group_events_by_tool(events: Iterable[TelemetryEvent]) -> dict[str, list[TelemetryEvent]]:
    """Index telemetry events by the analyzer tool that emitted them."""
    grouped: dict[str, list[TelemetryEvent]] = {}
    for event in events:
        grouped.setdefault(event.tool, []).append(event)
    return grouped


def _partition_notes_by_tool(
    notes: Iterable[str],
    plans: tuple[AnalyzerPlan, ...],
) -> tuple[dict[str, list[str]], list[str]]:
    """Split notes into per-tool collections and general run guidance."""
    notes_by_tool: dict[str, list[str]] = {}
    general_notes: list[str] = []
    for note in notes:
        matched_tool = next((plan.tool for plan in plans if plan.tool in note), None)
        if matched_tool is None:
            general_notes.append(note)
        else:
            notes_by_tool.setdefault(matched_tool, []).append(note)
    return notes_by_tool, general_notes


_SEVERITY_ORDER: tuple[str, ...] = ('info', 'low', 'medium', 'high', 'critical')
_SEVERITY_RANK: dict[str, int] = {level: index for index, level in enumerate(_SEVERITY_ORDER)}


def _summarise_severities(tool_events: Iterable[TelemetryEvent]) -> tuple[str, str | None]:
    """Summarise severities for a tool, returning display text and highest level."""
    counts: dict[str, int] = {}
    highest: str | None = None
    for event in tool_events:
        metadata = event.metadata
        if metadata is None:
            continue
        severity = metadata.get('severity')
        if not severity:
            continue
        level = severity.lower()
        counts[level] = counts.get(level, 0) + 1
        rank = _SEVERITY_RANK.get(level)
        if rank is None:
            # Treat unknown severities as review material.
            highest = level
            continue
        if highest is None or _SEVERITY_RANK.get(highest, -1) < rank:
            highest = level
    if not counts:
        return '—', None
    ordered_levels = sorted(
        counts,
        key=lambda level: _SEVERITY_RANK.get(level, -1),
        reverse=True,
    )
    display_parts = [
        f'{level} ({counts[level]})' if counts[level] > 1 else level for level in ordered_levels
    ]
    return ', '.join(display_parts), highest


def _severity_gate_status(tool: str, highest: str | None) -> tuple[str, str | None]:
    """Return a Rich-rendered gate badge and optional run-level note."""
    if highest is None:
        return '[green]PASS[/]', None
    level = highest.lower()
    rank = _SEVERITY_RANK.get(level)
    if rank is None:
        unknown_message = (
            'Severity gate triggered for '
            f"{tool}: unknown severity '{highest}' detected; manual review required."
        )
        return '[yellow]REVIEW[/]', unknown_message
    if rank >= _SEVERITY_RANK['high']:
        block_message = (
            'Severity gate triggered for '
            f'{tool}: highest severity {level} requires blocking remediation.'
        )
        return '[red]BLOCK[/]', block_message
    note: str | None
    if rank >= _SEVERITY_RANK['medium']:
        note = (
            'Severity gate triggered for '
            f'{tool}: highest severity {level} requires manual review.'
        )
    else:
        note = None
    badge = '[yellow]REVIEW[/]' if note else '[green]PASS[/]'
    return badge, note


def _render_analysis_run_summary(
    console: Console,
    plans: Iterable[AnalyzerPlan],
    run: TelemetryRun,
) -> None:
    """Render the execution results for each analyzer tool."""
    materialised = tuple(plans)
    events_by_tool = _group_events_by_tool(run.events)
    notes_by_tool, general_notes = _partition_notes_by_tool(run.notes, materialised)

    table = Table(title='Analysis Run Summary', show_lines=False)
    table.add_column('Tool', style='cyan')
    table.add_column('Steps', justify='right')
    table.add_column('Severities', style='white')
    table.add_column('Gate', style='white')
    table.add_column('Result', style='white')
    table.add_column('Details', style='white')

    for plan in materialised:
        tool_events = events_by_tool.get(plan.tool, [])
        stored_notes = notes_by_tool.get(plan.tool)
        tool_notes: list[str] = stored_notes if stored_notes is not None else []
        step_count = len(tool_events)
        severity_display, highest_severity = _summarise_severities(tool_events)
        gate_badge, gate_note = _severity_gate_status(plan.tool, highest_severity)
        if gate_note:
            general_notes.append(gate_note)
        if not tool_events:
            if not plan.steps:
                result = '[yellow]No steps[/]'
                detail = tool_notes[-1] if tool_notes else plan.reason
            else:
                result = '[yellow]Skipped[/]'
                detail = tool_notes[-1] if tool_notes else plan.reason
            steps_display = '0'
        else:
            failures = [event for event in tool_events if event.exit_code != 0]
            steps_display = str(step_count)
            if failures:
                result = '[red]FAILED[/]'
                detail = (
                    '; '.join(tool_notes) if tool_notes else f'{len(failures)} failing step(s).'
                )
            else:
                result = '[green]Success[/]'
                detail = '; '.join(tool_notes) if tool_notes else 'All steps succeeded.'
        table.add_row(plan.tool, steps_display, severity_display, gate_badge, result, detail)

    console.print(table)

    if general_notes:
        console.print(Panel('\n'.join(general_notes), title='Run Notes', border_style='yellow'))


@doctor_app.command('env')
def doctor_env(
    ctx: typer.Context,
    *,
    apply: bool = APPLY_OPTION,
) -> None:
    """Run environment diagnostics and optionally trigger remediations."""
    state = _get_state(ctx)
    results = run_checks(state.project_root)
    _render_check_table(state.console, results)
    if apply:
        state.console.print('[cyan]Applying remediation plan...[/]')
        progress = Progress(
            SpinnerColumn(),
            TextColumn('{task.description}'),
            console=state.console,
        )
        with progress:
            actions = list(iter_actions())
            task_id = progress.add_task('Running fixes', total=len(actions))
            for action in actions:
                progress.update(task_id, description=f'{action.name}')
                completed = run_remediation(action, dry_run=False, cwd=state.project_root)
                progress.advance(task_id)
                if completed and completed.returncode != 0:
                    message = (
                        f"[red]'{' '.join(action.command)}' exited with code "
                        f"{completed.returncode}[/]"
                    )
                    state.console.print(message)
                    if completed.stderr:
                        state.console.print(completed.stderr)
    else:
        state.console.print('[yellow]Use --apply to run the suggested remediation commands.[/]')


@analysis_app.command('inspect')
def analysis_inspect(ctx: typer.Context) -> None:
    """Summarise languages and analyzer readiness with progress feedback."""
    state = _get_state(ctx)
    progress = Progress(
        SpinnerColumn(),
        TextColumn('{task.description}'),
        BarColumn(bar_width=None),
        TimeElapsedColumn(),
        console=state.console,
    )
    with progress:
        task_id = progress.add_task('Detecting repository signals', total=2)
        progress.advance(task_id)
        progress.update(task_id, description='Building analysis report')
        report = gather_analysis(state.project_root)
        progress.advance(task_id)
    _render_analysis_report(state.console, report)


@analysis_app.command('wizard')
def analysis_wizard(ctx: typer.Context) -> None:
    """Guide developers through preparing the IR pipeline."""
    state = _get_state(ctx)
    report = gather_analysis(state.project_root)
    steps: list[str] = []

    if report.languages:
        detected = ', '.join(summary.language for summary in report.languages)
        steps.append(f'Review detected languages: {detected}.')
    else:
        steps.append('No supported languages detected — add source files or adjust mappings.')

    for status in report.tool_statuses:
        if status.available:
            location = status.location or 'system PATH'
            steps.append(f'✅ {status.name} ready at {location}.')
        else:
            steps.append(f'⚠️ {status.name} missing — {status.hint}')

    if report.hints:
        steps.append('Review the detailed hints below for follow-up actions.')

    wizard_lines = '\n'.join(f'{idx}. {text}' for idx, text in enumerate(steps, start=1))
    wizard_panel = Panel(
        Markdown(wizard_lines),
        title='Interactive Analysis Wizard',
        border_style='magenta',
    )
    state.console.print(wizard_panel)

    if report.hints:
        hints = '\n'.join(f'- **{hint.topic}:** {hint.guidance}' for hint in report.hints)
        state.console.print(Markdown(hints))


@analysis_app.command('plan')
def analysis_plan(ctx: typer.Context) -> None:
    """Surface recommended execution steps for analyzers."""
    state = _get_state(ctx)
    report = gather_analysis(state.project_root)
    plans = tuple(plan_tool_invocations(report))
    if not plans:
        state.console.print(
            '[yellow]No analyzer plans available yet. Add supported tooling to the contract.[/]'
        )
        return
    fingerprint = fingerprint_analysis(report, plans, metadata={'command': 'analysis-plan'})
    _render_analysis_plan(
        state.console,
        plans,
        fingerprint=fingerprint,
        telemetry_store=state.telemetry_store,
        telemetry_path=state.telemetry_path,
    )


@analysis_app.command('run')
def analysis_run(
    ctx: typer.Context,
    *,
    tool: list[str] | None = ANALYSIS_TOOL_OPTION,
    severity: list[str] | None = ANALYSIS_SEVERITY_OPTION,
    include_unready: bool = INCLUDE_UNREADY_ANALYZERS_OPTION,
) -> None:
    """Execute analyzer plans, stream progress, and record telemetry."""
    state = _get_state(ctx)
    report = gather_analysis(state.project_root)
    plans = tuple(plan_tool_invocations(report))
    if not plans:
        state.console.print(
            '[yellow]No analyzer plans available yet. Add supported tooling to the contract.[/]'
        )
        return

    selected_tools = {name.lower() for name in (tool or ())}
    if selected_tools:
        selected_plans = tuple(plan for plan in plans if plan.tool.lower() in selected_tools)
    else:
        selected_plans = plans

    if not selected_plans:
        state.console.print('[yellow]No analyzer plans matched the provided filters.[/]')
        return

    severity_values = tuple(value.lower() for value in (severity or ()))
    unique_severities = tuple(dict.fromkeys(severity_values))
    invalid_severities = sorted(
        {level for level in unique_severities if level not in _SUPPORTED_SEVERITIES}
    )
    if invalid_severities:
        supported = ', '.join(_SUPPORTED_SEVERITIES)
        levels = ', '.join(invalid_severities)
        message = f'Unsupported severity level(s): {levels}. ' f'Supported levels: {supported}.'
        raise typer.BadParameter(message, param_hint='--severity')

    executable_steps = sum(
        len(plan.steps) for plan in selected_plans if plan.ready or include_unready
    )
    metadata: dict[str, Any] = {'command': 'analysis-run', 'include_unready': include_unready}
    if selected_tools:
        metadata['tools'] = sorted(selected_tools)
    if unique_severities:
        metadata['severity_filter'] = list(unique_severities)

    progress = Progress(
        SpinnerColumn(),
        TextColumn('{task.description}'),
        BarColumn(bar_width=None),
        TimeElapsedColumn(),
        console=state.console,
    )
    task_label = 'Executing analyzer steps' if executable_steps else 'No executable steps detected'
    with progress:
        task_id = progress.add_task(task_label, total=executable_steps or None)

        def handle_start(plan: AnalyzerPlan, command: AnalyzerCommand) -> None:
            progress.update(
                task_id,
                description=f'Running {plan.tool}: {" ".join(command.command)}',
            )

        def handle_complete(
            plan: AnalyzerPlan,
            command: AnalyzerCommand,
            exit_code: int,
            duration: float,
        ) -> None:
            del plan, command, exit_code, duration
            progress.advance(task_id)

        run = execute_analysis_plan(
            report,
            selected_plans,
            telemetry_store=state.telemetry_store,
            metadata=metadata,
            include_unready=include_unready,
            severity_filter=unique_severities or None,
            on_step_start=handle_start if executable_steps else None,
            on_step_complete=handle_complete if executable_steps else None,
        )
        progress.update(
            task_id,
            description='Analyzer execution complete',
            completed=executable_steps or 0,
        )

    _render_run_telemetry(
        state.console,
        run,
        telemetry_store=state.telemetry_store,
        telemetry_path=state.telemetry_path,
    )
    _render_analysis_run_summary(state.console, selected_plans, run)


@codeql_app.command('create')
def analysis_codeql_create(
    ctx: typer.Context,
    *,
    language: str = CODEQL_LANGUAGE_OPTION,
    source: Path | None = CODEQL_SOURCE_OPTION,
    force: bool = CODEQL_FORCE_OPTION,
) -> None:
    """Create or refresh a CodeQL database for the repository."""
    state = _get_state(ctx)
    manager = _get_codeql_manager(state)
    source_root = (
        _resolve_project_path(state.project_root, source) if source else state.project_root
    )

    try:
        database = asyncio.run(
            manager.create_database(source_root=source_root, language=language, force=force)
        )
    except (CodeQLUnavailableError, CodeQLManagerError) as error:
        _handle_codeql_error(state.console, error)
        return

    message = (
        f'[green]Database ready[/] → [bold]{database.path}[/]\n'
        f'Language: [cyan]{database.language}[/]\n'
        f'Fingerprint: {database.fingerprint}\n'
        f'Size: {database.size_bytes:,} bytes'
    )
    state.console.print(Panel.fit(message, title='CodeQL'))


@codeql_app.command('query')
def analysis_codeql_query(
    ctx: typer.Context,
    *,
    database: Path | None = CODEQL_DATABASE_OPTION,
    query: list[Path] | None = CODEQL_QUERIES_OPTION,
    output: Path | None = CODEQL_OUTPUT_OPTION,
) -> None:
    """Execute CodeQL queries and report findings."""
    state = _get_state(ctx)
    if database is None:
        message = 'A database path is required.'
        raise typer.BadParameter(message, param_hint='--database')

    manager = _get_codeql_manager(state)
    db_path = _resolve_project_path(state.project_root, database)
    try:
        metadata = manager.load_database(db_path)
    except CodeQLManagerError as error:
        _handle_codeql_error(state.console, error)
        return

    selected_queries: list[Path] = list(query or [])
    if not selected_queries:
        selected_queries = list(_discover_default_queries(state.project_root))
        if not selected_queries:
            state.console.print(
                '[yellow]No queries specified and none discovered under rules/codeql.[/]'
            )
            raise typer.Exit(1)

    resolved_queries = tuple(
        _resolve_project_path(state.project_root, query_path) for query_path in selected_queries
    )
    sarif_output = _resolve_project_path(state.project_root, output) if output is not None else None

    try:
        findings = asyncio.run(
            manager.run_queries(metadata, resolved_queries, sarif_output=sarif_output)
        )
    except (CodeQLUnavailableError, CodeQLManagerError) as error:
        _handle_codeql_error(state.console, error)
        return

    if findings:
        table = Table(title='CodeQL Findings', show_lines=False)
        table.add_column('Rule', style='cyan')
        table.add_column('Severity', style='magenta')
        table.add_column('Location', style='white', overflow='fold')
        for finding in findings:
            severity = finding.severity or 'info'
            location = '—'
            if finding.file_path:
                line = finding.start_line or 0
                location = f'{finding.file_path}:{line}'
            table.add_row(finding.rule_id or '—', severity, location)
        state.console.print(table)
    else:
        state.console.print('[green]CodeQL did not report any findings.[/]')

    sarif_path = sarif_output or (metadata.path / CODEQL_DEFAULT_SARIF).resolve()
    state.console.print(f'SARIF output: [bold]{sarif_path}[/]')


@codeql_app.command('list')
def analysis_codeql_list(ctx: typer.Context) -> None:
    """List cached CodeQL databases."""
    state = _get_state(ctx)
    manager = _get_codeql_manager(state)
    databases = manager.list_databases()
    if not databases:
        state.console.print('[yellow]No cached CodeQL databases found.[/]')
        return

    table = Table(title='Cached CodeQL Databases', show_lines=False)
    table.add_column('Language', style='cyan')
    table.add_column('Fingerprint', style='magenta')
    table.add_column('Created', style='green')
    table.add_column('Size (bytes)', justify='right')
    table.add_column('Path', style='white', overflow='fold')

    for db in databases:
        table.add_row(
            db.language,
            db.fingerprint[:12],
            db.created_at.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z'),
            f'{db.size_bytes:,}',
            str(db.path),
        )

    state.console.print(table)


@codeql_app.command('prune')
def analysis_codeql_prune(
    ctx: typer.Context,
    *,
    older_than: int | None = CODEQL_OLDER_THAN_OPTION,
    max_bytes: int | None = CODEQL_MAX_BYTES_OPTION,
) -> None:
    """Remove stale CodeQL databases from the cache."""
    if older_than is None and max_bytes is None:
        message = 'Provide --older-than or --max-bytes to prune the cache.'
        raise typer.BadParameter(message)
    if older_than is not None and older_than < 0:
        message = 'older-than must be non-negative.'
        raise typer.BadParameter(message, param_hint='--older-than')
    if max_bytes is not None and max_bytes < 0:
        message = 'max-bytes must be non-negative.'
        raise typer.BadParameter(message, param_hint='--max-bytes')

    state = _get_state(ctx)
    manager = _get_codeql_manager(state)
    removed = manager.prune(older_than_days=older_than, max_total_bytes=max_bytes)
    if not removed:
        state.console.print('[green]No cached databases matched the prune criteria.[/]')
        return

    table = Table(title='Pruned CodeQL Databases', show_header=False)
    table.add_column('Removed', style='red', overflow='fold')
    for path in removed:
        table.add_row(str(path))
    state.console.print(table)


def _render_validation_summary(console: Console, result: ContractValidationResult) -> None:
    if result.warnings:
        warning_table = Table(title='Contract validation warnings', show_header=False)
        warning_table.add_column('Warning', style='yellow', overflow='fold')
        for warning in result.warnings:
            warning_table.add_row(warning)
        console.print(warning_table)


@contract_app.command('validate')
def contract_validate(
    ctx: typer.Context,
    *,
    strict: bool = STRICT_OPTION,
) -> None:
    """Validate the canonical Project Contract specification."""
    state = _get_state(ctx)
    result = validate_contract_spec(strict=strict)
    console = state.console
    if result.is_valid:
        console.print(Panel('[green]Contract validation passed.[/]', border_style='green'))
        _render_validation_summary(console, result)
        return

    error_table = Table(title='Contract validation errors', show_header=False)
    error_table.add_column('Error', style='red', overflow='fold')
    for message in result.errors:
        error_table.add_row(message)
    console.print(error_table)
    if not strict:
        _render_validation_summary(console, result)
    raise typer.Exit(code=1)


@fix_app.command('plan')
def fix_plan(ctx: typer.Context) -> None:
    """List the available remediation commands."""
    state = _get_state(ctx)
    table = Table(title='Auto-remediation Plan')
    table.add_column('Name', style='cyan')
    table.add_column('Command', style='white')
    table.add_column('Description', style='magenta')
    for action in iter_actions():
        table.add_row(action.name, ' '.join(action.command), action.description)
    state.console.print(table)


@fix_app.command('run')
def fix_run(
    ctx: typer.Context,
    *,
    only: list[str] | None = FIX_ONLY_OPTION,
    dry_run: bool = FIX_RUN_MODE_OPTION,
) -> None:
    """Execute the remediation plan with optional filtering."""
    state = _get_state(ctx)
    selected = [action for action in iter_actions() if not only or action.name in only]
    if not selected:
        state.console.print('[yellow]No remediation actions matched the selection.[/]')
        return

    progress = Progress(
        SpinnerColumn(),
        TextColumn('{task.description}'),
        console=state.console,
    )
    with progress:
        task_id = progress.add_task('Executing remediation plan', total=len(selected))
        for action in selected:
            progress.update(task_id, description=action.name)
            result = run_remediation(action, dry_run=dry_run, cwd=state.project_root)
            progress.advance(task_id)
            if result and result.returncode != 0:
                message = (
                    f"[red]Command '{' '.join(action.command)}' exited with {result.returncode}[/]"
                )
                state.console.print(message)
                if result.stderr:
                    state.console.print(result.stderr)
    if dry_run:
        state.console.print('[yellow]Dry run complete. Re-run with --apply to make changes.[/]')


# ┌────────────────────────────────────────────────────────────────────────┐
# │ IR Commands                                                            │
# └────────────────────────────────────────────────────────────────────────┘


@ir_app.command('parse')
def ir_parse(
    ctx: typer.Context,
    language: str = typer.Option(
        'python',
        '--language',
        '-l',
        help='Programming language to parse (python, javascript, etc.).',
    ),
) -> None:
    """Parse source files and build IR cache.

    This command parses source files in the specified language and builds
    an intermediate representation (IR) cache for fast incremental analysis.
    """
    state = _get_state(ctx)
    state.console.print(f'[bold]Parsing {language} files in {state.project_root}[/]')

    try:
        from emperator.ir import CacheManager, IRBuilder

        cache_dir = state.project_root / '.emperator' / 'ir-cache'
        builder = IRBuilder(cache_dir=cache_dir)
        snapshot = builder.parse_directory(state.project_root, languages=(language,))

        # Save to cache
        manager = CacheManager(cache_dir)
        manager.save_snapshot(snapshot)

        state.console.print(
            f'[green]✓[/] Parsed {snapshot.total_files} files '
            f'in {snapshot.parse_time_seconds:.2f}s'
        )
        state.console.print(f'  Cache hit rate: {snapshot.cache_hit_rate:.1f}%')
        if snapshot.files_with_errors > 0:
            state.console.print(
                f'  [yellow]⚠[/] {snapshot.files_with_errors} files with syntax errors'
            )

    except ImportError as e:
        state.console.print(f'[red]✗[/] IR dependencies not installed: {e}')
        state.console.print('Install with: uv pip install tree-sitter tree-sitter-python')
        raise typer.Exit(code=1) from None


@ir_app.command('cache')
def ir_cache(
    ctx: typer.Context,
    action: str = typer.Argument(
        'info',
        help='Action to perform: info, prune, or clear',
    ),
    older_than: int = typer.Option(
        30,
        '--older-than',
        help='Days threshold for pruning cache entries',
    ),
) -> None:
    """Manage IR cache.

    Actions:
    - info: Display cache statistics
    - prune: Remove old cache entries
    - clear: Delete all cache data
    """
    state = _get_state(ctx)
    cache_dir = state.project_root / '.emperator' / 'ir-cache'

    if action == 'info':
        if not cache_dir.exists():
            state.console.print('[yellow]No IR cache found[/]')
            return

        try:
            import json

            manifest_path = cache_dir / 'manifest.json'
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                file_count = len(manifest.get('files', {}))
                state.console.print('[bold]IR Cache Statistics[/]')
                state.console.print(f'  Location: {cache_dir}')
                state.console.print(f'  Cached files: {file_count}')
                state.console.print(f'  Version: {manifest.get("version", "unknown")}')
            else:
                state.console.print('[yellow]Cache manifest not found[/]')
        except (OSError, json.JSONDecodeError) as e:
            state.console.print(f'[red]✗[/] Error reading cache: {e}')

    elif action == 'prune':
        try:
            from emperator.ir import CacheManager

            manager = CacheManager(cache_dir)
            removed = manager.prune(older_than_days=older_than)
            state.console.print(f'[green]✓[/] Removed {removed} old cache entries')
        except ImportError as e:
            state.console.print(f'[red]✗[/] IR dependencies not installed: {e}')
            raise typer.Exit(code=1) from None

    elif action == 'clear':
        if cache_dir.exists():
            import shutil

            shutil.rmtree(cache_dir)
            state.console.print('[green]✓[/] Cache cleared')
        else:
            state.console.print('[yellow]No cache to clear[/]')

    else:
        state.console.print(f'[red]✗[/] Unknown action: {action}')
        state.console.print('Valid actions: info, prune, clear')
        raise typer.Exit(code=1)


# ┌────────────────────────────────────────────────────────────────────────┐
# │ Rules Commands                                                         │
# └────────────────────────────────────────────────────────────────────────┘


def _summarise_semgrep_rules(console: Console, rules_path: Path) -> tuple[int, int]:
    import yaml

    if rules_path.is_file():
        files = [rules_path]
    else:
        files = list(rules_path.glob('*.yaml')) + list(rules_path.glob('*.yml'))

    valid_count = 0
    invalid_count = 0

    for file in files:
        try:
            with file.open() as handle:
                data = yaml.safe_load(handle)
        except yaml.YAMLError as error:  # pragma: no cover - exercised via CLI
            console.print(f'[red]✗[/] {file}: YAML error: {error}')
            invalid_count += 1
            continue

        if not isinstance(data, dict) or 'rules' not in data:
            console.print(f'[yellow]⚠[/] {file}: missing "rules" key')
            invalid_count += 1
            continue

        missing_fields = []
        for rule in data.get('rules', []):
            required = ['id', 'message', 'severity', 'languages']
            missing = [field for field in required if field not in rule]
            if missing:
                missing_fields.append((rule.get('id', '<unknown>'), missing))

        if missing_fields:
            for rule_id, missing in missing_fields:
                console.print(f'[yellow]⚠[/] {file}: rule {rule_id} missing fields: {missing}')
            invalid_count += 1
            continue

        valid_count += 1
        console.print(f'[green]✓[/] {file}')

    return valid_count, invalid_count


@rules_app.command('generate')
def rules_generate(
    ctx: typer.Context,
    *,
    category: str | None = RULES_CATEGORY_OPTION,
    output: Path | None = RULES_OUTPUT_OPTION,
) -> None:
    """Generate Semgrep rules from contract conventions.

    This command reads your project contract (conventions.cue, policy/*.rego)
    and generates Semgrep rule packs that enforce those conventions.
    """
    state = _get_state(ctx)
    output_dir = output or state.project_root / 'contract' / 'generated' / 'semgrep'

    state.console.print('[bold]Generating Semgrep rules from contract[/]')

    try:
        from emperator.rules import SemgrepRuleGenerator

        generator = SemgrepRuleGenerator()
        all_rules = generator.generate_all_rules()

        if category:
            # Filter by category
            filtered_rules = tuple(r for r in all_rules if r.metadata.get('category') == category)
            if not filtered_rules:
                state.console.print(f'[yellow]No rules found for category: {category}[/]')
                return

            output_file = output_dir / f'{category}.yaml'
            generator.write_rule_pack(filtered_rules, output_file)
            state.console.print(
                f'[green]✓[/] Generated {len(filtered_rules)} {category} rules ' f'to {output_file}'
            )
        else:
            # Generate all categories
            written = generator.write_category_packs(all_rules, output_dir)
            state.console.print(
                f'[green]✓[/] Generated {len(all_rules)} rules in {len(written)} categories:'
            )
            for cat, path in written.items():
                count = len([r for r in all_rules if r.metadata.get('category') == cat])
                state.console.print(f'  - {cat}: {count} rules → {path}')

    except ImportError as e:
        state.console.print(f'[red]✗[/] Failed to import rule generator: {e}')
        raise typer.Exit(code=1) from None


@rules_app.command('validate')
def rules_validate(
    ctx: typer.Context,
    *,
    rules_path: Path = RULES_PATH_ARGUMENT,
) -> None:
    """Validate Semgrep rules syntax.

    This command checks that generated or custom Semgrep rules are valid.
    """
    state = _get_state(ctx)

    def _fail() -> None:
        raise typer.Exit(code=1)

    if not rules_path.exists():
        state.console.print(f'[red]✗[/] Rules path not found: {rules_path}')
        _fail()

    state.console.print(f'[bold]Validating Semgrep rules in {rules_path}[/]')

    try:
        valid_count, invalid_count = _summarise_semgrep_rules(state.console, rules_path)
        state.console.print(
            f'\n[bold]Validation complete:[/] {valid_count} valid, {invalid_count} invalid'
        )
        if invalid_count > 0:
            _fail()
    except ImportError:
        state.console.print('[red]✗[/] Semgrep is not installed or not on PATH.')
        _fail()
    except Exception as error:  # noqa: BLE001
        state.console.print(f'[red]✗[/] Validation failed: {error}')
        _fail()


def run() -> None:
    """Entry point for the CLI script."""
    app()

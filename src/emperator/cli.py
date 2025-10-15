"""Developer-focused command line interface for the Emperator workspace."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from . import __version__
from .analysis import AnalyzerPlan, gather_analysis, plan_tool_invocations
from .doctor import (
    CheckStatus,
    DoctorCheckResult,
    iter_actions,
    run_checks,
    run_remediation,
)
from .scaffolding import ScaffoldAction, ScaffoldStatus, audit_structure, ensure_structure

app = typer.Typer(help='Swiss-army knife for Emperator developers and AI copilots.')
scaffold_app = typer.Typer(help='Inspect and enforce the documented project layout.')
doctor_app = typer.Typer(help='Diagnose environment health and suggest fixes.')
analysis_app = typer.Typer(help='Plan IR generation and analyzer readiness.')
fix_app = typer.Typer(help='Auto-remediation helpers for common issues.')

app.add_typer(scaffold_app, name='scaffold')
app.add_typer(doctor_app, name='doctor')
app.add_typer(analysis_app, name='analysis')
app.add_typer(fix_app, name='fix')


ROOT_OPTION = typer.Option(
    None,
    '--root',
    help='Override the project root (defaults to the current working directory).',
    dir_okay=True,
    file_okay=False,
)

SCAFFOLD_DRY_RUN_OPTION = typer.Option(
    False,
    '--dry-run',
    help='Preview actions without writing to disk.',
)

APPLY_OPTION = typer.Option(
    False,
    '--apply',
    help='Execute recommended remediation commands after the checks.',
)

FIX_ONLY_OPTION = typer.Option(
    None,
    '--only',
    help='Name(s) of remediation actions to run; omit to execute the full plan.',
)

FIX_RUN_MODE_OPTION = typer.Option(
    True,
    '--dry-run/--apply',
    help='Preview the remediation steps; pass --apply to execute them.',
)


@dataclass
class CLIState:
    project_root: Path
    console: Console


def _get_state(ctx: typer.Context) -> CLIState:
    return ctx.ensure_object(CLIState)


def _status_style(status: CheckStatus) -> str:
    return {
        CheckStatus.PASS: 'green',
        CheckStatus.WARN: 'yellow',
        CheckStatus.FAIL: 'red',
    }[status]


@app.callback()
def main(
    ctx: typer.Context,
    root: Path | None = ROOT_OPTION,
) -> None:
    """Initialise CLI context and greet the user."""

    console = Console()
    project_root = (root or Path.cwd()).resolve()
    ctx.obj = CLIState(project_root=project_root, console=console)
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


def _render_analysis_report(console: Console, report) -> None:
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


def _render_analysis_plan(console: Console, plans: Iterable[AnalyzerPlan]) -> None:
    table = Table(title='Analysis Execution Plan', show_lines=False)
    table.add_column('Tool', style='cyan')
    table.add_column('Ready', justify='center')
    table.add_column('Summary', style='white')
    for plan in plans:
        icon = '✅' if plan.ready else '⚠️'
        style = 'green' if plan.ready else 'yellow'
        table.add_row(plan.tool, f'[{style}]{icon}[/]', plan.reason)
    console.print(table)

    for plan in plans:
        if not plan.steps:
            continue
        steps_table = Table(title=f'{plan.tool} Steps', show_lines=False)
        steps_table.add_column('Description', style='white')
        steps_table.add_column('Command', style='magenta')
        for step in plan.steps:
            steps_table.add_row(step.description, ' '.join(step.command))
        console.print(steps_table)


@doctor_app.command('env')
def doctor_env(
    ctx: typer.Context,
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
                        f'{completed.returncode}[/]'
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
    plans = plan_tool_invocations(report)
    if not plans:
        state.console.print(
            '[yellow]No analyzer plans available yet. Add supported tooling to the contract.[/]'
        )
        return
    _render_analysis_plan(state.console, plans)


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


def run() -> None:
    """Entry point for the CLI script."""

    app()

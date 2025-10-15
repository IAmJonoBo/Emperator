"""Integration tests for the developer CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

try:
    from emperator import cli as cli_module
    from emperator.cli import app
    from emperator.doctor import RemediationAction
except ModuleNotFoundError:  # pragma: no cover - allow running tests without install
    sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
    from emperator import cli as cli_module
    from emperator.cli import app
    from emperator.doctor import RemediationAction

runner = CliRunner()


def test_cli_scaffold_ensure_creates_structure(tmp_path: Path) -> None:
    """Scaffold ensure should create the expected policy file."""
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'scaffold', 'ensure'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    policy_path = tmp_path / 'contract' / 'policy' / 'policy.rego'
    assert policy_path.exists()
    assert 'TODO' in policy_path.read_text(encoding='utf-8')


def test_cli_scaffold_audit_reports_missing(tmp_path: Path) -> None:
    """Scaffold audit should report missing assets."""
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'scaffold', 'audit'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert 'policy.rego' in result.stdout


def test_cli_scaffold_ensure_dry_run(tmp_path: Path) -> None:
    """Dry-run ensure should not write to disk."""
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'scaffold', 'ensure', '--dry-run'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert 'Dry run complete' in result.stdout
    assert not (tmp_path / 'contract').exists()


def test_cli_doctor_env_reports_status(tmp_path: Path) -> None:
    """Doctor env should report bootstrap status."""
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'doctor', 'env'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert 'Environment Checks' in result.stdout
    assert 'Tooling bootstrap' in result.stdout


def test_cli_fix_plan_lists_actions() -> None:
    """Fix plan should list available remediation actions."""
    result = runner.invoke(app, ['fix', 'plan'], env={'NO_COLOR': '1'})
    assert result.exit_code == 0, result.stdout
    assert 'Auto-remediation Plan' in result.stdout
    assert 'Sync Python tooling' in result.stdout


def test_cli_doctor_env_apply_runs_remediations(monkeypatch, tmp_path: Path) -> None:
    """Doctor env apply should execute remediation actions."""
    actions = (RemediationAction('Sample', ('echo', 'sample'), 'desc'),)
    executed: list[tuple[RemediationAction, bool, Path | None]] = []

    monkeypatch.setattr(cli_module, 'iter_actions', lambda: actions)

    def fake_run(action: RemediationAction, dry_run: bool = True, cwd: Path | None = None):
        executed.append((action, dry_run, cwd))
        return SimpleNamespace(returncode=0, stderr='')

    monkeypatch.setattr(cli_module, 'run_remediation', fake_run)
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'doctor', 'env', '--apply'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert executed and executed[0][1] is False


def test_cli_doctor_env_apply_handles_failure(monkeypatch, tmp_path: Path) -> None:
    """Doctor env apply should surface remediation failures."""
    action = RemediationAction('Fail', ('echo', 'fail'), 'desc')
    monkeypatch.setattr(cli_module, 'iter_actions', lambda: (action,))

    def fake_run(action: RemediationAction, dry_run: bool = True, cwd: Path | None = None):
        del action, dry_run, cwd
        return SimpleNamespace(returncode=1, stderr='boom')

    monkeypatch.setattr(cli_module, 'run_remediation', fake_run)
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'doctor', 'env', '--apply'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert 'exited with code 1' in result.stdout
    assert 'boom' in result.stdout


def test_cli_fix_run_handles_filters(monkeypatch, tmp_path: Path) -> None:
    """Fix run should respect the --only filter when applying."""
    actions = (
        RemediationAction('A', ('echo', 'a'), 'desc'),
        RemediationAction('B', ('echo', 'b'), 'desc'),
    )
    outputs: list[str] = []

    monkeypatch.setattr(cli_module, 'iter_actions', lambda: actions)

    def fake_run(action: RemediationAction, dry_run: bool = True, cwd: Path | None = None):
        del dry_run, cwd
        outputs.append(action.name)
        return SimpleNamespace(returncode=0, stderr='')

    monkeypatch.setattr(cli_module, 'run_remediation', fake_run)
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'fix', 'run', '--only', 'B', '--apply'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert outputs == ['B']


def test_cli_fix_run_reports_no_match(monkeypatch, tmp_path: Path) -> None:
    """Fix run should report when no actions match filters."""
    monkeypatch.setattr(cli_module, 'iter_actions', lambda: ())
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'fix', 'run', '--only', 'missing'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert 'No remediation actions matched' in result.stdout


def test_cli_fix_run_handles_failure(monkeypatch, tmp_path: Path) -> None:
    """Fix run should report remediation command failures."""
    action = RemediationAction('Broken', ('echo', 'broken'), 'desc')
    monkeypatch.setattr(cli_module, 'iter_actions', lambda: (action,))

    def fake_run(action: RemediationAction, dry_run: bool = True, cwd: Path | None = None):
        del action, dry_run, cwd
        return SimpleNamespace(returncode=2, stderr='fail whale')

    monkeypatch.setattr(cli_module, 'run_remediation', fake_run)
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'fix', 'run', '--apply'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert 'exited with 2' in result.stdout
    assert 'fail whale' in result.stdout


def test_cli_fix_run_dry_run_message(monkeypatch, tmp_path: Path) -> None:
    """Fix run dry-run should explain no commands were executed."""
    action = RemediationAction('Dry', ('echo', 'dry'), 'desc')
    monkeypatch.setattr(cli_module, 'iter_actions', lambda: (action,))

    def fake_run(action: RemediationAction, dry_run: bool = True, cwd: Path | None = None):
        del action, dry_run, cwd
        return SimpleNamespace(returncode=0, stderr='')

    monkeypatch.setattr(cli_module, 'run_remediation', fake_run)
    result = runner.invoke(
        app,
        ['--root', str(tmp_path), 'fix', 'run'],
        env={'NO_COLOR': '1'},
    )
    assert result.exit_code == 0, result.stdout
    assert 'Dry run complete' in result.stdout


def test_cli_run_entry_point_invokes_app(monkeypatch) -> None:
    """CLI module run function should invoke Typer app."""
    called: dict[str, bool] = {}

    def fake_app() -> None:
        called['invoked'] = True

    monkeypatch.setattr(cli_module, 'app', fake_app)
    cli_module.run()
    assert called.get('invoked') is True

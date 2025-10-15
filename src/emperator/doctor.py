"""Environment health checks and auto-remediation helpers."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CheckStatus(Enum):
    """Outcome of a doctor check."""

    # Status strings are UI labels, not secrets.
    PASS = 'pass'  # nosec B105
    WARN = 'warn'
    FAIL = 'fail'


@dataclass(frozen=True)
class DoctorCheckResult:
    """Represents the outcome of a single validation."""

    name: str
    status: CheckStatus
    message: str
    remediation: str | None = None


@dataclass(frozen=True)
class RemediationAction:
    """Describes a fix that can be executed (optionally in dry-run mode)."""

    name: str
    command: Sequence[str]
    description: str


def _python_version_check(minimum: tuple[int, int]) -> DoctorCheckResult:
    version = sys.version_info
    current = f'{version.major}.{version.minor}.{version.micro}'
    target = f'{minimum[0]}.{minimum[1]}'
    if (version.major, version.minor) >= minimum:
        return DoctorCheckResult(
            name='Python runtime',
            status=CheckStatus.PASS,
            message=f'Python {current} detected (>= {target}).',
        )
    return DoctorCheckResult(
        name='Python runtime',
        status=CheckStatus.FAIL,
        message=f'Python {current} is below required {target}.',
        remediation='Upgrade the interpreter used for development and CI runs.',
    )


def _virtualenv_check(project_root: Path) -> DoctorCheckResult:
    venv = project_root / '.venv'
    if venv.exists():
        return DoctorCheckResult(
            name='Virtualenv',
            status=CheckStatus.PASS,
            message=f'Detected virtual environment at {venv}.',
        )
    return DoctorCheckResult(
        name='Virtualenv',
        status=CheckStatus.WARN,
        message='No managed virtual environment was found.',
        remediation='Run `./scripts/setup-tooling.sh` to create and populate .venv.',
    )


def _pnpm_check() -> DoctorCheckResult:
    pnpm = shutil.which('pnpm')
    if pnpm:
        return DoctorCheckResult(
            name='pnpm availability',
            status=CheckStatus.PASS,
            message=f'pnpm detected at {pnpm}.',
        )
    return DoctorCheckResult(
        name='pnpm availability',
        status=CheckStatus.WARN,
        message='pnpm is not on PATH.',
        remediation='Install pnpm to manage JavaScript tooling (see https://pnpm.io/installation).',
    )


def _uv_check() -> DoctorCheckResult:
    uv = shutil.which('uv')
    if uv:
        return DoctorCheckResult(
            name='uv CLI availability',
            status=CheckStatus.PASS,
            message=f'uv detected at {uv}.',
        )
    return DoctorCheckResult(
        name='uv CLI availability',
        status=CheckStatus.WARN,
        message='uv CLI is not on PATH.',
        remediation='Install uv to manage Python environments (https://github.com/astral-sh/uv).',
    )


def _script_check(project_root: Path, script_name: str, description: str) -> DoctorCheckResult:
    script_path = project_root / 'scripts' / script_name
    if script_path.exists():
        return DoctorCheckResult(
            name=description,
            status=CheckStatus.PASS,
            message=f'Found {script_path}.',
        )
    return DoctorCheckResult(
        name=description,
        status=CheckStatus.FAIL,
        message=f'Missing expected helper script: {script_path}.',
        remediation='Restore the helper script or regenerate it from project templates.',
    )


def run_checks(project_root: Path) -> list[DoctorCheckResult]:
    """Execute all standard doctor checks."""

    checks = [
        _python_version_check((3, 11)),
        _virtualenv_check(project_root),
        _pnpm_check(),
        _uv_check(),
        _script_check(project_root, 'setup-tooling.sh', 'Tooling bootstrap script'),
    ]
    return checks


def default_remediations() -> tuple[RemediationAction, ...]:
    """Provide the default remediation plan developers can opt into."""

    return (
        RemediationAction(
            name='Sync Python tooling',
            command=('bash', 'scripts/setup-tooling.sh'),
            description='Create the local virtual environment and install dev dependencies.',
        ),
        RemediationAction(
            name='Install lint hooks',
            command=('bash', 'scripts/setup-linting.sh'),
            description='Refresh linting configuration and git hooks.',
        ),
        RemediationAction(
            name='Install JS toolchain',
            command=('pnpm', 'install'),
            description='Ensure Node-based developer tooling is installed.',
        ),
    )


def run_remediation(
    action: RemediationAction,
    *,
    dry_run: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str] | None:
    """Execute a remediation action if not in dry-run mode."""

    if dry_run:
        return None
    # Commands are curated remediation steps and never accept untrusted input.
    try:
        return subprocess.run(  # nosec B603
            action.command,
            cwd=cwd,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            action.command,
            returncode=127,
            stdout='',
            stderr=str(exc),
        )


def iter_actions(actions: Iterable[RemediationAction] | None = None) -> Iterable[RemediationAction]:
    """Iterate over the remediation actions, defaulting to the curated plan."""

    if actions is None:
        actions = default_remediations()
    return actions

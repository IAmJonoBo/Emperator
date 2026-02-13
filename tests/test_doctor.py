"""Unit tests for the doctor utilities."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace

import pytest

from emperator import doctor


def test_python_version_check_handles_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    result = doctor._python_version_check((99, 0))
    assert result.status is doctor.CheckStatus.FAIL
    assert "below required" in result.message


def test_virtualenv_check_pass(tmp_path: Path) -> None:
    venv_path = tmp_path / ".venv"
    venv_path.mkdir()
    result = doctor._virtualenv_check(tmp_path)
    assert result.status is doctor.CheckStatus.PASS


def test_pnpm_check_warns_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    result = doctor._pnpm_check()
    assert result.status is doctor.CheckStatus.WARN


def test_uv_check_warns_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_which(name: str) -> str | None:
        calls.append(name)
        return None

    monkeypatch.setattr(doctor.shutil, "which", fake_which)
    result = doctor._uv_check()
    assert result.status is doctor.CheckStatus.WARN
    assert "uv" in result.message
    assert "Install uv" in (result.remediation or "")
    assert calls == ["uv"]


def test_script_check_success(tmp_path: Path) -> None:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "setup-tooling.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    result = doctor._script_check(
        tmp_path, "setup-tooling.sh", "Tooling bootstrap script"
    )
    assert result.status is doctor.CheckStatus.PASS


def test_run_remediation_executes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    action = doctor.RemediationAction("Echo", ("echo", "hi"), "Say hi")

    def fake_run(
        command: Iterable[str],
        cwd: Path | None,
        check: bool,
        text: bool,
        capture_output: bool,
    ):
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    result = doctor.run_remediation(action, dry_run=False, cwd=tmp_path)
    assert result is not None
    assert result.returncode == 0


def test_run_remediation_handles_missing_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    action = doctor.RemediationAction("Missing", ("missing",), "desc")

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        raise FileNotFoundError("missing executable")

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    result = doctor.run_remediation(action, dry_run=False, cwd=tmp_path)
    assert result is not None
    assert result.returncode == 127
    assert "missing executable" in (result.stderr or "")


def test_run_remediation_dry_run(tmp_path: Path) -> None:
    action = doctor.RemediationAction("Dry", ("echo", "dry"), "desc")
    result = doctor.run_remediation(action, dry_run=True, cwd=tmp_path)
    assert result is None


def test_iter_actions_uses_defaults() -> None:
    actions = list(doctor.iter_actions())
    assert any(action.name == "Sync Python tooling" for action in actions)


def test_run_checks_includes_uv(tmp_path: Path) -> None:
    results = doctor.run_checks(tmp_path)
    assert any(result.name.lower().startswith("uv") for result in results)

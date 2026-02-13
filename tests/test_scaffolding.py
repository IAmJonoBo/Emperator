"""Tests for the scaffolding utilities."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from emperator import scaffolding
    from emperator.scaffolding import (
        ScaffoldAction,
        ScaffoldItem,
        audit_structure,
        ensure_structure,
    )
except (
    ModuleNotFoundError
):  # pragma: no cover - allow running without installing the package
    sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
    from emperator import scaffolding
    from emperator.scaffolding import (
        ScaffoldAction,
        ScaffoldItem,
        audit_structure,
        ensure_structure,
    )


def test_audit_marks_items_missing(tmp_path: Path) -> None:
    """Audit should report missing scaffold assets."""
    statuses = audit_structure(tmp_path)
    # The contract policy file should be missing in a fresh workspace.
    policy_status = next(
        s for s in statuses if "policy.rego" in str(s.item.relative_path)
    )
    assert not policy_status.exists
    assert policy_status.action is ScaffoldAction.NONE


def test_ensure_creates_stub_files(tmp_path: Path) -> None:
    """Ensure action creates scaffold files and stubs."""
    statuses = ensure_structure(tmp_path, dry_run=False)
    policy_path = tmp_path / "contract" / "policy" / "policy.rego"
    semgrep_path = tmp_path / "rules" / "semgrep" / "ruleset.yaml"
    assert policy_path.exists()
    assert "TODO" in policy_path.read_text(encoding="utf-8")
    assert semgrep_path.exists()
    assert "emperator.todo.example" in semgrep_path.read_text(encoding="utf-8")
    # Ensure the status objects capture creation events.
    policy_status = next(
        s for s in statuses if s.item.relative_path.name == "policy.rego"
    )
    assert policy_status.action is ScaffoldAction.CREATED


def test_ensure_respects_existing_assets(tmp_path: Path) -> None:
    """Ensure action does not overwrite existing assets."""
    ensure_structure(tmp_path, dry_run=False)
    statuses = ensure_structure(tmp_path, dry_run=False)
    policy_status = next(
        s for s in statuses if s.item.relative_path.name == "policy.rego"
    )
    assert policy_status.action is ScaffoldAction.NONE
    assert not policy_status.needs_attention


def test_ensure_handles_items_without_stub(tmp_path: Path, monkeypatch) -> None:
    """Items without stub materials should still be created."""
    custom_item = ScaffoldItem(Path("custom.txt"), "Custom without stub", stub=None)

    def fake_iter():
        yield custom_item

    monkeypatch.setattr(scaffolding, "iter_scaffold_items", fake_iter)
    statuses = ensure_structure(tmp_path, dry_run=False)
    target = tmp_path / "custom.txt"
    assert target.exists()
    status = statuses[0]
    assert status.action is ScaffoldAction.CREATED

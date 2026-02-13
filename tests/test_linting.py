import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "lint-changed.mjs"


def run_lint_changed(*args: str) -> subprocess.CompletedProcess[str]:
    command = ["node", str(SCRIPT), *args]
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )


def test_lint_changed_accepts_file_list() -> None:
    """Linting a known-good Python file should succeed without output."""
    result = run_lint_changed("--files", "src/emperator/__init__.py")

    assert result.returncode == 0
    assert "[lint-changed]" in result.stdout


def test_lint_changed_rejects_unknown_option() -> None:
    """Unknown command-line flags should produce a clear error message."""
    result = run_lint_changed("--not-a-real-flag")

    assert result.returncode != 0
    assert "Unknown option" in result.stderr

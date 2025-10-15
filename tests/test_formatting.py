"""End-to-end coverage for local formatting helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAT_SCRIPT = REPO_ROOT / 'scripts' / 'format-yaml.mjs'
RUN_FORMAT_SCRIPT = REPO_ROOT / 'scripts' / 'run-format.mjs'


def _run_yaml_formatter(tmp_path: Path, contents: str, *, env: dict[str, str] | None = None) -> str:
    """Execute the YAML formatter against a temporary project tree."""
    yaml_file = tmp_path / 'sample.yaml'
    yaml_file.write_text(textwrap.dedent(contents).lstrip('\n'), encoding='utf8')

    command = ['node', str(FORMAT_SCRIPT)]
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        formatted_output = completed.stderr or completed.stdout
        raise RuntimeError(
            f'format-yaml failed with exit code {completed.returncode}: {formatted_output}'
        )

    return yaml_file.read_text(encoding='utf8')


@pytest.mark.parametrize('line_width', [88, 100])
def test_yaml_formatter_handles_multidocument_inputs(tmp_path: Path, line_width: int) -> None:
    """Multidocument YAML files should be normalised with consistent indentation."""
    long_sentence = 'Quality gates ' + 'and telemetry ' * 6 + 'must stay enforced.'
    contents = f"""
    ---
    pipeline:
        steps:
            - name: build
              run: echo "hello world"
    ---
    metadata:
      description: "{long_sentence}"
    """

    output = _run_yaml_formatter(
        tmp_path,
        contents,
        env={**os.environ, 'FORMAT_YAML_WIDTH': str(line_width)},
    )

    # Each document is preserved and prefixed by the explicit start marker.
    assert output.count('---\n') == 2

    # Every line should have an even indentation level with two-space multiples.
    lines = output.splitlines()
    lines.append('')
    for line in lines:
        if not line.strip():
            continue
        assert (len(line) - len(line.lstrip())) % 2 == 0

    # The long description must wrap under the configured width.
    assert max(len(line) for line in output.splitlines()) <= line_width + 2


def test_yaml_formatter_respects_environment_configuration(tmp_path: Path) -> None:
    """Indentation and wrapping knobs should be tunable via environment variables."""
    contents = """
    root:
      branch:
        - id: 1
          notes: "{}"
    """.format('process telemetry ' * 4)

    env = {
        **os.environ,
        'FORMAT_YAML_WIDTH': '60',
        'FORMAT_YAML_INDENT': '4',
    }
    output = _run_yaml_formatter(tmp_path, contents, env=env)

    # Nested structures should honour the configured indentation.
    lines = output.splitlines()
    assert any(line.startswith(' ' * 4 + 'branch:') for line in lines)
    assert any(line.startswith(' ' * 8 + '- id:') for line in lines)

    notes_index = next(i for i, line in enumerate(lines) if line.strip().startswith('notes:'))
    assert lines[notes_index + 1].startswith(' ' * 10)

    # Wrapped scalars stay within the configured width.
    assert max(len(line) for line in lines) <= 62


def test_run_format_check_mode_flags_pending_changes(tmp_path: Path) -> None:
    """`pnpm fmt --check` should surface pending edits without mutating files."""
    target_dir = REPO_ROOT / 'tmp_format_fixture'
    target_dir.mkdir(exist_ok=False)
    bad_yaml = target_dir / 'bad.yaml'
    original = 'root:\n    child: value\n'
    bad_yaml.write_text(original, encoding='utf8')

    completed = subprocess.run(
        ['node', str(RUN_FORMAT_SCRIPT), '--check'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    preserved = bad_yaml.read_text(encoding='utf8')
    shutil.rmtree(target_dir)

    assert completed.returncode != 0
    assert preserved == original
    assert 'bad.yaml' in (completed.stderr + completed.stdout)


def test_run_format_rejects_conflicting_flags() -> None:
    """Conflicting formatter flags should fail fast with a helpful message."""
    completed = subprocess.run(
        ['node', str(RUN_FORMAT_SCRIPT), '--all', '--check'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    combined_output = completed.stderr + completed.stdout
    assert completed.returncode != 0
    assert '--all cannot be combined with --check' in combined_output


def test_yaml_formatter_raises_for_parse_errors(tmp_path: Path) -> None:
    """Surface parse errors so callers can triage malformed YAML quickly."""
    contents = """
    invalid: [
      - missing-bracket
    """

    with pytest.raises(RuntimeError) as exc:
        _run_yaml_formatter(tmp_path, contents)

    message = str(exc.value)
    assert 'format-yaml failed with exit code' in message
    assert 'Block collections are not allowed within flow collections' in message

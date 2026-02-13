import asyncio
import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from emperator.analysis.codeql import (
    CodeQLDatabase,
    CodeQLManager,
    CodeQLManagerError,
    CodeQLUnavailableError,
)


def test_codeql_manager_create_builds_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    manager = CodeQLManager(codeql_path=tmp_path / "codeql", cache_dir=cache_dir)

    calls: list[tuple[tuple[str, ...], Path | None]] = []

    async def fake_run(command: tuple[str, ...], *, cwd: Path | None) -> None:
        calls.append((tuple(command), cwd))

    monkeypatch.setattr(manager, "_run_subprocess", fake_run)
    monkeypatch.setattr(
        manager, "_fingerprint_source", lambda root, lang: "abc123def456"
    )

    source_root = tmp_path / "src"
    source_root.mkdir()
    database = asyncio.run(
        manager.create_database(source_root=source_root, language="python")
    )

    assert calls, "Expected CodeQL CLI invocation"
    assert database.path.exists()
    metadata_path = database.path / "metadata.json"
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["language"] == "python"
    assert metadata["fingerprint"] == "abc123def456"


def test_codeql_manager_create_returns_cached_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    manager = CodeQLManager(codeql_path=tmp_path / "codeql", cache_dir=cache_dir)

    fingerprint = "cachedfingerprint"
    target_dir = cache_dir / f"python-{fingerprint[:12]}"
    target_dir.mkdir(parents=True)

    cached_db = CodeQLDatabase(
        language="python",
        path=target_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=512,
        fingerprint=fingerprint,
    )
    manager.cache_database(cached_db)

    monkeypatch.setattr(manager, "_fingerprint_source", lambda root, lang: fingerprint)

    called: list[SimpleNamespace] = []

    async def fake_run(command: tuple[str, ...], *, cwd: Path | None) -> None:
        del command, cwd
        called.append(SimpleNamespace())

    monkeypatch.setattr(manager, "_run_subprocess", fake_run)

    source_root = tmp_path / "src"
    source_root.mkdir()

    database = asyncio.run(
        manager.create_database(source_root=source_root, language="python")
    )

    assert database == cached_db
    assert not called, "Expected cached metadata to bypass CodeQL invocation"


def test_codeql_manager_create_force_overwrites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    manager = CodeQLManager(codeql_path=tmp_path / "codeql", cache_dir=cache_dir)

    fingerprint = "forcefingerprint"
    target_dir = cache_dir / f"python-{fingerprint[:12]}"
    target_dir.mkdir(parents=True)
    (target_dir / "stale.txt").write_text("stale", encoding="utf-8")

    source_root = tmp_path / "src"
    source_root.mkdir()

    monkeypatch.setattr(manager, "_fingerprint_source", lambda root, lang: fingerprint)

    original_rmtree = shutil.rmtree
    removed: list[Path] = []

    def fake_rmtree(path: Path, ignore_errors: bool = False) -> None:
        removed.append(path)
        original_rmtree(path, ignore_errors=ignore_errors)

    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    collected = CodeQLDatabase(
        language="python",
        path=target_dir,
        source_root=source_root,
        created_at=datetime.now(tz=UTC),
        size_bytes=0,
        fingerprint=fingerprint,
    )

    async def fake_run(command: tuple[str, ...], *, cwd: Path | None) -> None:
        del command, cwd

    monkeypatch.setattr(manager, "_run_subprocess", fake_run)
    monkeypatch.setattr(manager, "_collect_metadata", lambda *args: collected)

    cached: list[CodeQLDatabase] = []
    monkeypatch.setattr(manager, "cache_database", cached.append)

    database = asyncio.run(
        manager.create_database(source_root=source_root, language="python", force=True)
    )

    assert removed and removed[0] == target_dir
    assert database is collected
    assert cached == [collected]


def test_codeql_manager_run_queries_parses_sarif(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    db_dir = cache_dir / "python-abcdef123456"
    db_dir.mkdir(parents=True)

    manager = CodeQLManager(codeql_path=tmp_path / "codeql", cache_dir=cache_dir)
    database = CodeQLDatabase(
        language="python",
        path=db_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=0,
        fingerprint="abcdef123456",
    )

    async def fake_run(command: tuple[str, ...], *, cwd: Path | None) -> None:
        output_flag = command.index("--output") + 1
        sarif_path = Path(command[output_flag])
        sarif_payload = {
            "runs": [
                {
                    "results": [
                        {
                            "ruleId": "security.test",
                            "message": {"text": "Problem detected"},
                            "properties": {"problem.severity": "error"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "uri": str(tmp_path / "module.py")
                                        },
                                        "region": {"startLine": 12, "startColumn": 4},
                                    }
                                }
                            ],
                        }
                    ]
                }
            ]
        }
        sarif_path.write_text(json.dumps(sarif_payload), encoding="utf-8")

    monkeypatch.setattr(manager, "_run_subprocess", fake_run)

    findings = asyncio.run(manager.run_queries(database, (tmp_path / "query.ql",)))
    assert findings
    finding = findings[0]
    assert finding.rule_id == "security.test"
    assert finding.start_line == 12
    assert finding.file_path and finding.file_path.name == "module.py"


def test_codeql_manager_run_queries_handles_empty_queries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manager = CodeQLManager(
        codeql_path=tmp_path / "codeql", cache_dir=tmp_path / "cache"
    )
    database = CodeQLDatabase(
        language="python",
        path=tmp_path,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=0,
        fingerprint="noop",
    )

    async def fake_run(command: tuple[str, ...], *, cwd: Path | None) -> None:
        del command, cwd
        raise AssertionError("CodeQL should not run when no queries are provided")

    monkeypatch.setattr(manager, "_run_subprocess", fake_run)

    findings = asyncio.run(manager.run_queries(database, ()))
    assert findings == ()


def test_codeql_manager_list_and_prune(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    manager = CodeQLManager(codeql_path=tmp_path / "codeql", cache_dir=cache_dir)

    recent_dir = cache_dir / "python-recent"
    recent_dir.mkdir(parents=True)
    recent_db = CodeQLDatabase(
        language="python",
        path=recent_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=256,
        fingerprint="recent",
    )
    manager.cache_database(recent_db)

    old_dir = cache_dir / "python-old"
    old_dir.mkdir(parents=True)
    old_db = CodeQLDatabase(
        language="python",
        path=old_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC) - timedelta(days=10),
        size_bytes=512,
        fingerprint="old",
    )
    manager.cache_database(old_db)

    databases = manager.list_databases()
    assert databases and databases[0].fingerprint == "recent"

    removed = manager.prune(older_than_days=5)
    assert old_dir in removed
    assert not old_dir.exists()

    removed_by_size = manager.prune(max_total_bytes=128)
    assert recent_dir in removed_by_size
    assert not recent_dir.exists()

    replacement_dir = cache_dir / "python-latest"
    replacement_dir.mkdir(parents=True)
    latest_db = CodeQLDatabase(
        language="python",
        path=replacement_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=42,
        fingerprint="latest",
    )
    manager.cache_database(latest_db)
    removed_cache = manager.invalidate_cache(tmp_path, "python")
    assert replacement_dir in removed_cache
    assert not replacement_dir.exists()


def test_codeql_manager_parse_sarif_handles_missing_properties(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    manager = CodeQLManager(codeql_path=tmp_path / "codeql", cache_dir=cache_dir)

    database = CodeQLDatabase(
        language="python",
        path=cache_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=0,
        fingerprint="noop",
    )

    sarif_path = cache_dir / "analysis.sarif"
    sarif_payload = {
        "runs": [
            {
                "results": [
                    {
                        "ruleId": "rule.missing",
                        "message": {"text": "No severity provided"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {},
                                    "region": {},
                                }
                            }
                        ],
                    }
                ]
            }
        ]
    }
    sarif_path.write_text(json.dumps(sarif_payload), encoding="utf-8")

    async def fake_run(command: tuple[str, ...], *, cwd: Path | None) -> None:
        del command, cwd

    monkeypatch.setattr(manager, "_run_subprocess", fake_run)

    findings = asyncio.run(manager.run_queries(database, (tmp_path / "query.ql",)))
    assert findings
    finding = findings[0]
    assert finding.severity is None
    assert finding.file_path is None
    assert finding.start_line is None


def test_codeql_manager_fingerprint_includes_files(tmp_path: Path) -> None:
    manager = CodeQLManager(
        codeql_path=tmp_path / "codeql", cache_dir=tmp_path / "cache"
    )
    source_root = tmp_path / "project"
    source_root.mkdir()
    file_path = source_root / "module.py"
    file_path.write_text('print("hi")\n', encoding="utf-8")

    digest = manager._fingerprint_source(source_root, "python")

    assert len(digest) == 64
    assert list(manager._iter_source_files(source_root)) == [file_path]


def test_codeql_manager_run_queries_returns_empty_when_sarif_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "cache"
    manager = CodeQLManager(codeql_path=tmp_path / "codeql", cache_dir=cache_dir)
    database = CodeQLDatabase(
        language="python",
        path=cache_dir,
        source_root=tmp_path,
        created_at=datetime.now(tz=UTC),
        size_bytes=0,
        fingerprint="noop",
    )

    async def fake_run(command: tuple[str, ...], *, cwd: Path | None) -> None:
        del command, cwd

    monkeypatch.setattr(manager, "_run_subprocess", fake_run)

    findings = asyncio.run(manager.run_queries(database, (tmp_path / "missing.ql",)))
    assert findings == ()


def test_codeql_manager_run_subprocess_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manager = CodeQLManager(
        codeql_path=tmp_path / "codeql", cache_dir=tmp_path / "cache"
    )

    class FakeProcess:
        def __init__(self) -> None:
            self.returncode = 1

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b"failure"

    async def fake_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    with pytest.raises(CodeQLManagerError):
        asyncio.run(manager._run_subprocess(("codeql",), cwd=None))


def test_codeql_manager_run_subprocess_streams_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manager = CodeQLManager(
        codeql_path=tmp_path / "codeql", cache_dir=tmp_path / "cache"
    )

    class FakeProcess:
        def __init__(self) -> None:
            self.returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"stdout", b"stderr"

    async def fake_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args, kwargs
        return FakeProcess()

    writes: list[tuple[int, bytes]] = []

    def fake_write(fd: int, data: bytes) -> int:
        writes.append((fd, data))
        return len(data)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(os, "write", fake_write)

    asyncio.run(manager._run_subprocess(("codeql",), cwd=None))

    assert (1, b"stdout") in writes
    assert (2, b"stderr") in writes


def test_codeql_manager_load_database_missing_manifest(tmp_path: Path) -> None:
    manager = CodeQLManager(
        codeql_path=tmp_path / "codeql", cache_dir=tmp_path / "cache"
    )
    with pytest.raises(CodeQLManagerError):
        manager.load_database(tmp_path / "missing")


def test_codeql_manager_discover_codeql_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = CodeQLManager(cache_dir=Path(".emperator/codeql-cache"))

    monkeypatch.setattr("shutil.which", lambda _: None)

    with pytest.raises(CodeQLUnavailableError):
        manager._ensure_codeql()


def test_codeql_manager_ensure_codeql_discovers_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manager = CodeQLManager(cache_dir=tmp_path / "cache")
    binary_path = tmp_path / "bin" / "codeql"
    binary_path.parent.mkdir(parents=True)
    binary_path.write_text("", encoding="utf-8")

    calls = {"count": 0}

    def fake_which(name: str) -> str:
        calls["count"] += 1
        assert name == "codeql"
        return str(binary_path)

    monkeypatch.setattr("shutil.which", fake_which)

    first = manager._ensure_codeql()
    second = manager._ensure_codeql()

    assert first == binary_path.resolve()
    assert second == binary_path.resolve()
    assert calls["count"] == 1

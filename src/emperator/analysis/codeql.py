"""CodeQL database orchestration utilities."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

METADATA_FILE_NAME = 'metadata.json'
SARIF_FORMAT = 'sarifv2.1.0'
DEFAULT_CACHE_DIR = Path('.emperator/codeql-cache')
DEFAULT_SARIF_NAME = 'analysis.sarif'

__all__ = [
    'CodeQLManager',
    'CodeQLDatabase',
    'CodeQLFinding',
    'CodeQLManagerError',
    'CodeQLUnavailableError',
]


class CodeQLManagerError(RuntimeError):
    """Base exception for CodeQL manager failures."""


class CodeQLUnavailableError(CodeQLManagerError):
    """Raised when the CodeQL CLI is not available on PATH."""


@dataclass(frozen=True)
class CodeQLDatabase:
    """Metadata describing a CodeQL database."""

    language: str
    path: Path
    source_root: Path
    created_at: datetime
    size_bytes: int
    fingerprint: str


@dataclass(frozen=True)
class CodeQLFinding:
    """Subset of SARIF finding details produced by CodeQL."""

    rule_id: str
    message: str
    severity: str | None
    file_path: Path | None
    start_line: int | None
    start_column: int | None
    sarif: dict[str, Any]


class CodeQLManager:
    """Coordinate CodeQL database creation, caching, and query execution."""

    def __init__(
        self,
        *,
        codeql_path: Path | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._codeql_path = codeql_path
        self._cache_dir = (cache_dir or DEFAULT_CACHE_DIR).expanduser().resolve()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        """Return the directory storing cached CodeQL databases."""
        return self._cache_dir

    def _discover_codeql(self) -> Path:
        location = shutil.which('codeql')
        if location is None:
            message = (
                'CodeQL CLI was not found on PATH. '
                'Install CodeQL and ensure the binary is discoverable.'
            )
            raise CodeQLUnavailableError(message)
        return Path(location).resolve()

    async def create_database(
        self,
        source_root: Path,
        language: str,
        *,
        output: Path | None = None,
        force: bool = False,
        extra_args: Sequence[str] = (),
    ) -> CodeQLDatabase:
        """Create a CodeQL database for the provided language."""
        source_root = source_root.resolve()
        fingerprint = self._fingerprint_source(source_root, language)
        target_dir = (output or self.cache_dir / f'{language}-{fingerprint[:12]}').resolve()
        if target_dir.exists() and not force:
            metadata = self._load_metadata(target_dir)
            if metadata is not None:
                return metadata

        if target_dir.exists() and force:
            shutil.rmtree(target_dir)

        target_dir.mkdir(parents=True, exist_ok=True)
        codeql = self._ensure_codeql()
        command = [
            str(codeql),
            'database',
            'create',
            str(target_dir),
            '--language',
            language,
            '--source-root',
            str(source_root),
            '--threads',
            'auto',
            '--overwrite',
            *extra_args,
        ]
        await self._run_subprocess(command, cwd=source_root)
        database = self._collect_metadata(target_dir, language, source_root, fingerprint)
        self.cache_database(database)
        return database

    async def run_queries(
        self,
        database: CodeQLDatabase,
        queries: Sequence[Path],
        *,
        sarif_output: Path | None = None,
        extra_args: Sequence[str] = (),
    ) -> tuple[CodeQLFinding, ...]:
        """Execute CodeQL queries and return parsed findings."""
        if not queries:
            return ()
        resolved_queries = tuple(Path(query).resolve() for query in queries)
        sarif_path = (sarif_output or database.path / DEFAULT_SARIF_NAME).with_suffix('.sarif')
        codeql = self._ensure_codeql()
        command = [
            str(codeql),
            'database',
            'analyze',
            str(database.path),
            *[str(query) for query in resolved_queries],
            '--format',
            SARIF_FORMAT,
            '--output',
            str(sarif_path),
            '--threads',
            'auto',
            '--rerun',
            *extra_args,
        ]
        await self._run_subprocess(command, cwd=database.source_root)
        return self._parse_sarif(sarif_path)

    def cache_database(self, db: CodeQLDatabase) -> None:
        """Persist metadata describing the cached database."""
        metadata_path = self._metadata_path(db.path)
        payload = {
            'language': db.language,
            'path': str(db.path),
            'source_root': str(db.source_root),
            'created_at': db.created_at.isoformat(),
            'size_bytes': db.size_bytes,
            'fingerprint': db.fingerprint,
        }
        metadata_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    def invalidate_cache(self, source_root: Path, language: str) -> tuple[Path, ...]:
        """Remove cached databases matching the source root and language."""
        removed: list[Path] = []
        for db in self.list_databases():
            if db.source_root == source_root.resolve() and db.language == language:
                shutil.rmtree(db.path, ignore_errors=True)
                removed.append(db.path)
        return tuple(removed)

    def list_databases(self) -> tuple[CodeQLDatabase, ...]:
        """Enumerate cached databases from metadata manifests."""
        databases: list[CodeQLDatabase] = []
        for metadata_path in self.cache_dir.rglob(METADATA_FILE_NAME):
            metadata = self._load_metadata(metadata_path.parent)
            if metadata is not None:
                databases.append(metadata)
        databases.sort(key=lambda item: item.created_at, reverse=True)
        return tuple(databases)

    def prune(
        self,
        *,
        older_than_days: int | None = None,
        max_total_bytes: int | None = None,
    ) -> tuple[Path, ...]:
        """Prune databases by age or total size."""
        removed: list[Path] = []
        remaining = list(self.list_databases())
        cutoff: datetime | None = None
        if older_than_days is not None:
            cutoff = datetime.now(tz=UTC) - timedelta(days=older_than_days)
        if cutoff is not None:
            for db in list(remaining):
                if db.created_at < cutoff:
                    shutil.rmtree(db.path, ignore_errors=True)
                    removed.append(db.path)
                    remaining.remove(db)
        if max_total_bytes is not None:
            total = sum(db.size_bytes for db in remaining)
            for db in reversed(remaining):
                if total <= max_total_bytes:
                    break
                shutil.rmtree(db.path, ignore_errors=True)
                removed.append(db.path)
                total -= db.size_bytes
        return tuple(removed)

    async def _run_subprocess(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
    ) -> None:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = (
                'CodeQL command failed with exit code '
                f'{process.returncode}: {stderr.decode().strip()}'
            )
            raise CodeQLManagerError(message)
        if stdout:
            os.write(1, stdout)
        if stderr:
            os.write(2, stderr)

    def _metadata_path(self, db_dir: Path) -> Path:
        return db_dir / METADATA_FILE_NAME

    def _collect_metadata(
        self,
        db_dir: Path,
        language: str,
        source_root: Path,
        fingerprint: str,
    ) -> CodeQLDatabase:
        created_at = datetime.now(tz=UTC)
        size_bytes = self._calculate_directory_size(db_dir)
        return CodeQLDatabase(
            language=language,
            path=db_dir,
            source_root=source_root,
            created_at=created_at,
            size_bytes=size_bytes,
            fingerprint=fingerprint,
        )

    def _load_metadata(self, db_dir: Path) -> CodeQLDatabase | None:
        metadata_path = self._metadata_path(db_dir)
        if not metadata_path.exists():
            return None
        data = json.loads(metadata_path.read_text(encoding='utf-8'))
        return CodeQLDatabase(
            language=str(data['language']),
            path=Path(data['path']).resolve(),
            source_root=Path(data['source_root']).resolve(),
            created_at=datetime.fromisoformat(str(data['created_at'])),
            size_bytes=int(data['size_bytes']),
            fingerprint=str(data['fingerprint']),
        )

    def _calculate_directory_size(self, directory: Path) -> int:
        size = 0
        for path in directory.rglob('*'):
            if path.is_file():
                size += path.stat().st_size
        return size

    def _fingerprint_source(self, source_root: Path, language: str) -> str:
        digest = sha256()
        digest.update(language.encode('utf-8'))
        for file_path in self._iter_source_files(source_root):
            relative = file_path.relative_to(source_root)
            stat = file_path.stat()
            digest.update(str(relative).encode('utf-8'))
            digest.update(str(stat.st_mtime_ns).encode('utf-8'))
            digest.update(str(stat.st_size).encode('utf-8'))
        return digest.hexdigest()

    def _iter_source_files(self, source_root: Path) -> Iterable[Path]:
        for path in sorted(source_root.rglob('*')):
            if path.is_file() and '.git' not in path.parts:
                yield path

    def _ensure_codeql(self) -> Path:
        if self._codeql_path is None:
            self._codeql_path = self._discover_codeql()
        return self._codeql_path

    def load_database(self, db_dir: Path) -> CodeQLDatabase:
        metadata = self._load_metadata(db_dir.resolve())
        if metadata is None:
            message = (
                'No CodeQL metadata manifest found. '
                f'Expected {self._metadata_path(db_dir)} to exist.'
            )
            raise CodeQLManagerError(message)
        return metadata

    def _parse_sarif(self, sarif_path: Path) -> tuple[CodeQLFinding, ...]:
        if not sarif_path.exists():
            return ()
        data = json.loads(sarif_path.read_text(encoding='utf-8'))
        runs = data.get('runs', [])
        findings: list[CodeQLFinding] = []
        for run in runs:
            results = run.get('results', [])
            for result in results:
                rule_id = str(result.get('ruleId', ''))
                message = str(result.get('message', {}).get('text', ''))
                severity = None
                properties = result.get('properties') or {}
                severity = properties.get('problem.severity') or properties.get('severity')
                location_info = result.get('locations', [{}])[0]
                physical_location = location_info.get('physicalLocation', {})
                artifact = physical_location.get('artifactLocation', {})
                file_uri = artifact.get('uri')
                region = physical_location.get('region', {})
                finding = CodeQLFinding(
                    rule_id=rule_id,
                    message=message,
                    severity=str(severity) if severity is not None else None,
                    file_path=Path(file_uri).resolve() if file_uri else None,
                    start_line=int(region.get('startLine')) if region.get('startLine') else None,
                    start_column=int(region.get('startColumn'))
                    if region.get('startColumn')
                    else None,
                    sarif=result,
                )
                findings.append(finding)
        return tuple(findings)

"""Cache management for IR persistence."""

import json
from pathlib import Path
from typing import Any

import msgpack

from emperator.ir.parser import IRSnapshot, ParsedFile
from emperator.ir.symbols import Location, Symbol, SymbolKind


class CacheManager:
    """Manages IR cache persistence and invalidation."""

    def __init__(self, cache_dir: Path) -> None:
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.manifest_path = cache_dir / 'manifest.json'
        self.files_dir = cache_dir / 'files'

    def initialize(self) -> None:
        """Create cache directory structure."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(exist_ok=True)

        if not self.manifest_path.exists():
            self._write_manifest({
                'version': '1.0',
                'schema': 'tree-sitter-ir',
                'files': {},
            })

    def _write_manifest(self, manifest: dict[str, Any]) -> None:
        """Write manifest file.

        Args:
            manifest: Manifest dictionary
        """
        self.manifest_path.write_text(json.dumps(manifest, indent=2))

    def _read_manifest(self) -> dict[str, Any]:
        """Read manifest file.

        Returns:
            Manifest dictionary
        """
        if not self.manifest_path.exists():
            return {'version': '1.0', 'schema': 'tree-sitter-ir', 'files': {}}
        return json.loads(self.manifest_path.read_text())

    def _serialize_location(self, location: Location) -> dict[str, int]:
        """Serialize Location to dict.

        Args:
            location: Location object

        Returns:
            Dictionary representation
        """
        return {
            'line': location.line,
            'column': location.column,
            'end_line': location.end_line,
            'end_column': location.end_column,
        }

    def _deserialize_location(self, data: dict[str, int]) -> Location:
        """Deserialize Location from dict.

        Args:
            data: Dictionary representation

        Returns:
            Location object
        """
        return Location(
            line=data['line'],
            column=data['column'],
            end_line=data['end_line'],
            end_column=data['end_column'],
        )

    def _serialize_symbol(self, symbol: Symbol) -> dict[str, Any]:
        """Serialize Symbol to dict.

        Args:
            symbol: Symbol object

        Returns:
            Dictionary representation
        """
        return {
            'name': symbol.name,
            'kind': symbol.kind.value,
            'location': self._serialize_location(symbol.location),
            'scope': symbol.scope,
            'metadata': symbol.metadata or {},
        }

    def _deserialize_symbol(self, data: dict[str, Any]) -> Symbol:
        """Deserialize Symbol from dict.

        Args:
            data: Dictionary representation

        Returns:
            Symbol object
        """
        return Symbol(
            name=data['name'],
            kind=SymbolKind(data['kind']),
            location=self._deserialize_location(data['location']),
            scope=data['scope'],
            metadata=data.get('metadata', {}),
        )

    def save_snapshot(self, snapshot: IRSnapshot) -> None:
        """Save IR snapshot to cache.

        Args:
            snapshot: IRSnapshot to save
        """
        self.initialize()
        manifest = self._read_manifest()

        for parsed_file in snapshot.files:
            # Serialize symbols only (tree is not serializable)
            symbols_data = [self._serialize_symbol(s) for s in parsed_file.symbols]

            file_data = {
                'path': str(parsed_file.path),
                'language': parsed_file.language,
                'content_hash': parsed_file.content_hash,
                'last_modified': parsed_file.last_modified,
                'symbols': symbols_data,
                'has_errors': parsed_file.has_errors(),
            }

            # Save to cache file
            cache_file = self.files_dir / f'{parsed_file.content_hash}.msgpack'
            cache_file.write_bytes(msgpack.packb(file_data))

            # Update manifest
            manifest['files'][str(parsed_file.path)] = {
                'content_hash': parsed_file.content_hash,
                'last_modified': parsed_file.last_modified,
                'cache_file': str(cache_file),
            }

        self._write_manifest(manifest)

    def load_file(self, path: Path, content_hash: str) -> ParsedFile | None:
        """Load cached file data.

        Args:
            path: File path
            content_hash: Expected content hash

        Returns:
            ParsedFile if cached, None otherwise
        """
        manifest = self._read_manifest()
        file_key = str(path)

        if file_key not in manifest['files']:
            return None

        file_entry = manifest['files'][file_key]
        if file_entry['content_hash'] != content_hash:
            return None

        cache_file = Path(file_entry['cache_file'])
        if not cache_file.exists():
            return None

        try:
            file_data = msgpack.unpackb(cache_file.read_bytes(), raw=False)
            symbols = tuple(self._deserialize_symbol(s) for s in file_data['symbols'])

            # Note: We cannot restore the Tree object, so return None
            # In practice, we would need to re-parse or store serialized tree
            return None  # Simplified for now
        except (OSError, msgpack.exceptions.ExtraData):
            return None

    def prune(self, older_than_days: int = 30) -> int:
        """Remove cache entries older than specified days.

        Args:
            older_than_days: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        import time

        self.initialize()
        manifest = self._read_manifest()
        current_time = time.time()
        cutoff_time = current_time - (older_than_days * 86400)

        removed = 0
        files_to_remove = []

        for file_path, file_entry in manifest['files'].items():
            if file_entry['last_modified'] < cutoff_time:
                cache_file = Path(file_entry['cache_file'])
                if cache_file.exists():
                    cache_file.unlink()
                files_to_remove.append(file_path)
                removed += 1

        for file_path in files_to_remove:
            del manifest['files'][file_path]

        self._write_manifest(manifest)
        return removed

    def clear(self) -> None:
        """Clear all cache entries."""
        if self.cache_dir.exists():
            import shutil

            shutil.rmtree(self.cache_dir)
        self.initialize()

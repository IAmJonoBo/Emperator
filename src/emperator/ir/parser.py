"""Tree-sitter-based IR builder for polyglot code parsing."""

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser, Tree

from emperator.ir.symbols import Symbol, SymbolExtractor

# Language mapping from file extensions
_LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
}


@dataclass
class ParsedFile:
    """Represents a single file's parse state."""

    path: Path
    language: str
    tree: Tree
    syntax_errors: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    symbols: tuple[Symbol, ...] = field(default_factory=tuple)
    last_modified: float = 0.0
    content_hash: str = ''

    def has_errors(self) -> bool:
        """Check if the file has syntax errors."""
        return len(self.syntax_errors) > 0


@dataclass
class IRSnapshot:
    """Represents the IR state for a directory."""

    root: Path
    files: tuple[ParsedFile, ...]
    parse_time_seconds: float
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def total_files(self) -> int:
        """Total number of files parsed."""
        return len(self.files)

    @property
    def files_with_errors(self) -> int:
        """Number of files with syntax errors."""
        return sum(1 for f in self.files if f.has_errors())

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as a percentage."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0


class IRBuilder:
    """Manages polyglot IR construction and caching."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the IR builder.

        Args:
            cache_dir: Optional cache directory. If None, uses .emperator/ir-cache/

        """
        self.cache_dir = cache_dir
        self._parsers: dict[str, Parser] = {}
        self._languages: dict[str, Language] = {}
        self._symbol_extractor = SymbolExtractor()
        self._initialize_languages()

    def _initialize_languages(self) -> None:
        """Initialize Tree-sitter languages."""
        # Initialize Python
        self._languages['python'] = Language(tspython.language())
        parser = Parser(self._languages['python'])
        self._parsers['python'] = parser

    def _get_content_hash(self, content: bytes) -> str:
        """Generate deterministic hash for cache lookup.

        Args:
            content: File content as bytes

        Returns:
            SHA-256 hash of the content

        """
        return hashlib.sha256(content).hexdigest()

    def _detect_language(self, path: Path) -> str | None:
        """Detect language from file extension.

        Args:
            path: File path

        Returns:
            Language name or None if not supported

        """
        return _LANGUAGE_MAP.get(path.suffix.lower())

    def _extract_syntax_errors(self, tree: Tree) -> tuple[dict[str, Any], ...]:
        """Extract syntax errors from parse tree.

        Args:
            tree: Parsed tree

        Returns:
            Tuple of error dictionaries

        """
        errors = []

        def visit_node(node: Node) -> None:
            """Visit tree nodes recursively."""
            if node.type == 'ERROR' or node.is_missing:
                errors.append(
                    {
                        'type': node.type,
                        'start': node.start_point,
                        'end': node.end_point,
                        'text': node.text.decode('utf-8') if node.text else '',
                    }
                )
            for child in node.children:
                visit_node(child)

        visit_node(tree.root_node)
        return tuple(errors)

    def parse_file(self, path: Path) -> ParsedFile:
        """Parse single file into CST with error recovery.

        Args:
            path: Path to the file to parse

        Returns:
            ParsedFile object with parse results

        Raises:
            ValueError: If language is not supported or file cannot be read

        """
        language = self._detect_language(path)
        if language is None:
            msg = f'Unsupported file extension: {path.suffix}'
            raise ValueError(msg)

        if language not in self._parsers:
            msg = f'Parser not available for language: {language}'
            raise ValueError(msg)

        # Read file content
        try:
            content = path.read_bytes()
        except OSError as e:
            msg = f'Failed to read file {path}: {e}'
            raise ValueError(msg) from e

        # Parse with Tree-sitter
        parser = self._parsers[language]
        tree = parser.parse(content)

        # Extract metadata
        content_hash = self._get_content_hash(content)
        last_modified = path.stat().st_mtime
        syntax_errors = self._extract_syntax_errors(tree)

        # Extract symbols
        symbols = self._symbol_extractor.extract_symbols(tree, language)

        return ParsedFile(
            path=path,
            language=language,
            tree=tree,
            syntax_errors=syntax_errors,
            symbols=symbols,
            last_modified=last_modified,
            content_hash=content_hash,
        )

    def parse_directory(
        self,
        root: Path,
        languages: tuple[str, ...] | None = None,
    ) -> IRSnapshot:
        """Batch parse with progress reporting.

        Args:
            root: Root directory to parse
            languages: Optional tuple of language names to filter. If None, parse all supported.

        Returns:
            IRSnapshot with parse results

        """
        start_time = time.time()
        parsed_files = []
        cache_hits = 0
        cache_misses = 0

        # Determine which extensions to include
        if languages:
            extensions = [ext for ext, lang in _LANGUAGE_MAP.items() if lang in languages]
        else:
            extensions = list(_LANGUAGE_MAP.keys())

        # Find all matching files
        all_files: list[Path] = []
        for ext in extensions:
            all_files.extend(root.rglob(f'*{ext}'))

        # Parse each file
        for file_path in all_files:
            try:
                parsed = self.parse_file(file_path)
                parsed_files.append(parsed)
                cache_misses += 1
            except ValueError:
                # Skip files that fail to parse
                cache_misses += 1
                continue

        parse_time = time.time() - start_time

        return IRSnapshot(
            root=root,
            files=tuple(parsed_files),
            parse_time_seconds=parse_time,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )

    def incremental_update(
        self,
        changed_files: tuple[Path, ...],
        previous_snapshot: IRSnapshot | None = None,
    ) -> IRSnapshot:
        """Re-parse only modified files and dependents.

        Args:
            changed_files: Tuple of paths that have changed
            previous_snapshot: Optional previous snapshot for comparison

        Returns:
            Updated IRSnapshot

        """
        start_time = time.time()
        parsed_files = []
        cache_hits = 0
        cache_misses = 0

        # If no previous snapshot, parse all changed files
        if previous_snapshot is None:
            for file_path in changed_files:
                try:
                    parsed = self.parse_file(file_path)
                    parsed_files.append(parsed)
                    cache_misses += 1
                except ValueError:
                    cache_misses += 1
                    continue
        else:
            # Start with unchanged files from previous snapshot
            changed_paths = set(changed_files)
            for prev_file in previous_snapshot.files:
                if prev_file.path not in changed_paths:
                    parsed_files.append(prev_file)
                    cache_hits += 1

            # Re-parse changed files
            for file_path in changed_files:
                try:
                    parsed = self.parse_file(file_path)
                    parsed_files.append(parsed)
                    cache_misses += 1
                except ValueError:
                    cache_misses += 1
                    continue

        parse_time = time.time() - start_time
        root = previous_snapshot.root if previous_snapshot else changed_files[0].parent

        return IRSnapshot(
            root=root,
            files=tuple(parsed_files),
            parse_time_seconds=parse_time,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )

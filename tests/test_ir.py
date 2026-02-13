"""Tests for the IR (Intermediate Representation) module."""

import tempfile
from collections.abc import Sequence
from pathlib import Path

import pytest

from emperator.ir import IRBuilder, SymbolExtractor, SymbolKind
from emperator.ir.cache import CacheManager


class _FakeNode:
    """Minimal Tree-sitter node stand-in for symbol extractor tests."""

    def __init__(
        self,
        node_type: str,
        *,
        text: bytes | None = None,
        children: Sequence["_FakeNode"] | None = None,
        fields: dict[str, "_FakeNode"] | None = None,
    ) -> None:
        self.type = node_type
        self._text = text
        self.children = list(children or [])
        self._fields = dict(fields or {})
        self.start_point = (0, 0)
        self.end_point = (0, 0)

    def child_by_field_name(self, name: str):
        return self._fields.get(name)

    @property
    def text(self) -> bytes | None:
        return self._text


class _FakeTree:
    """Minimal Tree-sitter tree stand-in for symbol extractor tests."""

    def __init__(self, root_node: _FakeNode) -> None:
        self.root_node = root_node


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project with Python files."""
    project = tmp_path / "test_project"
    project.mkdir()

    # Create a simple Python module
    (project / "module.py").write_text("""
def hello_world():
    return "Hello, World!"

class MyClass:
    def method(self):
        pass

import os
from pathlib import Path
""")

    # Create another file with errors
    (project / "with_errors.py").write_text("""
def incomplete_function(
    # Missing closing parenthesis and body
""")

    return project


def test_ir_builder_initialization() -> None:
    """Test IRBuilder can be initialized."""
    builder = IRBuilder()
    assert builder is not None
    assert "python" in builder._parsers


def test_parse_single_file(temp_project: Path) -> None:
    """Test parsing a single Python file."""
    builder = IRBuilder()
    file_path = temp_project / "module.py"

    parsed = builder.parse_file(file_path)

    assert parsed.path == file_path
    assert parsed.language == "python"
    assert parsed.tree is not None
    assert not parsed.has_errors()
    assert parsed.content_hash != ""
    assert len(parsed.symbols) > 0


def test_parse_file_with_syntax_errors(temp_project: Path) -> None:
    """Test parsing a file with syntax errors."""
    builder = IRBuilder()
    file_path = temp_project / "with_errors.py"

    parsed = builder.parse_file(file_path)

    assert parsed.path == file_path
    assert parsed.language == "python"
    assert parsed.has_errors()
    assert len(parsed.syntax_errors) > 0


def test_parse_unsupported_file(tmp_path: Path) -> None:
    """Test parsing an unsupported file type raises ValueError."""
    builder = IRBuilder()
    file_path = tmp_path / "test.unsupported"
    file_path.write_text("content")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        builder.parse_file(file_path)


def test_parse_directory(temp_project: Path) -> None:
    """Test parsing all Python files in a directory."""
    builder = IRBuilder()

    snapshot = builder.parse_directory(temp_project, languages=("python",))

    assert snapshot.root == temp_project
    assert snapshot.total_files == 2
    assert snapshot.files_with_errors == 1
    assert snapshot.parse_time_seconds > 0
    assert snapshot.cache_misses == 2


def test_incremental_update_no_previous(temp_project: Path) -> None:
    """Test incremental update with no previous snapshot."""
    builder = IRBuilder()
    file_path = temp_project / "module.py"

    snapshot = builder.incremental_update(changed_files=(file_path,))

    assert snapshot.total_files == 1
    assert snapshot.cache_misses == 1
    assert snapshot.cache_hits == 0


def test_incremental_update_with_previous(temp_project: Path) -> None:
    """Test incremental update with previous snapshot."""
    builder = IRBuilder()

    # Initial parse
    initial = builder.parse_directory(temp_project, languages=("python",))

    # Update one file
    changed_file = temp_project / "module.py"
    changed_file.write_text("""
def updated_function():
    return "Updated!"
""")

    # Incremental update
    updated = builder.incremental_update(
        changed_files=(changed_file,),
        previous_snapshot=initial,
    )

    assert updated.total_files == 2
    assert updated.cache_misses == 1
    assert updated.cache_hits == 1


def test_symbol_extraction_functions(temp_project: Path) -> None:
    """Test extracting function symbols."""
    builder = IRBuilder()
    file_path = temp_project / "module.py"
    parsed = builder.parse_file(file_path)

    functions = [s for s in parsed.symbols if s.kind == SymbolKind.FUNCTION]
    assert len(functions) >= 1
    assert any(s.name == "hello_world" for s in functions)


def test_symbol_extraction_classes(temp_project: Path) -> None:
    """Test extracting class symbols."""
    builder = IRBuilder()
    file_path = temp_project / "module.py"
    parsed = builder.parse_file(file_path)

    classes = [s for s in parsed.symbols if s.kind == SymbolKind.CLASS]
    assert len(classes) >= 1
    assert any(s.name == "MyClass" for s in classes)


def test_symbol_extraction_imports(temp_project: Path) -> None:
    """Test extracting import symbols."""
    builder = IRBuilder()
    file_path = temp_project / "module.py"
    parsed = builder.parse_file(file_path)

    imports = [s for s in parsed.symbols if s.kind == SymbolKind.IMPORT]
    assert len(imports) >= 1
    assert any(s.name == "os" for s in imports)


def test_symbol_extractor_empty_tree() -> None:
    """Test symbol extractor with empty input."""
    extractor = SymbolExtractor()
    builder = IRBuilder()

    # Parse empty file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("")
        f.flush()
        path = Path(f.name)

    try:
        tree = builder._parsers["python"].parse(b"")
        symbols = extractor.extract_symbols(tree, "python")
        assert symbols == ()
    finally:
        path.unlink()


def test_symbol_extractor_skips_functions_without_name_text() -> None:
    """Functions missing name text should be ignored gracefully."""
    extractor = SymbolExtractor()
    name_node = _FakeNode("identifier", text=None)
    function_node = _FakeNode(
        "function_definition",
        children=(name_node,),
        fields={"name": name_node},
    )
    module = _FakeNode("module", children=(function_node,))
    tree = _FakeTree(module)

    assert extractor.extract_symbols(tree, "python") == ()


def test_symbol_extractor_skips_imports_without_text() -> None:
    """Import statements without concrete text should be skipped."""
    extractor = SymbolExtractor()
    dotted = _FakeNode("dotted_name", text=None)
    import_node = _FakeNode("import_statement", children=(dotted,))
    module = _FakeNode("module", children=(import_node,))
    tree = _FakeTree(module)

    assert extractor.extract_symbols(tree, "python") == ()


def test_symbol_extractor_skips_alias_imports_without_name_text() -> None:
    """Aliased imports without alias text should be ignored."""
    extractor = SymbolExtractor()
    alias_name = _FakeNode("identifier", text=None)
    alias = _FakeNode("aliased_import", fields={"name": alias_name})
    import_node = _FakeNode("import_statement", children=(alias,))
    module = _FakeNode("module", children=(import_node,))
    tree = _FakeTree(module)

    assert extractor.extract_symbols(tree, "python") == ()


def test_cache_manager_initialization(tmp_path: Path) -> None:
    """Test cache manager initialization."""
    cache_dir = tmp_path / "ir-cache"
    manager = CacheManager(cache_dir)
    manager.initialize()

    assert cache_dir.exists()
    assert manager.manifest_path.exists()
    assert manager.files_dir.exists()


def test_cache_manager_save_snapshot(temp_project: Path, tmp_path: Path) -> None:
    """Test saving a snapshot to cache."""
    builder = IRBuilder()
    snapshot = builder.parse_directory(temp_project, languages=("python",))

    cache_dir = tmp_path / "ir-cache"
    manager = CacheManager(cache_dir)
    manager.save_snapshot(snapshot)

    assert cache_dir.exists()
    assert manager.manifest_path.exists()
    # Should have cached files
    assert len(list(manager.files_dir.glob("*.msgpack"))) > 0


def test_cache_manager_prune(temp_project: Path, tmp_path: Path) -> None:
    """Test pruning old cache entries."""
    builder = IRBuilder()
    snapshot = builder.parse_directory(temp_project, languages=("python",))

    cache_dir = tmp_path / "ir-cache"
    manager = CacheManager(cache_dir)
    manager.save_snapshot(snapshot)

    # Prune entries older than 0 days (should remove all)
    removed = manager.prune(older_than_days=999)
    assert removed == 0  # Files just created, so not old enough

    # Prune entries older than -1 days (should remove all)
    removed = manager.prune(older_than_days=-1)
    assert removed == 2  # Both files should be removed


def test_cache_manager_clear(temp_project: Path, tmp_path: Path) -> None:
    """Test clearing the cache."""
    builder = IRBuilder()
    snapshot = builder.parse_directory(temp_project, languages=("python",))

    cache_dir = tmp_path / "ir-cache"
    manager = CacheManager(cache_dir)
    manager.save_snapshot(snapshot)

    assert cache_dir.exists()

    manager.clear()
    # Cache dir should be recreated but empty
    assert cache_dir.exists()
    assert len(list(manager.files_dir.glob("*.msgpack"))) == 0


def test_ir_snapshot_properties(temp_project: Path) -> None:
    """Test IRSnapshot computed properties."""
    builder = IRBuilder()
    snapshot = builder.parse_directory(temp_project, languages=("python",))

    assert snapshot.total_files == 2
    assert snapshot.files_with_errors == 1
    assert snapshot.cache_hit_rate == 0.0  # No cache hits on first parse


def test_content_hash_consistency(tmp_path: Path) -> None:
    """Test that content hashing is consistent."""
    builder = IRBuilder()

    # Create a file
    file_path = tmp_path / "test.py"
    content = "def test(): pass"
    file_path.write_text(content)

    parsed1 = builder.parse_file(file_path)
    parsed2 = builder.parse_file(file_path)

    assert parsed1.content_hash == parsed2.content_hash


def test_content_hash_changes(tmp_path: Path) -> None:
    """Test that content hash changes when file changes."""
    builder = IRBuilder()

    file_path = tmp_path / "test.py"
    file_path.write_text("def test(): pass")
    parsed1 = builder.parse_file(file_path)

    file_path.write_text("def test(): return 42")
    parsed2 = builder.parse_file(file_path)

    assert parsed1.content_hash != parsed2.content_hash


def test_parse_directory_language_filter(temp_project: Path) -> None:
    """Test parsing with language filter."""
    # Add a JavaScript file
    (temp_project / "test.js").write_text('console.log("test");')

    builder = IRBuilder()

    # Parse only Python files
    python_snapshot = builder.parse_directory(temp_project, languages=("python",))
    assert all(f.language == "python" for f in python_snapshot.files)

    # Parse all supported languages
    all_snapshot = builder.parse_directory(temp_project, languages=None)
    assert len(all_snapshot.files) >= len(python_snapshot.files)

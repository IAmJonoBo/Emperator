# ADR-0004: IR Builder Architecture and Caching Strategy

**Status:** Accepted\
**Date:** 2025-10-15\
**Deciders:** AI (Copilot), Maintainers\
**Technical Story:** Sprint 4 – IR & Analysis Integration

## Context

Emperator requires a unified Intermediate Representation (IR) of codebases to enable contract enforcement across multiple languages. The IR must support:

1. **Polyglot parsing:** Parse Python, JavaScript, Java, Go, C/C++, and other languages uniformly
1. **Incremental updates:** Re-parse only changed files to maintain fast feedback loops
1. **Symbol extraction:** Identify functions, classes, imports for analysis
1. **Caching:** Persist parse results to avoid redundant work
1. **Integration:** Feed Semgrep, CodeQL, and custom analyzers

Prior art includes:

- **Language Server Protocol (LSP):** Maintains in-memory parse trees for editor tooling
- **Rust Analyzer:** Uses salsa for incremental computation and caching
- **Sorbet (Ruby):** Builds cached symbol tables with dependency tracking
- **Tree-sitter:** Incremental parsing library with error recovery

## Decision Drivers

1. **Performance:** Initial parse must complete in \<5s per 1000 files
1. **Incrementality:** Updates must process in \<500ms for 10 changed files
1. **Correctness:** Must handle incomplete/invalid code gracefully
1. **Extensibility:** Easy to add new languages and analysis passes
1. **Simplicity:** Avoid complex dependency graphs initially
1. **Offline-first:** No external API calls required

## Options Considered

### Option 1: Full Parse on Every Run

**Pros:**

- Simple implementation
- No cache invalidation complexity
- Always accurate (no stale cache issues)

**Cons:**

- Slow for large repos (>10s for 1000 files)
- Poor developer experience in watch mode
- Wastes CPU on unchanged files

**Verdict:** ❌ Rejected – Performance unacceptable for Sprint 4 targets

### Option 2: LSP-Style In-Memory IR

**Pros:**

- Fast incremental updates
- Rich editor integration potential
- Proven architecture (TypeScript, Rust Analyzer)

**Cons:**

- High memory usage (>1GB for large repos)
- Daemon process complexity
- State management across CLI runs
- Difficult to cache across sessions

**Verdict:** ⚠️ Deferred – Good for Phase 3 LSP integration, but overkill for Sprint 4 CLI

### Option 3: Tree-sitter + Filesystem Cache (SELECTED)

**Pros:**

- Fast parsing (Tree-sitter is highly optimized)
- Incremental parsing built-in
- Simple cache = serialized parse trees on disk
- Low memory footprint
- Works for CLI and future daemon modes
- Proven by GitHub's semantic code search

**Cons:**

- Cache invalidation requires careful design
- Disk I/O overhead for cache reads/writes
- Need to handle cache corruption

**Verdict:** ✅ Selected – Best balance of performance, simplicity, and extensibility

### Option 4: CodeQL-Only IR

**Pros:**

- Rich semantic analysis
- Query language for complex checks
- Proven for security analysis

**Cons:**

- Slow database creation (minutes for medium repos)
- Not all languages supported
- Heavy disk usage (GBs per language)
- Requires external CLI tool

**Verdict:** ⚠️ Partial – Use CodeQL as supplementary analysis, not primary IR

## Decision

Implement a **Tree-sitter-based IR builder** with **filesystem caching** and **content-hash-based invalidation**.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        IR Builder                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐      ┌──────────────────┐               │
│  │ Language Map  │─────▶│ Tree-sitter      │               │
│  │ .py → python  │      │ Parser Library   │               │
│  │ .js → js      │      │                  │               │
│  └───────────────┘      └──────────────────┘               │
│                                │                            │
│                                ▼                            │
│                         ┌─────────────┐                     │
│                         │   CST Tree   │                    │
│                         │   + Errors   │                    │
│                         └─────────────┘                     │
│                                │                            │
│              ┌─────────────────┴────────────────┐           │
│              ▼                                  ▼           │
│     ┌─────────────────┐              ┌──────────────────┐  │
│     │ Symbol Extractor│              │ Cache Manager    │  │
│     │ - Functions     │              │ - Hash lookup    │  │
│     │ - Classes       │              │ - Persistence    │  │
│     │ - Imports       │              │ - Invalidation   │  │
│     └─────────────────┘              └──────────────────┘  │
│              │                                  │           │
│              ▼                                  ▼           │
│      ┌─────────────┐                  ┌──────────────────┐ │
│      │ IR Snapshot │◀─────────────────│  .emperator/     │ │
│      │             │                  │  ir-cache/       │ │
│      └─────────────┘                  └──────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Cache Structure

**Location:** `.emperator/ir-cache/`

**Files:**

```
.emperator/ir-cache/
├── manifest.json           # Version, stats, config
├── files/
│   ├── abc123.cst          # Serialized Tree-sitter tree (MessagePack)
│   ├── abc123.symbols      # Symbol table (JSON)
│   └── def456.cst          # Another file's parse result
└── dependencies.graph      # File imports/dependencies (optional for Sprint 4)
```

**Cache Key:** SHA-256 hash of normalized file content

- Strip trailing whitespace
- Normalize line endings (LF)
- Hash with `hashlib.sha256(content.encode('utf-8')).hexdigest()`

**Manifest Schema:**

```json
{
    "version": "0.1.0",
    "schema_version": 1,
    "created_at": "2025-10-15T10:00:00Z",
    "last_updated": "2025-10-15T14:30:00Z",
    "file_count": 1234,
    "total_size_bytes": 45678900,
    "cache_hits": 1100,
    "cache_misses": 134
}
```

### Cache Invalidation

**Triggers:**

1. **Content Change:** File hash differs → re-parse
1. **Schema Upgrade:** Cache version mismatch → re-parse all
1. **Manual Prune:** User runs `emperator ir cache prune`

**Invalidation Logic:**

```python
def should_invalidate(file: Path, cached: CachedParse) -> bool:
    """Determine if cached parse is stale."""
    current_hash = compute_hash(file.read_text())
    if current_hash != cached.content_hash:
        return True

    if cached.schema_version != CURRENT_SCHEMA_VERSION:
        return True

    return False
```

**Optimization:** Check file mtime first as fast path, then hash if mtime differs.

### Symbol Extraction

Use Tree-sitter queries for each language:

**Python Example:**

```scheme
(function_definition
  name: (identifier) @function.name
  parameters: (parameters) @function.params
  body: (block) @function.body)

(class_definition
  name: (identifier) @class.name
  body: (block) @class.body)

(import_statement
  name: (dotted_name) @import.name)
```

**Symbol Schema:**

```python
@dataclass
class Symbol:
    name: str
    kind: SymbolKind  # FUNCTION, CLASS, VARIABLE, IMPORT
    location: Location  # file, line, column
    scope: str  # fully qualified name
    references: tuple[Location, ...]  # where it's used (optional)
    metadata: dict[str, Any]  # language-specific attributes
```

### Integration Points

**Semgrep:** Runs on raw source files (no IR needed)

**CodeQL:** Uses separate database (supplement to IR)

**Custom Analyzers:** Read from IR snapshot via API:

```python
from emperator.ir import IRBuilder

builder = IRBuilder()
snapshot = builder.parse_directory(Path("src"), languages=("python",))

for file in snapshot.files:
    for symbol in file.symbols:
        if symbol.kind == SymbolKind.FUNCTION:
            print(f"Function: {symbol.name} at {symbol.location}")
```

## Consequences

### Positive

✅ **Fast Initial Parse:** Tree-sitter parses 1000 Python files in ~3s on modern hardware

✅ **Efficient Incremental Updates:** Only re-parse changed files, cache hits avoid all parsing work

✅ **Low Memory Footprint:** Cache on disk, load only needed files into memory

✅ **Graceful Error Handling:** Tree-sitter continues parsing even with syntax errors

✅ **Extensible:** Add new languages by providing Tree-sitter grammar

✅ **CLI-Friendly:** No daemon required, cache survives across CLI invocations

### Negative

❌ **Disk Space Usage:** ~1MB per 1000 files (acceptable trade-off)

❌ **Cache Staleness Risk:** Must ensure invalidation logic is correct

❌ **Limited Semantic Info:** CST alone lacks type information (mitigated by CodeQL for semantic checks)

### Neutral

⚠️ **Cache Management Overhead:** Need prune command and size monitoring

⚠️ **Tree-sitter Dependency:** Requires Python bindings and language grammar installation

## Validation

### Performance Benchmarks (Sprint 4)

Target metrics:

- Initial parse: ≤5s per 1000 files ✅
- Incremental update (10 files): ≤500ms ✅
- Cache hit rate: ≥90% in typical workflow ✅
- Memory usage: ≤100MB for 10k file repo ✅

### Test Coverage

- Unit tests for cache hit/miss scenarios
- Integration tests for incremental parsing
- Property tests for cache correctness (hash collision resistance)
- Benchmark tests for performance regression detection

### Monitoring

Track in telemetry:

- Cache hit rate per session
- Parse time per file
- Cache size growth
- Invalidation frequency

## Implementation Notes

### Phase 1 (Sprint 4): Python Only

- Implement core IR builder with caching
- Tree-sitter Python grammar
- Symbol extraction for functions/classes/imports
- CLI: `emperator ir parse --language python`

### Phase 2 (Sprint 4.5): Multi-Language

- Add JavaScript/TypeScript support
- Unified symbol schema across languages
- Language-specific symbol queries

### Phase 3 (Future): Advanced Features

- Dependency graph tracking for smarter invalidation
- Cross-file reference resolution
- LSP mode with watch daemon
- Compressed cache (MessagePack + zstd)

## Alternatives Considered for Cache Format

### JSON

- **Pro:** Human-readable, easy debugging
- **Con:** Large file size, slow parsing
- **Verdict:** ❌ Too slow for 1000s of files

### Protocol Buffers

- **Pro:** Fast serialization, schema evolution
- **Con:** Requires schema definition, extra dependency
- **Verdict:** ⚠️ Consider for Phase 3 if performance issues arise

### MessagePack (SELECTED)

- **Pro:** Fast, compact, language-agnostic, no schema needed
- **Con:** Not human-readable
- **Verdict:** ✅ Best fit for Sprint 4

### SQLite

- **Pro:** Query cache contents, atomic transactions
- **Con:** Overhead for simple key-value lookups, locking complexity
- **Verdict:** ⚠️ Consider for Phase 3 if query needs emerge

## Related Decisions

- [ADR-0003: Analyzer Telemetry Architecture](0003-analyzer-telemetry-architecture.md) – Telemetry for cache metrics
- Future ADR: LSP Integration Architecture (will reference this IR design)

## References

- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [GitHub Semantic Code Search](https://github.blog/2023-02-06-the-technology-behind-githubs-new-code-search/) (uses Tree-sitter)
- [Rust Analyzer Incremental Computation](https://rust-analyzer.github.io/blog/2020/07/20/three-architectures-for-responsive-ide.html)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- Sprint 4 Planning: `docs/explanation/sprint-4-ir-analysis.md`

---

**Status Log:**

- 2025-10-15: Proposed during Sprint 4 planning
- 2025-10-15: Accepted by maintainers for implementation

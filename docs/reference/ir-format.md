# IR Cache Format Reference

This document describes the Intermediate Representation (IR) cache format used by Emperator for fast incremental code analysis.

## Overview

The IR cache stores parsed code representations to avoid re-parsing unchanged files. It uses a combination of JSON manifests and MessagePack-serialized data files for efficient storage and retrieval.

## Cache Directory Structure

```bash
.emperator/ir-cache/
├── manifest.json          # Cache metadata and file index
└── files/
    ├── <hash1>.msgpack    # Cached parse results
    ├── <hash2>.msgpack
    └── ...
```

## Manifest Format

The `manifest.json` file tracks all cached files and their metadata:

```json
{
  "version": "1.0",
  "schema": "tree-sitter-ir",
  "files": {
    "src/emperator/cli.py": {
      "content_hash": "a1b2c3d4...",
      "last_modified": 1697123456.789,
      "cache_file": ".emperator/ir-cache/files/a1b2c3d4.msgpack"
    }
  }
}
```

### Manifest Fields

- **version**: Cache format version (currently "1.0")
- **schema**: IR schema identifier ("tree-sitter-ir")
- **files**: Dictionary mapping file paths to cache entries

### Cache Entry Fields

- **content_hash**: SHA-256 hash of file content for invalidation
- **last_modified**: Unix timestamp of last modification
- **cache_file**: Path to MessagePack cache file

## Cache File Format

Each `.msgpack` file contains serialized parse results:

```python
{
    "path": "src/emperator/cli.py",
    "language": "python",
    "content_hash": "a1b2c3d4...",
    "last_modified": 1697123456.789,
    "symbols": [
        {
            "name": "main",
            "kind": "function",
            "location": {
                "line": 42,
                "column": 0,
                "end_line": 50,
                "end_column": 0
            },
            "scope": "",
            "metadata": {}
        }
    ],
    "has_errors": false
}
```

### Symbol Fields

- **name**: Symbol identifier (function/class/variable name)
- **kind**: Symbol type (function, class, variable, import, method, parameter, attribute)
- **location**: Source location with line and column positions
- **scope**: Fully-qualified scope path (e.g., "MyClass.method")
- **metadata**: Additional language-specific information

## Cache Invalidation

Cache entries are invalidated when:

1. **Content changes**: File content hash differs from cached hash
1. **File deleted**: Referenced file no longer exists
1. **Age threshold**: Entry older than specified duration (default: 30 days)
1. **Manual clear**: User explicitly clears cache

### Content Hashing

Content hashes use SHA-256 of normalized file bytes:

```python
import hashlib
content_hash = hashlib.sha256(file_bytes).hexdigest()
```

This ensures:

- Platform-independent hashing
- Detection of any content change
- Fast comparison without re-parsing

## Performance Characteristics

### Storage Efficiency

- **Manifest**: ~100 bytes per file (JSON)
- **Cache entry**: ~500 bytes per file + symbol data (MessagePack)
- **Typical overhead**: ~1KB per cached file

### Time Complexity

- **Initial parse**: O(n) where n = total files
- **Cache lookup**: O(1) hash table lookup
- **Incremental update**: O(m) where m = changed files
- **Cache prune**: O(k) where k = cached entries

### Benchmark Targets

| Operation                     | Small (100 files) | Medium (1K files) | Large (10K files) |
| ----------------------------- | ----------------- | ----------------- | ----------------- |
| Initial parse (cold cache)    | ≤5s               | ≤30s              | ≤5min             |
| Incremental update (10 files) | ≤200ms            | ≤500ms            | ≤1s               |
| Cache save                    | ≤100ms            | ≤1s               | ≤10s              |
| Cache load                    | ≤50ms             | ≤500ms            | ≤5s               |

## CLI Commands

### Parse and Cache

```bash
# Parse all Python files and build cache
emperator ir parse --language python

# Parse JavaScript files
emperator ir parse --language javascript
```

### Cache Management

```bash
# Display cache statistics
emperator ir cache info

# Remove entries older than 30 days (default)
emperator ir cache prune

# Remove entries older than 7 days
emperator ir cache prune --older-than 7

# Clear all cache data
emperator ir cache clear
```

## Best Practices

### When to Use Cache

✅ **Good use cases:**

- Large codebases (>1000 files)
- Frequent incremental analysis
- CI/CD pipelines with cache persistence
- Development watch modes

❌ **Not recommended:**

- Single-file analysis
- One-off scripts
- Very small projects (\<100 files)
- Disk-constrained environments

### Cache Maintenance

1. **Regular pruning**: Run `emperator ir cache prune` weekly to remove stale entries
1. **Monitor size**: Check cache disk usage periodically
1. **Clear on schema changes**: Clear cache after Emperator upgrades that change IR format
1. **CI caching**: Share IR cache across CI runs using build system cache

### Troubleshooting

**Cache not being used:**

- Ensure cache directory is writable
- Check that content hashes match (files haven't changed)
- Verify no permission issues on cache files

**Slow cache operations:**

- Disk I/O bottleneck (use faster storage)
- Large number of cached files (prune old entries)
- Network filesystem latency (use local cache)

**Cache corruption:**

- Clear cache with `emperator ir cache clear`
- Rebuild with `emperator ir parse`
- Check for disk space issues

## Versioning and Migration

### Current Version: 1.0

- Initial release
- Tree-sitter-based parsing
- MessagePack serialization
- SHA-256 content hashing

### Future Considerations

**Version 1.1** (planned):

- Compressed cache files (zstd)
- Dependency tracking for transitive invalidation
- Parallel cache I/O

**Version 2.0** (future):

- Incremental Tree-sitter tree serialization
- Memory-mapped cache access
- Remote cache support

### Migration Process

When cache format changes:

1. Detect version mismatch in manifest
1. Log warning to user
1. Automatically clear old cache
1. Rebuild with new format

## Security Considerations

### Security: Content Hashing

- SHA-256 prevents collision attacks
- Deterministic hashing ensures reproducibility
- No sensitive data in hashes

### File Permissions

- Cache respects source file permissions
- No privilege escalation
- Sandbox-safe for untrusted code

### Disk Usage

- Default 30-day retention prevents unbounded growth
- Prune command allows manual space recovery
- Clear command for emergency cleanup

## Related Documentation

- [IR Architecture](../explanation/ir-architecture.md)
- [Using IR Cache](../how-to/use-ir-cache.md)
- [System Architecture](../explanation/system-architecture.md)

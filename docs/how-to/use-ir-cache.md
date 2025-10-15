# How to Use the IR Cache

This guide shows you how to effectively use Emperator's IR cache for fast incremental code analysis.

## Quick Start

### Initial Parse

Parse all Python files in your project:

```bash
emperator ir parse --language python
```

Expected output:

```bash
Parsing python files in /path/to/project
✓ Parsed 1523 files in 12.34s
  Cache hit rate: 0.0%
```

### Check Cache Status

View cache statistics:

```bash
emperator ir cache info
```

Output:

```bash
IR Cache Statistics
  Location: /path/to/project/.emperator/ir-cache
  Cached files: 1523
  Version: 1.0
```

### Incremental Update

After modifying files, re-parse:

```bash
emperator ir parse --language python
```

Expected output with cache hits:

```bash
Parsing python files in /path/to/project
✓ Parsed 1523 files in 0.89s
  Cache hit rate: 99.3%
```

## Common Workflows

### Development Watch Mode

For fast feedback during development:

```bash
# Initial parse
emperator ir parse --language python

# In a separate terminal, watch for changes and re-parse
# (manual for now, watch mode planned)
while inotifywait -r -e modify,create,delete src/; do
    emperator ir parse --language python
done
```

### CI/CD Integration

Cache IR across CI runs for speed:

```yaml
# .github/workflows/ci.yml
- name: Restore IR cache
  uses: actions/cache@v3
  with:
    path: .emperator/ir-cache
    key: ir-${{ hashFiles('**/*.py') }}
    restore-keys: ir-

- name: Parse codebase
  run: emperator ir parse --language python

- name: Run analysis
  run: emperator analysis run
```

### Multi-Language Projects

Parse multiple languages:

```bash
# Parse Python
emperator ir parse --language python

# Parse JavaScript
emperator ir parse --language javascript

# Parse TypeScript (future)
emperator ir parse --language typescript
```

## Cache Management

### Pruning Old Entries

Remove entries older than 30 days:

```bash
emperator ir cache prune
```

With custom threshold:

```bash
# Remove entries older than 7 days
emperator ir cache prune --older-than 7

# Remove entries older than 90 days
emperator ir cache prune --older-than 90
```

Expected output:

```bash
✓ Removed 42 old cache entries
```

### Clearing Cache

Clear all cache data:

```bash
emperator ir cache clear
```

Use cases:

- After Emperator version upgrade
- When debugging cache issues
- To reclaim disk space
- Before fresh analysis

### Monitoring Disk Usage

Check cache size:

```bash
du -sh .emperator/ir-cache
```

Typical sizes:

- Small project (100 files): ~100 KB
- Medium project (1K files): ~1 MB
- Large project (10K files): ~10 MB

## Performance Tips

### When Cache Helps Most

✅ **High benefit:**

- Large codebases (>1000 files)
- Frequent small changes
- CI/CD with cache persistence
- Development with hot reload

❌ **Limited benefit:**

- Single file analysis
- Complete repository rewrites
- First-time setup
- Very small projects (\<100 files)

### Optimizing Cache Hit Rate

**Best practices:**

1. **Parse before major changes**: Build cache on stable state
1. **Commit .gitignore for cache**: Add `.emperator/ir-cache/` to `.gitignore`
1. **Use in CI**: Share cache across runs
1. **Prune regularly**: Remove stale entries weekly

**Factors affecting hit rate:**

| Factor                | Impact on Hit Rate  |
| --------------------- | ------------------- |
| File modifications    | ❌ Lower (expected) |
| Git branch switching  | ❌ Lower (expected) |
| Code generation       | ❌ Lower            |
| Documentation changes | ✅ Higher           |
| Test-only changes     | ✅ Higher           |

### Storage Location

**Default:** `.emperator/ir-cache/`

**Custom location:**

```python
from emperator.ir import IRBuilder

builder = IRBuilder(cache_dir=Path('/tmp/ir-cache'))
```

**Considerations:**

- Use fast SSD for cache storage
- Avoid network filesystems (high latency)
- Ensure sufficient disk space
- Consider tmpfs for very fast access

## Troubleshooting

### Cache Not Being Used

**Symptoms:**

- Cache hit rate always 0%
- Parse time doesn't improve on re-run

**Diagnosis:**

```bash
# Check if cache exists
ls -la .emperator/ir-cache/

# Check manifest
cat .emperator/ir-cache/manifest.json | jq
```

**Common causes:**

1. **Files modified**: Content hash changed (expected)
1. **Cache cleared**: Manual or automatic cleanup
1. **Permissions**: Cache directory not writable
1. **Schema mismatch**: Emperator version changed

**Solutions:**

```bash
# Rebuild cache
emperator ir parse --language python

# Check permissions
chmod -R u+w .emperator/ir-cache/

# Clear and rebuild
emperator ir cache clear
emperator ir parse --language python
```

### Slow Cache Operations

**Symptoms:**

- Cache save/load takes seconds
- Disk I/O spikes during parse

**Diagnosis:**

```bash
# Check cache size
du -sh .emperator/ir-cache/

# Check file count
find .emperator/ir-cache/files -name "*.msgpack" | wc -l
```

**Common causes:**

1. **Slow disk**: HDD or network filesystem
1. **Many files**: >10K cached files
1. **Large files**: Individual files >1MB

**Solutions:**

```bash
# Prune old entries
emperator ir cache prune --older-than 30

# Move cache to faster storage
mv .emperator/ir-cache /tmp/ir-cache
emperator ir parse --language python  # TODO: support custom cache dir

# Consider excluding large auto-generated files
echo "generated/*" >> .gitignore
```

### Cache Corruption

**Symptoms:**

- Error reading cache manifest
- MessagePack deserialization failures
- Incomplete symbol data

**Diagnosis:**

```bash
# Validate manifest JSON
python -m json.tool .emperator/ir-cache/manifest.json

# Check for corrupted msgpack files
for f in .emperator/ir-cache/files/*.msgpack; do
    python -c "import msgpack; msgpack.unpackb(open('$f','rb').read())" || echo "Corrupted: $f"
done
```

**Solutions:**

```bash
# Clear corrupted cache
emperator ir cache clear

# Rebuild from scratch
emperator ir parse --language python

# If persistent, report bug with:
# - Emperator version (emperator --version)
# - Cache manifest (redacted)
# - Error message
```

### High Memory Usage

**Symptoms:**

- Python process using >1GB RAM
- Out of memory errors on large codebases

**Diagnosis:**

```bash
# Monitor memory during parse
/usr/bin/time -v emperator ir parse --language python
```

**Common causes:**

1. **Many concurrent parses**: Parallel parsing (planned)
1. **Large parse trees**: Files >10K lines
1. **Memory leak**: Report bug if grows unbounded

**Solutions:**

```bash
# Parse in smaller batches (manual workaround)
for dir in src/module1 src/module2; do
    cd $dir && emperator ir parse --language python
done

# Increase system memory
# Or wait for streaming parser (v2.0)
```

## Advanced Usage

### Programmatic Access

Use IR from Python code:

```python
from pathlib import Path
from emperator.ir import IRBuilder, CacheManager

# Initialize builder with cache
cache_dir = Path('.emperator/ir-cache')
builder = IRBuilder(cache_dir=cache_dir)

# Parse directory
snapshot = builder.parse_directory(
    root=Path('src'),
    languages=('python',)
)

# Access results
print(f"Parsed {snapshot.total_files} files")
print(f"Cache hit rate: {snapshot.cache_hit_rate:.1f}%")

for file in snapshot.files:
    print(f"\n{file.path}:")
    for symbol in file.symbols:
        print(f"  {symbol.kind.value}: {symbol.name}")

# Save to cache
manager = CacheManager(cache_dir)
manager.save_snapshot(snapshot)
```

### Incremental Updates

For watch mode or real-time analysis:

```python
from pathlib import Path
from emperator.ir import IRBuilder

builder = IRBuilder(cache_dir=Path('.emperator/ir-cache'))

# Initial parse
initial = builder.parse_directory(root=Path('src'), languages=('python',))

# Later, update only changed files
changed_files = (
    Path('src/module.py'),
    Path('src/util.py'),
)

updated = builder.incremental_update(
    changed_files=changed_files,
    previous_snapshot=initial,
)

print(f"Cache hits: {updated.cache_hits}")
print(f"Cache misses: {updated.cache_misses}")
```

### Custom Symbol Extraction

Extend symbol extraction for your needs:

```python
from emperator.ir import SymbolExtractor, Symbol, SymbolKind

class CustomExtractor(SymbolExtractor):
    def extract_symbols(self, tree, language):
        # Start with default extraction
        symbols = list(super().extract_symbols(tree, language))

        # Add custom logic
        if language == 'python':
            # Extract decorators, docstrings, etc.
            pass

        return tuple(symbols)

# Use custom extractor
builder = IRBuilder()
builder._symbol_extractor = CustomExtractor()
```

## Best Practices

### Do's

✅ Add `.emperator/ir-cache/` to `.gitignore`\
✅ Prune cache regularly (weekly or monthly)\
✅ Use cache in CI/CD with build system cache\
✅ Parse on stable branches for best hit rate\
✅ Monitor cache size and set up alerts

### Don'ts

❌ Don't commit cache to version control\
❌ Don't rely on cache for correctness (always validate)\
❌ Don't use cache on network filesystems\
❌ Don't skip pruning (unbounded growth)\
❌ Don't edit cache files manually

## Next Steps

- [IR Format Reference](../reference/ir-format.md)
- [IR Architecture](../explanation/ir-architecture.md)
- [Sprint 4 Plan](../explanation/sprint-4-ir-analysis.md)
- [Analysis Integration](../explanation/sprint-4-ir-analysis.md#semgrep-integration)

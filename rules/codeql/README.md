# CodeQL Packs

Collect custom CodeQL queries or packs that target Emperator-specific anti-patterns. Keep `qlpack.yml`
metadata up to date as queries evolve.

## Query categories

- `security-queries.ql` bans dangerous primitives (`eval`, `exec`) and flags likely secret leaks.
- `dataflow-queries.ql` demonstrates taint tracking into `os.system`.
- `architecture-queries.ql` enforces layering boundaries between domain and API modules.

Regenerate CodeQL databases and execute packs with the CLI commands documented in
[`docs/how-to/develop-codeql-queries.md`](../../docs/how-to/develop-codeql-queries.md).

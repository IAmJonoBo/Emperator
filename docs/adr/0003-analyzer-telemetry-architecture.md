# ADR-0003: Analyzer Telemetry Architecture and Caching Strategy

- **Status:** Accepted
- **Date:** 2025-10-15
- **Deciders:** Core maintainers, Emperator automation lead
- **Consulted:** Platform engineering, Security reviewers
- **Tags:** Telemetry, Tooling, Observability

## Context

Analyzer execution currently surfaces recommended commands but provides no durable record of what
actually ran, how long it took, or whether results can be reused. The hardening sprint prioritises a
telemetry model that captures run metadata, enables cache-aware short-circuiting, and prepares for
future persistence work without introducing storage lock-in today.

Requirements:

- Capture per-command metrics (exit codes, durations, configuration hints) alongside aggregate
  metadata for an analyzer plan.
- Provide a stable fingerprint that invalidates cached runs when project structure, tooling state, or
  analyzer steps change.
- Offer an injectable persistence seam so future storage backends (JSONL, SQLite, remote services)
  can be adopted without refactoring the CLI entrypoints.
- Maintain privacy: telemetry defaults to local storage under the repository unless explicitly
  redirected, avoiding accidental exfiltration of SARIF payloads or proprietary code paths.

## Decision

Introduce first-class telemetry primitives inside `emperator.analysis`:

1. **Telemetry data model** — `TelemetryEvent` captures per-command data, while `TelemetryRun`
   aggregates a full plan execution, including duration calculations, success heuristics, and freeform
   notes for cache provenance.
1. **Pluggable store contract** — `TelemetryStore` defines the persistence protocol. A simple
   `InMemoryTelemetryStore` implementation unblocks tests and CLI prototypes, while future commits can
   layer durable stores without breaking callers.
1. **Deterministic fingerprinting** — `fingerprint_analysis(...)` normalises language detection output,
   tool availability, analyzer steps, and optional metadata into a SHA-256 digest. The fingerprint keys
   persistence lookups and doubles as a cache invalidation mechanism when plans drift.
1. **Designated storage path** — Subsequent persistence work will default to
   `.emperator/telemetry/*.jsonl`, retaining one JSON-L lines file per fingerprint with rolling history
   limits. The directory lives in `.gitignore` to keep telemetry local by default.
1. **CLI integration roadmap** — The CLI will accept `--telemetry-store` hooks, default to the in-memory
   implementation for dry-runs, and persist to disk when the JSONL backend lands. Historical runs will
   hydrate “last seen” banners in `emperator analysis plan` output.

## Consequences

- Analyzer tooling can begin emitting structured telemetry immediately, enabling unit tests to guard
  against regressions in the cache surface area.
- Future storage implementations only need to honour the `TelemetryStore` protocol, keeping changes
  additive and low-risk.
- The deterministic fingerprint gives developers a single source of truth when deciding to re-run heavy
  analyzers, reducing redundant work.
- Local-only defaults respect privacy while leaving room for opt-in remote uploads documented in later
  ADRs.

## Implementation Notes

- Unit tests assert that fingerprints change when analyzer commands differ and that the in-memory store
  retains chronological history.
- The CLI will thread fingerprints into progress output, enabling quick comparisons between planned and
  cached runs.
- Guardrails for regenerated YAML artefacts will hook into the same telemetry surface, recording whether
  formatters were re-run before commits land.

## Status Log

- 2025-10-15 — Accepted with initial in-memory store and fingerprint helper to unblock persistence
  follow-up work.

## References

- Next_Steps.md (Telemetry tasks)
- `src/emperator/analysis.py` (Telemetry primitives and fingerprint helper)

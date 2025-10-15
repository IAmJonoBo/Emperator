# ADR-0001: Adopt a Repository-wide ADR Process

- **Status:** Accepted
- **Date:** 2025-10-15
- **Deciders:** Core maintainers, Emperator automation lead
- **Consulted:** Documentation maintainers, Contract governance reviewers
- **Tags:** Process, Governance

## Context

The repository lacked an authoritative log for architectural and governance decisions. Previous
changes relied on ad-hoc references in `Next_Steps.md` or inline comments, making it difficult to
trace rationale, consult stakeholders, or evaluate whether a decision still holds. The current sprint
introduces multiple strategic shifts (hardened tooling, telemetry planning) that require durable
context.

## Options Considered

### 1. Continue without ADRs

- **Pros:** No new process overhead.
- **Cons:** Decisions remain tribal knowledge; onboarding new contributors stays slow; auditors lack a
  single source for rationale.

### 2. Lightweight changelog entries only

- **Pros:** Minimal documentation effort.
- **Cons:** Changelogs emphasise outcomes, not decision drivers or rejected alternatives. They are not
  easily cross-linked with governance controls.

### 3. Dedicated ADR log (selected)

- **Pros:** Standard practice for architectural governance, easy to index, and compatible with the
  Diátaxis documentation structure.
- **Cons:** Requires discipline to maintain.

## Decision

Adopt a formal ADR workflow under `docs/adr/`. Each decision receives a numbered record following the
`0000-template.md` structure, including context, options, decision, consequences, implementation
notes, and a status log. ADRs are required for architectural changes, tooling shifts, and governance
updates that affect contracts or developer workflows.

## Consequences

- Creates a durable audit trail linked from governance documentation and contracts.
- Adds light process overhead for significant changes but improves review quality.
- Enables future supersession when decisions evolve, avoiding stale documentation.

## Implementation Notes

- Store new ADRs in `docs/adr/` with zero-padded prefixes and descriptive slugs.
- Reference the ADR in related PR descriptions, contract updates, or documentation.
- Update `docs/mkdocs.yml` and governance pages to surface the ADR index for discoverability.

## Status Log

- 2025-10-15 — Drafted and accepted during the code-hardening sprint kickoff.

## References

- [docs/adr/0000-template.md](0000-template.md)
- [docs/adr/README.md](README.md)

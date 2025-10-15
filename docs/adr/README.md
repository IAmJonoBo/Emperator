# Architecture Decision Records

The ADR log documents why Emperator makes significant architectural, tooling, and process choices.
Every record follows the numbering convention `NNNN-short-slug.md` so decisions sort chronologically
and remain easy to reference from the contract, docs, and code comments.

## Workflow

1. Draft decisions in collaboration with the stakeholders noted in the template.
1. Store working notes in the `Context` and `Options Considered` sections so reviewers understand the
   data behind the decision.
1. Once accepted, update the `Status` field and record the outcome in the `Status Log`.
1. If a decision is replaced, mark it as superseded and link to the newer ADR.

See `0000-template.md` for the canonical structure and metadata expectations. All new ADRs should be
committed alongside supporting tests, contract updates, or documentation changes that enforce the
decision.

## Index

- [ADR-0001: Adopt a Repository-wide ADR Process](0001-adopt-adr-process.md)
- [ADR-0002: Sprint Focus on Code Hardening and Analyzer Telemetry](0002-code-hardening-and-telemetry.md)
- [ADR-0003: Analyzer Telemetry Architecture and Caching Strategy](0003-analyzer-telemetry-architecture.md)

# Project Contract

This area captures the executable agreement that keeps Emperator implementations aligned across teams.

## Layout

- `api/` — machine-readable interface definitions (OpenAPI, GraphQL, or gRPC) shared with integrators.
- `policy/` — OPA/Rego policies that encode governance and guardrails.
- `conventions/` — CUE schemas constraining naming, resource layouts, and other structural contracts.
- `generators/` — scaffolding templates or recipes used to bootstrap new components from the contract.

Add documentation or diagrams alongside artifacts when clarity helps downstream users.

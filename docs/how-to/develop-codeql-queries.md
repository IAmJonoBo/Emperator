# Develop CodeQL Queries

This guide documents the local workflow for extending Emperator's CodeQL packs.

## Prerequisites

- Install the [CodeQL CLI](https://codeql.github.com/docs/cli/) and ensure the `codeql`
  executable is on your `PATH`.
- Synchronise dependencies via `./scripts/setup-tooling.sh` so Python and Node helpers are
  available.
- Familiarise yourself with the repository structure described in `docs/reference/toolchain.md`.

## Directory layout

Custom CodeQL content lives in `rules/codeql/`:

- `qlpack.yml` – metadata describing the query pack and its dependencies.
- `queries/` – individual `.ql` files grouped by category (security, dataflow, architecture).
- `README.md` – short description of the pack and maintenance notes.

## Authoring workflow

1. Create a new query file inside `rules/codeql/queries/` with a descriptive name.
1. Follow the header conventions used in the existing queries (`@name`, `@description`,
   `@kind`, `@problem.severity`, and `@tags`).
1. Use the appropriate CodeQL libraries (`import python`,
   `import semmle.python.security.dataflow.TaintTracking`, etc.) depending on the scenario.
1. Run `emperator analysis codeql create --language python` to build a database for the
   project under analysis.
1. Execute the query pack: `emperator analysis codeql query --database <db-path>`.
1. Inspect the rendered findings table or review the generated SARIF report.
1. Add unit tests covering the new behaviour (see `tests/test_codeql.py`).
1. Document the change in the sprint notes or architecture docs when relevant.

## Validation checklist

- [ ] Queries compile locally via the CodeQL CLI.
- [ ] SARIF output highlights the intended location and includes remediation guidance.
- [ ] The new query is referenced in documentation or training material when applicable.
- [ ] Existing automation (`analysis plan`, `analysis run`) continues to succeed.

## Troubleshooting

- If the CLI reports missing libraries ensure the `qlpack.yml` lists the correct
  `libraryPathDependencies`.
- When resolving complex dataflow scenarios, extend `TaintTracking::Configuration` and
  override `isSource`/`isSink` predicates to describe the flow precisely.
- Use `--debug --verbosity=3` when calling the CodeQL CLI to inspect command execution.

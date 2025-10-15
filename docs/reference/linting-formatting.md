# Linting and Formatting Reference

The Emperator toolchain enforces a single, opinionated set of style and hygiene rules across every
language we touch. This reference explains the checks we run, how they are configured, and why each
choice supports the architectural conventions documented elsewhere in the brief. Use it when
bootstrapping a new environment, extending the stack, or deciding how to deviate from the default
settings.

## Quick matrix

| Domain | Primary tool | Configuration | What it guarantees |
| --- | --- | --- | --- |
| JavaScript / TypeScript / JSON / CSS / HTML | [Biome 2.2.6](https://biomejs.dev/) | `biome.json` | Fast formatter + linter with strict defaults, consistent JSON/CSS/HTML wrapping, ignores generated assets |
| JavaScript / TypeScript (semantic) | [ESLint 9](https://eslint.org/) + `eslint-plugin-import` | `eslint.config.js` | Module graph hygiene, import sorting, complements Biome with type-aware rules |
| Python | [Ruff](https://docs.astral.sh/ruff/) | `pyproject.toml` (`[tool.ruff]`) | PEP8-aligned formatting, lint bundles (`E`, `F`, `I`, `W`, `UP`, `B`, `C90`), fixes applied by default |
| YAML | [yamllint](https://yamllint.readthedocs.io/) + `scripts/format-yaml.mjs` | `.yamllint` + `pnpm fmt` | Enforces 2-space indentation, sequence alignment, YAML formatter mirrors Biome defaults |
| GitHub Actions | [actionlint](https://github.com/rhysd/actionlint) | pre-commit hook | Validates workflow syntax, catches unused inputs, ensures indentation |
| Shell | [shfmt](https://github.com/mvdan/sh) | Pre-commit args `-w -i 2 -bn -ci` | Enforces POSIX shell formatting with 2-space indents |
| Universal hygiene | pre-commit hooks | `.pre-commit-config.yaml` | Trailing whitespace, missing EOF newlines, prevents macOS metadata from entering Git |
| Commits | [commitlint](https://commitlint.js.org/) | `package.json` `commitlint` block | Conventional commits for changelog + automation |

The `scripts/setup-tooling.sh` entry point wires everything together for both local developers and
CI. Running `bash scripts/setup-tooling.sh` installs Python + Node dependencies, installs
pre-commit hooks, and executes the full lint pipeline. `bash scripts/setup-tooling.sh --ci` skips
mutating steps and is the command we expect in automation.

## JavaScript and friends: Biome + ESLint

Biome acts as the first line of defence for every web asset. The configuration in `biome.json`
mirrors the installed version (2.2.6) to avoid schema drift and enables Biome's recommended linting
profile. Key decisions:

- **Formatting rules** &mdash; JS/TS use double quotes, trailing commas follow the `es5` style, HTML/CSS
  respect a 100 character line width. These defaults align with our documentation theme and keep
  diffs tight across auto-generated snippets.
- **Ignored paths** &mdash; We explicitly drop MkDocs output (`site/`), pnpm cache,
  Python virtualenvs, minified bundles, and macOS `._*` resource forks. Biome previously surfaced IO
  errors on Apple metadata files; excluding them keeps the pipeline green on macOS.
- **Global formatter defaults** &mdash; The `formatter` block sets the global indentation and line width
  (two-space indent, 100 character width) so any future Biome-supported language inherits the same
  layout without additional overrides.
- **Maximum file size** &mdash; Large bundles (>1 MiB) are skipped to ensure deterministic performance in CI.

Biome runs via two scripts:

- `pnpm fmt` delegates to `scripts/run-format.mjs`, which formats YAML (`scripts/format-yaml.mjs`),
  runs `biome format --write .`, then executes `uv run ruff format .` followed by
  `uv run ruff check . --select I --fix` to keep Python sources aligned and imports sorted. Append
  `--all` to include a full `uv run ruff check . --fix` sweep after the import-only pass. Install
  `uv` (or run `scripts/setup-tooling.sh`) before invoking the formatter so the Ruff commands are
  available.
- `pnpm check` executes `biome check .` without writes and is the first half of `pnpm lint`.

ESLint supplements Biome with rules that require type/module awareness. `eslint.config.js` imports
ESLint's flat config plus the TypeScript preset from `typescript-eslint` and the [`eslint-plugin-import`](https://github.com/import-js/eslint-plugin-import) package. Rationale:

- **Module hygiene** &mdash; We enforce alphabetical import ordering and a newline after import groups to
  keep service modules readable.
- **Environment globals** &mdash; `globals.browser` and `globals.node` mirror the hybrid runtime our
  scripts target (CLIs plus front-end docs tooling).
- **Ignored paths** &mdash; Matches Biome's exclusions and adds `.venv/`, `.pnpm-store/`, and coverage
  reports so ESLint never inspects generated output.

Run ESLint with `pnpm lint:eslint`. The combined `pnpm lint` script now runs `pnpm lint:ruff`,
`pnpm check` (Biome), and `pnpm lint:eslint`, guaranteeing Ruff, Biome, and ESLint all pass before
CI greenlights a change.

## YAML style enforcement: format script + yamllint

Biome does not yet format YAML, so we layer dedicated tooling on top:

- `pnpm fmt` runs `scripts/format-yaml.mjs` before invoking Biome. The script recursively walks the
  repository (respecting the same ignore paths as the rest of the toolchain), round-trips tracked
  `.yml`/`.yaml` documents through the [`yaml`](https://eemeli.org/yaml/) serializer with a two-space indent and
  120-character line width, and rewrites files when changes are detected. The YAML stringifier
  preserves comments and key order, so configuration files remain human-friendly.
- `yamllint` runs inside pre-commit (and therefore `scripts/setup-tooling.sh`) with the
  configuration defined in `.yamllint`. It enforces two-space indentation, consistent sequence
  padding, safe booleans, and a 120-character line limit that keeps MkDocs configuration readable.

The formatter + linter pairing keeps YAML documents aligned with the rest of the stack until Biome
adds native support. Update this section if we migrate away from the custom formatter or wire it
into additional automation.

### Customising the JS/TS toolchain

1. **Extend Biome rules** by editing `biome.json`. The schema link at the top keeps IDE validation in
   sync; use Biome's `migrate` subcommand after upgrades.
2. **Add ESLint plugins** by updating `devDependencies` and the `plugins` block inside
   `eslint.config.js`. Remember to document new rules in this reference.
3. **Generated assets** should be ignored in both tools to avoid slow linting and CI noise.

## Python: Ruff-first workflow

Python style enforcement lives in `pyproject.toml`:

- **Targets Python 3.11** to match our runtime requirement.
- **Line length 100** aligns with the JS/CSS width, so prose and code patches remain consistent.
- **Lint bundles** cover the most common error classes (`E`, `F`, `I`, `W`) plus modernization (`UP`),
  bugbear (`B`), and complex comprehension checks (`C90`).
- **Formatter integration** (`ruff format`) honours single quotes to match our FastAPI templates.
- **Exclusions** mirror the non-source directories Biome ignores, keeping the mental model aligned.

Ruff runs through two pre-commit hooks (`ruff` with `--fix` and `ruff-format`) so developers receive
fast feedback before code lands in the repository. When working outside pre-commit you can run the
tools directly from the managed virtualenv:

```bash
source .venv/bin/activate
ruff check .
ruff format .
```

Alternatively, use the project script `pnpm lint:ruff` to execute `uv run ruff check .` without
manually activating the virtualenv; `pnpm fmt` now calls the Ruff formatter and import sorter in the
same pass.

Because `scripts/setup-tooling.sh` drives `uv lock`/`uv sync`, the project-managed `.venv/` always
has the right version of Ruff and the dev dependencies on the path.

### Type checking and tests

While not strictly formatting, `mypy` and `pytest` ship in the `dev` extra. Run them via the
virtualenv created in `.venv`:

```bash
source .venv/bin/activate
mypy src/emperator
pytest
```

Documenting these commands here helps future maintainers understand the expectations baked into the
Python portion of the stack.

## Universal hygiene via pre-commit

`.pre-commit-config.yaml` stitches every formatter and linter together. Highlights:

- `pre-commit-hooks` prevents whitespace regressions and filename clashes.
- `yamllint` (driven by `.yamllint`) guards our MkDocs configuration and GitHub workflows with strict two-space indentation and safe boolean values while Biome awaits first-party YAML formatting.
- `shfmt` keeps shell scripts consistent with `set -euo pipefail` defaults.
- `actionlint` validates GitHub Actions syntax, unused inputs, and indentation before we push workflows.
- Local hooks `cleanup-apple-cruft` / `ban-apple-cruft` remove macOS Finder artefacts before they can
  be committed.
- Biome, ESLint, Ruff, and commitlint all run through pre-commit, so developers get identical checks
  to CI.

Install the hooks automatically with `scripts/setup-tooling.sh` (development mode) or manually via
`pre-commit install --install-hooks`.

## Commit hygiene: Commitlint

Commit messages must follow the Conventional Commits schema. `pnpm commitlint --edit` is wired as a
`commit-msg` hook and reuses the `@commitlint/config-conventional` preset declared in
`package.json`. This keeps release notes and CI workflows deterministic. We extend the type allowlist
to include `fmt` for formatter-only commits driven by `pnpm fmt`, aligning automation terminology
with the scripts documented earlier in this guide.

## Extending or diverging from the defaults

- **Change detection** &mdash; Update this document whenever you modify linting or formatting behaviour.
- **Project variants** &mdash; If a downstream consumer needs different rules, duplicate the relevant
  config file and adjust pre-commit to run an alternative command set.
- **Upgrades** &mdash; For Biome or ESLint, upgrade the dependency in `package.json`, run the respective
  migration commands (`pnpm biome migrate`, `npx eslint --print-config` diffing), and validate with
  `scripts/setup-tooling.sh --ci` before merging.
- **CI integration** &mdash; Any pipeline should call `bash scripts/setup-tooling.sh --ci` to reproduce the
  exact checks documented here.

Keeping this reference current ensures every contributor understands both the _what_ and the _why_
behind our style gate, and makes it easy to reproduce the setup in future Emperator-aligned
repositories.

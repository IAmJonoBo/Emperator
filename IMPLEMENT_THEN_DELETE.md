A few concrete ways we could evolve the lint/format lane without adding churn:

Differentiate quick vs. deep passes. Keep the current pre-commit run --all-files for setup, but add a pnpm lint:changed (or uv run ruff check --fix $(git diff --name-only HEAD) style helper) that only inspects staged files. Contributors get near-instant feedback while still running the full suite in CI.

Surface SARIF everywhere. We already upload SARIF in CI, but we can wire pnpm lint to emit SARIF locally (ruff check --output-format sarif, eslint --format sarif, biome check --reporter sarif). Combining those into .sarif bundles keeps review tools (VS Code, GitHub’s security tab) consistent across lanes.

Cache hook environments aggressively. Document (or bake in) PRE_COMMIT_HOME=$REPO/.cache/pre-commit and UV_CACHE_DIR, then add pnpm run cache:prune helpers. Fast, deterministic caches make pre-commit “feel” lighter, so people won’t skip it.

Tighten docs formatting. Biome still ignores Markdown/YAML docs. We could add mdformat or enable Biome’s Markdown preview build once stable, then rely on format-yaml.mjs plus yamllint only for real YAML. That reduces false positives like the ones we just fought.

Adopt Ruff rule packs deliberately. Moving from the default ["E","F","I","W","UP","B","C90"] to Ruff’s higher-level presets (lint.select = ["ALL"] with targeted ignore) gives better signal for things like security or perf regressions. Pair it with ruff format to reduce the number of tools touching Python.

Biome + ESLint responsibilities. Now that Biome covers most syntax rules, consider letting ESLint focus purely on plugin-based policies (e.g., import boundaries) and run it in --max-warnings=0 --cache. A companion .eslintcache (ignored) speeds up reruns.

Add contextual hints. Extend linting-formatting.md with “what to do when X fails” sections (e.g., common Ruff violations, Biome fix flags). Hook those into pre-commit output via pre-commit’s fail_fast messages or additional_dependencies to teach the fix path.

Enable automated PR hints. Pre-commit.ci or GitHub Actions pre-commit jobs can comment on PRs with autofix suggestions. It keeps reviewers focused on architecture while the bot comments on style nits. If we prefer self-hosted, setup-linting.sh could upload diff patches as artifacts for go/no-go decisions.

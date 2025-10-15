# Emperator Agent Handbook

This guide aligns every automation agent (Copilot, local LLMs, bespoke scripts) with the workflows
and guardrails that keep the Emperator repository compliant with its contract-driven standards.
Use it alongside `.github/copilot-instructions.md`, the references under `docs/`, and the
project contract itself. Update this file whenever architecture, tooling, or governance rules
change.

## Mission and Operating Principles

- Treat the Project Contract (`contract/`) as the source of truth. Implementation, docs, and policy
  updates must stay in lockstep with contract changes.
- Follow the Propose → Rank → Validate safety loop from
  `docs/explanation/ai-orchestration.md`: no automated patch is trusted until static analysis,
  tests, and formatters all pass.
- Prefer deterministic codemods (LibCST/OpenRewrite) and existing scripts before crafting ad-hoc
  shell pipelines.
- Keep automation local-first and offline-friendly per `docs/explanation/security-safety.md`. Do
  not call external APIs unless the task explicitly permits it.
- Never modify generated artefacts (`site/`, `dist/`, `src/emperator.egg-info/`) or macOS metadata
  (`._*`, `.DS_Store`). Regenerate instead via documented scripts.
- Escalate to a maintainer when requirements are unclear, a rule conflicts with observed reality,
  or safety tiers (`formatting`, `low`, `medium`, `high`) are ambiguous.

## Repository Map

| Path | Intent | Agent Notes |
| --- | --- | --- |
| `src/emperator/` | FastAPI app, Typer CLI, helpers | Keep modules small, add tests under `tests/`. |
| `contract/` | Contract assets (CUE, Rego, OpenAPI, codemods) | Run `cue fmt`, `cue vet`, `opa fmt`, `opa eval` before committing. |
| `docs/` | MkDocs sources | Format with `pnpm fmt`, validate with `mkdocs build --strict` + `lychee`. |
| `infra/`, `compose/` | Kubernetes, Terraform, Docker | Respect IaC conventions; run toolchain lint as documented. |
| `scripts/` | Bootstrap and lint helpers | Prefer invoking these scripts; keep them POSIX-sh compatible. |
| `tests/` | Pytest suite covering CLI, contract scaffolding | Add coverage for new behaviour and contract rules. |

## Standard Workflow for Automation

1. **Collect context.** Read relevant contract sections, docs (especially under
   `docs/reference/`), and existing implementation before planning a change.
2. **Plan aloud.** Share a concise execution plan with the requester before editing files.
3. **Use official bootstrap commands:**
   - `./scripts/setup-tooling.sh` (or `pnpm run setup:tooling`) prepares both Python and Node lanes.
   - `pnpm run setup:lint` installs JS tooling and runs the formatter/lint suite.
4. **Implement with guardrails.** Keep diffs minimal, add succinct comments only when the intent
   would otherwise be unclear, and respect the 100-character guideline where practical.
5. **Sync contract + docs.** When a rule, generator, or policy changes, update:
   - `docs/reference/contract-spec.md`
   - `docs/includes/copilot-prompts.md`
   - Any affected how-to or explanation pages (e.g., developer experience, governance).
6. **Validate before handing off:**
   - `pnpm fmt` (includes YAML formatter, Biome, Ruff format/import sort)
   - `pnpm lint` (Ruff check, Biome check, ESLint)
   - `uv run pytest`
   - `uv run mypy src`
   - `mkdocs build --strict` for docs-heavy changes
   - `lychee --config .lychee.toml docs` when touching links
   - `emperator apply --diff --no-commit` (or `--strict` in CI-critical flows)
7. **Report outcomes.** Surface command summaries and residual risks. Call out skipped steps and
   justify them.

## Contract Change Checklist

- Update CUE schemas, Rego policies, and OpenAPI specs together; run `cue fmt`, `cue vet`,
   `opa fmt`, and `opa eval` against representative input before committing.
- Record new rules, severity tiers, and evidence in `contract/README.md` and
   `docs/reference/contract-spec.md`.
- Provide examples and prompt adjustments in `docs/includes/copilot-prompts.md` so assistants stay
   aligned with the latest expectations.
- Use `emperator apply --diff --no-commit --fast` to preview enforcement, then `--strict` once
   satisfied. Document any exemptions or staged rollouts.

## Documentation Standards

- Author only in `docs/`; rebuild static output via MkDocs CI jobs. Never hand-edit `site/`.
- Format prose with `pnpm fmt`; ensure tables remain pipe-aligned and diagrams use Mermaid blocks.
- Run `mkdocs build --strict` plus link linting after meaningful docs updates. Capture broken link
     fixes in the same change set.
- Reference related guides (`developer-tooling`, `toolchain`, `governance`) when new procedures are
     introduced.

## AI and Codemod Guidance

- Honour safety tiers: auto-apply only `formatting` and `low` tier results; surface `medium`/`high`
   as reviewable diffs with provenance comments (model name, prompt hash).
- Follow the prompt patterns in `docs/includes/copilot-prompts.md` when interacting with AI
   assistants or generating new prompt packs.
- Capture rejected AI outputs to refine prompts or escalate for human review. Where a pattern is
   repeatable, graduate it into a deterministic codemod under `contract/generators/` with tests.

## Commit and Review Hygiene

- Use Conventional Commits (`type: scope? subject`). Allowed types include the conventional set plus
   `fmt` for formatter-only commits. Document multi-area changes with separate
   commits when possible.
- Ensure pre-commit hooks are installed (`pre-commit install --install-hooks`) if the automation
   environment supports it.
- Include validation notes in summaries (commands run, artefacts uploaded) so reviewers can audit
   the change quickly.
- Never rewrite or discard user-authored changes outside the task scope. If unexpected diffs appear,
   pause and request guidance.

## Escalation and Maintenance

- When in doubt, gather context and ask. Do not guess at contract intent or override safety
   measures.
- Keep this handbook current: update it after notable migrations, tooling upgrades, or new
   governance processes. Mention AGENTS.md updates in PR descriptions so downstream consumers know
   to refresh their local context.

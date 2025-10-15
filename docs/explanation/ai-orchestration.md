# AI-Orchestrated Refactoring

Optional AI assistance augments Emperator’s deterministic pipeline when rule-based codemods are insufficient, while strict validation keeps proposals safe.

## Propose → rank → validate workflow

1. **Propose:** Emperator crafts prompts with rule context, offending code, and acceptance tests to solicit candidate patches from a local LLM.
1. **Rank:** Contract-aware heuristics (diff size, naming compliance, static lint) filter and order candidates before deeper checks.
1. **Validate:** The leading candidate is applied in a scratch workspace, rerun through Emperator’s full analysis suite, and optionally tested. Only clean results surface to developers.

## Local-first model strategy

- Favors on-prem, open-weight models such as Code Llama, StarCoder, or Phi-3 to avoid leaking proprietary code.
- Stores model metadata, prompt hashes, and outputs for provenance so reviewers know when AI contributed to a change.
- Allows teams to swap or fine-tune models as new, higher-quality releases appear without altering the orchestration layer.

## Use cases

- Complex deprecations where templated codemods fall short; AI suggests migrations that preserve behaviour and formatting.
- Contract-driven scaffolding (e.g., generating controller stubs from OpenAPI paths) beyond simple text templates.
- Documentation upkeep, such as drafting docstrings or changelog entries tied to rule updates for human refinement.

## Guardrails against hallucinations

- AI-generated diffs must satisfy the same static analysis, tests, and safety tier checks as human-authored code; failures discard the suggestion.
- Provenance comments embed model version and prompt id, enabling audits and post-mortem analysis.
- Teams can restrict AI usage to advisory mode, requiring manual application of any suggested patches.

## Continuous improvement

- Capture rejected proposals to refine prompts, adjust model temperature, or retrain with organization-specific patterns.
- Package successful AI-assisted migrations as formal codemod recipes so future occurrences bypass the model entirely.

With a tightly controlled feedback loop, AI becomes a force multiplier for large-scale refactors without weakening Emperator’s compliance and safety guarantees.

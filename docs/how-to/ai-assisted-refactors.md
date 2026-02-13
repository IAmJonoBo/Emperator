# Using AI-Assisted Refactors Safely

Emperator’s deterministic codemods cover common rules, but some refactors benefit from context-aware suggestions. This guide explains how to enable local LLM support and keep every AI-generated change within Emperator’s safety envelope.

## 1. Enable local models

- Install an open-source code-capable model (e.g., Code Llama, StarCoder, Phi-3) that fits your security requirements. Keep weights on-prem to avoid leaking proprietary code.
- Configure Emperator’s AI bridge via `emperator ai init --model path/to/model.gguf --max-tokens 1024`. This stores model metadata in `.emperator/config.yaml`.
- Set `EMPERATOR_AI_ENABLED=1` in your environment to opt in.

````yaml title=".emperator/config.yaml"
ai:
    provider: local
    model_path: /models/code-llama-13b.gguf
    context_window: 32768
    temperature: 0.15
    stop_sequences:
        - "```"
        - "# end"
````

## 2. Follow the propose → rank → validate loop

```mermaid
flowchart LR
  A[Static analysis finding] --> B[LLM prompt builder]
  B --> C[Generate N candidate patches]
  C --> D[Ranker
  (contract diff heuristics)]
  D --> E[Safety gate]
  E -->|passes checks| F[Apply patch + log provenance]
  E -->|fails| G[Discard + surface manual TODO]
```

The loop guarantees that AI assistance never bypasses Emperator’s core validation:

1. **Propose:** Emperator crafts a prompt with the rule description, relevant code slice, and contract snippets. It requests multiple candidates to improve diversity.
1. **Rank:** Candidates are evaluated using contract-aware heuristics (diff size, naming compliance) and quick static checks. Lower-ranked suggestions are discarded early.
1. **Validate:** The remaining candidate is applied in a scratch workspace, then Emperator re-runs static analysis and optional property-based tests. Only if everything passes does the change graduate to a formal suggestion.

## 3. Craft effective prompts

- Reference authoritative docs in the prompt payload (e.g., link to new API contract, cite policy rationale). Models perform better when given explicit constraints.
- Provide before/after code patterns for deterministic sections, keeping the AI focused on the gap you need filled.
- Include acceptance tests or assertions when possible so the validation stage can execute them immediately.

Example prompt block stored in `docs/includes/copilot-prompts.md`:

```text
You are Emperator’s refactoring planner. Transform the provided code so it complies with the contract rule: {{rule.id}} — {{rule.description}}.

Constraints:
- Maintain public signatures.
- Preserve documented side effects.
- Prefer codemodable patterns (LibCST/OpenRewrite friendly).

Return unified diff only.
```

## 4. Gate AI suggestions by safety tier

- Map each contract rule to a safety tier (`formatting`, `low`, `medium`, `high`). Allow automatic AI fixes only for `formatting` and `low`; surface `medium/high` as reviewable diffs.
- Require human approval when AI changes touch security-critical modules, persistence layers, or public API contracts.
- Log provenance (model version, prompt hash) with `emperator explain --last` so reviewers can inspect the AI context.

## 5. Test before trusting

- Run `emperator test --scope touched-files` after each accepted AI patch. Emperator can synthesize property-based tests for marked functions, providing additional assurance.
- For migrations, pair AI-generated diffs with codemod regression tests to ensure idempotence (`emperator codemod verify path/to/recipe.py`).

## Lint-aware fixes {#lint-aware-fixes}

- Keep the [Toolchain Matrix](../reference/toolchain.md#recommended-lint-and-formatter-stacks) handy so AI suggestions never fight formatter output. Apply formatters (`ruff format`, `prettier --write`, `gofmt`) immediately after accepting an AI diff to normalize style before review.
- Prefer codemod-plus-formatter combinations for deterministic cleanups; Emperator can chain Ruff/Prettier after AI changes to minimize noise in pull requests.
- When a team mandates a specific formatter (e.g., Black), configure Emperator’s safety tiers so AI fixes stop short of reformats and leave the existing formatter to resolve layout.

## 6. Maintain feedback loops

- Capture rejected suggestions to fine-tune prompts or adjust model parameters (e.g., reduce temperature to limit creative deviations).
- Periodically retrain or swap models as new open releases improve code quality metrics.
- Update the Copilot prompt include with new rule exemplars so human copilots stay aligned with the latest contract expectations.

By treating AI output as a proposal that must earn its place through the same stringent checks as manual code, you gain the productivity benefits of context-aware refactors without compromising safety.

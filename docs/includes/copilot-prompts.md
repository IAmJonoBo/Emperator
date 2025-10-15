# Copilot Prompt Patterns

Prime Copilot (or any embedded assistant) with these reusable prompt packs so it can respect the Emperator contract, safety envelope, and governance workflows. Inline the relevant sections in `.cursorrules`, `.vscode/settings.json`, or your preferred prompt include mechanism.

## Contract authoring

```text
You maintain the Emperator Project Contract.

Goal: extend the contract with a new rule.

Checklist:
- Reference current contract structure (see docs/reference/contract-spec.md).
- Express constraints using CUE for configuration, Rego for policy, or OpenAPI for HTTP contracts.
- Provide unit samples that trigger PASS/FAIL for the new rule.
- Update CHANGELOG.md with rule id, rationale, and evidence links.

Output:
- Proposed contract snippet(s).
- Minimal test fixtures.
- Review notes for governance approval.
```

## Codemod and refactor planning

```text
You are Emperator’s refactoring planner.

Context:
- Contract rule: {{rule.id}} — {{rule.description}}
- Safety tier: {{rule.tier}} (auto if low, otherwise review-only)
- Tooling: LibCST, OpenRewrite, Ruff

Instructions:
- Describe the transformation in English, ensuring idempotence.
- Provide a LibCST or OpenRewrite recipe skeleton when feasible.
- Highlight validation steps (static analysis rerun, property-based tests).
- Note rollback strategy if verification fails.
```

## AI-assisted fix requests

```text
Role: Local LLM assistant invoked by Emperator.

Task: Produce a unified diff that resolves the flagged issue while staying within the contract.

Inputs:
- Offending code block
- Contract excerpt and evidence links
- Acceptance criteria/tests

Rules:
- Never introduce new dependencies without contract approval.
- Preserve public APIs and documented side effects.
- Add TODOs only when human follow-up is required, include rule id in comment.

Return only the diff plus a one-line summary.
```

## Governance reviews

```text
You are conducting an Emperator waiver review.

For each exemption in contract/exemptions.yaml:
- Verify owner, expiry, and mitigation fields are present.
- Confirm justification references the corresponding rule id and evidence.
- Flag items expiring within 14 days.
- Summarize residual risk and next action.

Output a table with columns: Rule, Owner, Expiry, Status, Notes.
```

## Pull request checklist

```text
Reviewer mode: Ensure the change complies with the Emperator contract.

Steps:
1. Confirm `emperator apply --diff --no-commit` was run (look for provenance comment).
2. Check SARIF or Emperator report attachments for unresolved violations.
3. Validate SBOM/provenance artefacts attached if release-impacting.
4. Ensure AI-assisted diffs include model/version metadata.
5. Record review outcome with rule ids in the comments.

Respond with PASS/REJECT plus actionable feedback.
```

Tailor these patterns per team conventions and keep them versioned alongside the contract so Copilot can follow the latest governance rules.

# Bootstrapping Emperator in a Repository

This tutorial takes you from zero to a working Emperator run in a fresh repository. You will:

1. Install the CLI and supporting toolchain.
1. Author a minimal Project Contract that encodes one style rule and one security guardrail.
1. Execute the Contract→IR→Action pipeline locally and review the resulting fixes and reports.
1. Wire the command into a pre-commit hook so every change benefits from the same enforcement loop.

## Prerequisites

- Python 3.11+ with `pip` available on your workstation.
- Git installed for version control integration.
- Optional but recommended: Node.js 18+ if you plan to expand formatting support with additional ecosystem tools.
- A repo you can experiment with. The examples below assume a project root called `sample-app`.

```bash
python -m pip install --upgrade pip
pip install emperator-cli tree-sitter pymdown-extensions codeql-bundle semgrep ruff
```

> **Note:** `codeql-bundle` is a large dependency. If you cannot install it locally, skip for now and rely on Semgrep checks; you can add CodeQL later during CI integration.

## Step 1 — Initialize the contract directory

Create a `contract/` folder at the root of your repo. Emperator treats this as the executable specification for your standards. Start with three files that mirror the layers described in the architecture overview.

```text
contract/
├── conventions.cue
├── policy/rules.rego
└── api/openapi.yaml
```

Sample content:

```cue title="contract/conventions.cue"
package contract

controllers: {
    files: [...string] & =~"^[a-z0-9_]+\.py$"
}
```

```rego title="contract/policy/rules.rego"
package contract.security

deny[msg] {
    input.findings[_].rule == "SecretDetection"
    msg := "Hardcoded secret detected"
}
```

```yaml title="contract/api/openapi.yaml"
openapi: 3.1.0
info:
    title: Sample Service Contract
    version: 0.1.0
paths:
    /healthz:
        get:
            operationId: getHealth
            responses:
                "200":
                    description: OK
```

## Step 2 — Seed a code sample that violates the contract

Add a small file that intentionally breaks your rules so you can observe Emperator in action.

```python title="src/controllers/UserController.py"
from util import db


def get_user():
    token = "AKIA-FAKE-KEY"
    return db.query("SELECT * FROM users WHERE id = 1")
```

The filename mixes casing, the code embeds a credential-like string, and the controller hits the database layer directly.

## Step 3 — Run `emperator apply`

Execute the CLI at the project root to compile the contract, build the IR, and run checks.

```bash
cd sample-app
emperator apply --diff --format table
```

Typical output after the first run:

```text
Emperator v1.0 • Contract revision 0.1.0

[Check] 3 issues found
  1. NamingConvention: controllers/UserController.py → rename to snake_case
  2. SecretDetection: Potential credential literal at line 4
  3. LayeringPolicy: Direct DB access from controller at line 5

[Fix] Applied 1 autofix
  ✔ Renamed controllers/UserController.py → controllers/user_controller.py

[Suggest] 2 manual reviews required
  ❗ Replace literal credential with vault reference
  ❗ Route DB call through service layer

Summary: 1 change applied, 2 suggestions pending review.
```

Behind the scenes Emperator performed the following workflow:

```mermaid
flowchart LR
  subgraph Contract Layer
    A[Project Contract<br/>(OpenAPI, CUE, Rego)]
  end
  subgraph IR Layer
    B[Tree-sitter CST<br/>+ CodeQL semantics<br/>+ Semgrep patterns]
  end
  subgraph Action Layer
    C1[Check Engines]
    C2[Fix Engines]
    C3[Formatters]
  end
  A --> B --> C1
  C1 -->|violations| D{Safety Gate}
  D -->|Auto-fixable| C2 --> C3 --> E[Proposed or Applied Changes]
  D -->|Manual review| E
  E --> F[Re-check & Optional Tests]
  F -->|Pass| G[✅ Standards satisfied]
  F -->|Fail| H[Rollback & Report]
```

## Step 4 — Inspect diffs and apply suggestions

- Accept or modify Emperator’s proposed rename (already applied).
- Replace the hardcoded credential with a secrets manager reference.
- Move the database call into a dedicated service module and expose a service method to the controller.

Re-run `emperator apply` until the summary shows `✅ Standards satisfied`.

## Step 5 — Align linting and install the pre-commit hook

If you are working inside this documentation repository, run the helper script so the JavaScript and TypeScript tooling matches the documented defaults:

```bash
pnpm run setup:lint
```

The script installs Node dependencies, wires the `pre-commit` and commit-msg hooks, formats sources with Biome, and then performs the full lint suite (Biome + ESLint). Use `pnpm run setup:lint -- --ci` when running inside CI or on machines where you cannot modify the working tree.

Integrate Emperator with `pre-commit` so every developer receives the same enforcement locally.

```yaml title=".pre-commit-config.yaml"
repos:
    - repo: local
      hooks:
          - id: emperator
            name: Emperator Standards Check
            entry: emperator apply --diff --color
            language: system
            pass_filenames: false
```

Install the hook:

```bash
pip install pre-commit
pre-commit install
```

Now any commit that breaks the contract will fail fast with actionable diagnostics.

If you are working directly on the Emperator repository, `./scripts/setup-tooling.sh` (or `pnpm run setup:tooling`) orchestrates the Python virtual environment, installs dev dependencies, and then runs this lint bootstrap end-to-end.

## Next steps

- Expand the contract with additional rules from the how-to guides.
- Wire Emperator into CI using the pipeline recipes in [Integrating Emperator with CI/CD Pipelines](../how-to/ci-integration.md).
- Explore the architecture deep dive to understand how the IR stays synchronized across languages and how the safety envelope protects your code base.

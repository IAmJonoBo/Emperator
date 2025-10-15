# Emperator Directory Structure

Emperator/
├─ contract/                     # Executable rules & blueprints (the “Project Contract”)
│  ├─ api/                       # OpenAPI/GraphQL/Proto specs
│  ├─ policy/                    # OPA/Rego policies (*.rego)
│  ├─ conventions/               # CUE constraints (naming, layouts, limits)
│  └─ generators/                # Scaffold templates and recipe data
├─ src/                          # Application/library code (PyPA “src/” layout)
│  └─ emperator/                 # Python package(s)
├─ tests/                        # Pytest-style tests (separate from code)
├─ rules/                        # Static-analysis packs owned by the repo
│  ├─ semgrep/                   # Custom Semgrep rules
│  └─ codeql/                    # CodeQL queries/packs
├─ tools/                        # Developer CLIs, codemods, one-off scripts
│  ├─ dev/                       # Local-only helpers (seed data, demo scripts)
│  └─ ci/                        # Small utilities invoked from CI
├─ env/                          # Environment descriptors (config *inputs*, not secrets)
│  ├─ dev.env.example
│  ├─ ci.env.example
│  └─ prod.env.example
├─ compose/                      # Container orchestration for dev/CI (opt-in)
│  ├─ compose.yaml               # Base services
│  ├─ compose.dev.yaml           # Dev overrides (-f compose.yaml -f compose.dev.yaml)
│  └─ compose.ci.yaml            # CI overrides
├─ infra/                        # (Optional) IaC with clear env split
│  ├─ k8s/
│  │  ├─ base/                   # Kustomize base
│  │  └─ overlays/{dev,prod}/    # Env overlays
│  └─ terraform/
│     ├─ modules/                # Reusable modules
│     └─ envs/{dev,prod}/        # Per-env root configs / tfvars
├─ docs/                         # MkDocs or Sphinx sources (kept out of src/)
│  └─ index.md
├─ dist/                         # Build artifacts (wheel/sdist) — gitignored
├─ .devcontainer/                # Dev Containers spec (picked up automatically)
├─ .github/workflows/            # CI pipelines (standard location)
├─ .pre-commit-config.yaml
├─ .editorconfig
├─ pyproject.toml                # PEP 621 metadata & tool config
├─ README.md
└─ .gitignore

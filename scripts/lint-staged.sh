#!/usr/bin/env bash
set -euo pipefail

log_info() {
    printf '[lint-staged] %s\n' "$1"
}

log_warn() {
    printf '[lint-staged] WARN: %s\n' "$1" >&2
}

ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "${ROOT_DIR}"

IFS=$'\n' read -r -d '' -a staged_files < <(
    git diff --name-only --cached --diff-filter=ACMR && printf '\0'
)

if [[ ${#staged_files[@]} -eq 0 ]]; then
    log_info 'No staged files to lint.'
    exit 0
fi

python_files=()
biome_files=()
eslint_files=()

for file in "${staged_files[@]}"; do
    if [[ ! -f ${file} ]]; then
        continue
    fi
    case "${file}" in
    *.py)
        python_files+=("${file}")
        ;;
    *.js | *.jsx | *.ts | *.tsx | *.mjs | *.cjs | *.json | *.jsonc | *.css | *.scss | *.html | *.yml | *.yaml | *.md | *.mdx)
        biome_files+=("${file}")
        ;;
    esac

    case "${file}" in
    *.js | *.jsx | *.ts | *.tsx | *.mjs | *.cjs)
        eslint_files+=("${file}")
        ;;
    esac
done

exit_code=0

if [[ ${#python_files[@]} -gt 0 ]]; then
    if command -v uv >/dev/null 2>&1; then
        log_info "Running Ruff on ${#python_files[@]} staged file(s)."
        if ! uv run ruff check "${python_files[@]}"; then
            exit_code=$?
        fi
    else
        log_warn 'uv not found on PATH; skipping Ruff staged lint.'
    fi
fi

if [[ ${#biome_files[@]} -gt 0 ]]; then
    log_info "Running Biome on ${#biome_files[@]} staged file(s)."
    if ! pnpm exec biome check --no-errors-on-unmatched "${biome_files[@]}"; then
        exit_code=$?
    fi
fi

if [[ ${#eslint_files[@]} -gt 0 ]]; then
    log_info "Running ESLint on ${#eslint_files[@]} staged file(s)."
    if ! pnpm exec eslint --max-warnings=0 --cache --cache-location .cache/eslint "${eslint_files[@]}"; then
        exit_code=$?
    fi
fi

if [[ ${exit_code} -ne 0 ]]; then
    log_warn 'Lint issues detected in staged files.'
fi

exit "${exit_code}"

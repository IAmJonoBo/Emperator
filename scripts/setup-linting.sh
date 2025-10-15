#!/usr/bin/env bash
set -euo pipefail

MODE="dev"
INSTALL_DEPS=true
INSTALL_HOOKS=true
CUSTOM_ROOT=""

usage() {
  cat <<'EOF'
Usage: setup-linting.sh [OPTIONS]

Prepare and validate the JavaScript/TypeScript linting + formatting toolchain.
The script installs dependencies, wires pre-commit hooks (when appropriate),
and runs the repo's formatter + linter passes.

Options:
  --ci             Skip editor-focused steps (hooks, writes) and run CI-safe checks.
  --skip-install   Skip pnpm install (useful if dependencies are already fetched).
  --skip-hooks     Do not install pre-commit hooks (implied by --ci).
  --root PATH      Override repository root discovery.
  -h, --help       Show this help message.

Examples:
  ./scripts/setup-linting.sh              # Developer workstation bootstrap
  ./scripts/setup-linting.sh --ci         # CI / deployment pipeline check
  ./scripts/setup-linting.sh --skip-install --skip-hooks
EOF
}

log_info() {
  printf '[lint-setup] %s\n' "$1"
}

log_warn() {
  printf '[lint-setup] WARN: %s\n' "$1" >&2
}

log_error() {
  printf '[lint-setup] ERROR: %s\n' "$1" >&2
}

on_error() {
  log_error "Aborted (line $1)."
}

trap 'on_error $LINENO' ERR

run_pre_commit_suite() {
  if [[ ${MODE} != "dev" ]]; then
    log_info "Skipping pre-commit validation run"
    return
  fi

  if ! command -v pre-commit >/dev/null 2>&1; then
    log_warn "pre-commit not found; skipping validation run"
    return
  fi

  log_info "Running pre-commit checks across the repository"
  pre-commit run --all-files --show-diff-on-failure
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ci)
      MODE="ci"
      INSTALL_HOOKS=false
      shift
      ;;
    --skip-install)
      INSTALL_DEPS=false
      shift
      ;;
    --skip-hooks)
      INSTALL_HOOKS=false
      shift
      ;;
    --root)
      if [[ $# -lt 2 ]]; then
        log_error "--root requires a path argument"
        exit 1
      fi
      CUSTOM_ROOT="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    -*)
      log_error "Unknown option: $1"
      usage >&2
      exit 1
      ;;
    *)
      log_error "Unexpected positional argument: $1"
      usage >&2
      exit 1
      ;;
  esac
done

find_repo_root() {
  local candidate="$1"
  while [[ -n ${candidate} && ${candidate} != "/" ]]; do
    if [[ -d "${candidate}/.git" || -f "${candidate}/.git" ]]; then
      echo "${candidate}"
      return 0
    fi
    candidate="$(dirname "${candidate}")"
  done
  return 1
}

resolve_repo_root() {
  local provided="$1"
  if [[ -n ${provided} ]]; then
    cd "${provided}" 2>/dev/null && pwd && return 0
    log_error "Provided root path is invalid: ${provided}"
    exit 1
  fi

  if command -v git >/dev/null 2>&1; then
    if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
      echo "${git_root}"
      return 0
    fi
  fi

  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  repo_root="$(find_repo_root "${script_dir}")"
  if [[ -n "${repo_root}" ]]; then
    echo "${repo_root}"
    return 0
  fi

  echo "${script_dir}/.."
}

ROOT_DIR="$(resolve_repo_root "${CUSTOM_ROOT}")"
cd "${ROOT_DIR}"

if [[ ! -f "pnpm-lock.yaml" ]]; then
  log_error "pnpm-lock.yaml not found — are you in the repository root?"
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  log_error "pnpm is required. Install it from https://pnpm.io/installation"
  exit 1
fi

if [[ ${INSTALL_DEPS} == true ]]; then
  if [[ ${MODE} == "ci" ]]; then
    log_info "Pre-fetching pnpm store from lockfile"
    pnpm fetch
    log_info "Installing dependencies (frozen lockfile)"
    pnpm install --frozen-lockfile --prefer-offline
  else
    log_info "Installing dependencies"
    pnpm install
  fi
else
  log_info "Skipping dependency installation"
fi

if [[ ${MODE} == "dev" && ${INSTALL_HOOKS} == true ]]; then
  if command -v pre-commit >/dev/null 2>&1; then
    log_info "Installing pre-commit hooks"
    pre-commit install --install-hooks
    pre-commit install --hook-type commit-msg
  else
    log_warn "pre-commit not found; skipping hook installation"
  fi
else
  log_info "Skipping hook installation"
fi

if [[ ${MODE} == "dev" ]]; then
  log_info "Applying Biome formatter (writes to workspace)"
  pnpm fmt
  log_info "Running lint pipeline (Biome check + ESLint)"
  pnpm lint
else
  log_info "Running CI-safe lint pipeline (no writes)"
  pnpm lint
fi

run_pre_commit_suite

log_info "Linting + formatting toolchain ready"

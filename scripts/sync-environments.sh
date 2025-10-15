#!/usr/bin/env bash
set -euo pipefail

MODE="dev"
PYTHON_CMD=""
CUSTOM_ROOT=""

usage() {
  cat <<'EOF'
Usage: sync-environments.sh [OPTIONS]

Synchronise the Python (uv) and JavaScript/TypeScript (pnpm) toolchains without
running the full setup routines. Useful for keeping local and CI environments
in lockstep after lockfile changes.

Options:
  --ci             Run in CI mode (frozen lockfiles, no workspace writes).
  --python PATH    Explicit Python interpreter to use when syncing with uv.
  --root PATH      Override repository root discovery.
  -h, --help       Show this help message.
EOF
}

log_info() {
  printf '[sync-envs] %s\n' "$1"
}

log_warn() {
  printf '[sync-envs] WARN: %s\n' "$1" >&2
}

log_error() {
  printf '[sync-envs] ERROR: %s\n' "$1" >&2
}

on_error() {
  log_error "Aborted (line $1)."
}

trap 'on_error $LINENO' ERR

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ci)
      MODE="ci"
      shift
      ;;
    --python)
      if [[ $# -lt 2 ]]; then
        log_error "--python requires a path argument"
        exit 1
      fi
      PYTHON_CMD="$2"
      shift 2
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
  if repo_root="$(find_repo_root "${script_dir}")"; then
    echo "${repo_root}"
    return 0
  fi

  echo "${script_dir}/.."
}

ROOT_DIR="$(resolve_repo_root "${CUSTOM_ROOT}")"
cd "${ROOT_DIR}"

if [[ ! -f "pyproject.toml" ]]; then
  log_error "pyproject.toml not found — are you in the repository root?"
  exit 1
fi

if [[ ! -f "pnpm-lock.yaml" ]]; then
  log_error "pnpm-lock.yaml not found — are you in the repository root?"
  exit 1
fi

detect_uv() {
  if [[ -n ${UV_BIN-} && -x ${UV_BIN} ]]; then
    echo "${UV_BIN}"
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  if [[ -x "${HOME}/.cargo/bin/uv" ]]; then
    echo "${HOME}/.cargo/bin/uv"
    return 0
  fi
  return 1
}

ensure_uv() {
  local uv_path
  uv_path="$(detect_uv)"
  if [[ -n ${uv_path} ]]; then
    echo "${uv_path}"
    return 0
  fi

  if [[ ${MODE} == "ci" ]]; then
    log_error "uv is required in CI. Install it before running sync-environments."
    exit 1
  fi

  log_info "Installing uv (https://astral.sh/uv)"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    log_error "curl is required to install uv automatically. Install uv manually and re-run."
    exit 1
  fi

  uv_path="$(detect_uv)"
  if [[ -n ${uv_path} ]]; then
    echo "${uv_path}"
    return 0
  fi

  log_error "uv installation failed. Set UV_BIN to the uv executable and retry."
  exit 1
}

sync_python() {
  local uv_bin
  local sync_args=(--extra dev)

  uv_bin="$(ensure_uv)"
  export UV_BIN="${uv_bin}"
  export UV_VENV_IN_PROJECT=1

  if [[ -n ${PYTHON_CMD} ]]; then
    sync_args+=(--python "${PYTHON_CMD}")
  fi

  if [[ ${MODE} == "ci" ]]; then
    if [[ ! -f "uv.lock" ]]; then
      log_error "uv.lock not found. Generate it with 'uv lock' before running in CI."
      exit 1
    fi
    log_info "Syncing Python environment from uv.lock (frozen)"
    "${uv_bin}" sync --frozen "${sync_args[@]}"
  else
    log_info "Syncing Python environment (dev extras included)"
    "${uv_bin}" sync "${sync_args[@]}"
  fi
}

sync_node() {
  if ! command -v pnpm >/dev/null 2>&1; then
    log_error "pnpm is required. Install it from https://pnpm.io/installation"
    exit 1
  fi

  if [[ ${MODE} == "ci" ]]; then
    log_info "Pre-fetching pnpm store from lockfile"
    pnpm fetch
    log_info "Installing JavaScript dependencies (frozen lockfile)"
    pnpm install --frozen-lockfile --prefer-offline
  else
    log_info "Installing JavaScript dependencies"
    pnpm install
  fi
}

sync_python
sync_node

log_info "Dependency sync complete"

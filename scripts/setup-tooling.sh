#!/usr/bin/env bash
set -euo pipefail

MODE="dev"
RUN_PYTHON=true
RUN_NODE=true
PYTHON_CMD=""
CUSTOM_ROOT=""
# All variables are used in the script below.

usage() {
  cat <<'EOF'
Usage: setup-tooling.sh [OPTIONS]

Bootstrap the full Emperator developer toolchain. The script orchestrates the Python
virtual environment, installs project dependencies (including dev extras), exposes the
virtualenv on PATH, and then delegates to the JavaScript/TypeScript lint setup.

Options:
  --ci             Run in CI mode (no workspace writes, skip hook installation).
  --skip-python    Skip Python environment creation and dependency installation.
  --skip-node      Skip JavaScript/TypeScript tooling setup.
  --python PATH    Explicit Python interpreter to use when creating the virtualenv.
  --root PATH      Override repository root discovery.
  -h, --help       Show this help message.

Examples:
  ./scripts/setup-tooling.sh              # Full workstation bootstrap
  ./scripts/setup-tooling.sh --ci         # CI / deployment pipeline verification
  ./scripts/setup-tooling.sh --skip-node  # Python-only setup
EOF
}

log_info() {
  printf '[tooling-setup] %s\n' "$1"
}

log_warn() {
  printf '[tooling-setup] WARN: %s\n' "$1" >&2
}

log_error() {
  printf '[tooling-setup] ERROR: %s\n' "$1" >&2
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
    --skip-python)
      RUN_PYTHON=false
      shift
      ;;
    --skip-node)
      RUN_NODE=false
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
  repo_root="$(find_repo_root "${script_dir}")"
  if [[ -n "${repo_root}" ]]; then
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
  if [[ -n "${uv_path}" ]]; then
    echo "${uv_path}"
    return 0
  fi

  if [[ ${MODE} == "ci" ]]; then
    log_error "uv is required in CI. Install it before running setup-tooling (see https://docs.astral.sh/uv/)."
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
  if [[ -n "${uv_path}" ]]; then
    echo "${uv_path}"
    return 0
  fi

  log_error "uv installation failed. Set UV_BIN to the uv executable and retry."
  exit 1
}

prepare_python() {
  local uv_bin
  local lock_args=()
  local sync_args=(--extra dev)

  uv_bin="$(ensure_uv)"
  export UV_BIN="${uv_bin}"
  export UV_VENV_IN_PROJECT=1

  if [[ -n ${PYTHON_CMD} ]]; then
    sync_args+=(--python "${PYTHON_CMD}")
  fi

  if [[ ${MODE} == "ci" ]]; then
    if [[ ! -f "uv.lock" ]]; then
      log_error "uv.lock not found. Generate it with 'uv lock' before running CI."
      exit 1
    fi
    log_info "Syncing Python environment from uv.lock (frozen)"
    "${uv_bin}" sync --frozen "${sync_args[@]}"
  else
    if [[ -f "uv.lock" ]]; then
      log_info "Refreshing uv.lock with the latest compatible versions"
    else
      log_info "Generating uv.lock with the latest compatible versions"
    fi
    if ((${#lock_args[@]} > 0)); then
      "${uv_bin}" lock "${lock_args[@]}"
    else
      "${uv_bin}" lock
    fi
    log_info "Syncing Python environment (dev extras included)"
    "${uv_bin}" sync "${sync_args[@]}"
  fi

  export PATH="${ROOT_DIR}/.venv/bin:${PATH}"
  log_info "Python tooling ready"
}

prepare_node() {
  local lint_script="${ROOT_DIR}/scripts/setup-linting.sh"
  if [[ ! -x ${lint_script} ]]; then
    log_error "Expected ${lint_script} to exist and be executable"
    exit 1
  fi

  local args=()
  if [[ ${MODE} == "ci" ]]; then
    args+=(--ci)
  fi

  log_info "Bootstrapping JavaScript/TypeScript tooling"
  "${lint_script}" "${args[@]}"
}

install_git_hooks() {
  if [[ ${MODE} == "ci" ]]; then
    log_info "Skipping Git hook installation (CI mode)"
    return
  fi

  if ! command -v pre-commit >/dev/null 2>&1; then
    log_warn "pre-commit not found; skipping Git hook installation"
    return
  fi

  log_info "Ensuring Git hooks are installed"
  if ! pre-commit install --install-hooks >/dev/null; then
    log_warn "Failed to install pre-commit hook"
  fi
  if ! pre-commit install --install-hooks --hook-type commit-msg >/dev/null; then
    log_warn "Failed to install commit-msg hook"
  fi
}

if [[ ${RUN_PYTHON} == true ]]; then
  prepare_python
else
  log_warn "Skipping Python environment setup"
fi

if [[ ${RUN_NODE} == true ]]; then
  prepare_node
else
  log_warn "Skipping JavaScript/TypeScript tooling setup"
fi

install_git_hooks

log_info "Developer tooling ready"

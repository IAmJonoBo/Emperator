#!/usr/bin/env bash
set -euo pipefail

log_info() {
  printf '[cache] %s\n' "$1"
}

log_warn() {
  printf '[cache] WARN: %s\n' "$1" >&2
}

ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "${ROOT_DIR}"

CACHE_ROOT="${ROOT_DIR}/.cache"
PRE_COMMIT_DIR="${PRE_COMMIT_HOME:-${CACHE_ROOT}/pre-commit}"
UV_CACHE_DIR_VALUE="${UV_CACHE_DIR:-${CACHE_ROOT}/uv}"

mkdir -p "${CACHE_ROOT}" "${PRE_COMMIT_DIR}" "${UV_CACHE_DIR_VALUE}"

log_info 'Pruning pnpm store'
pnpm store prune || log_warn 'pnpm store prune failed'

if command -v uv >/dev/null 2>&1; then
  log_info 'Pruning uv cache'
  UV_CACHE_DIR="${UV_CACHE_DIR_VALUE}" uv cache prune --all || log_warn 'uv cache prune failed'
else
  log_warn 'uv not found on PATH; skipping uv cache prune'
fi

if command -v pre-commit >/dev/null 2>&1; then
  log_info 'Cleaning pre-commit environments'
  PRE_COMMIT_HOME="${PRE_COMMIT_DIR}" pre-commit clean || log_warn 'pre-commit clean failed'
else
  log_warn 'pre-commit not found; skipping hook cache cleanup'
fi

find "${CACHE_ROOT}" -type d -empty -delete 2>/dev/null || true

log_info 'Cache pruning complete'

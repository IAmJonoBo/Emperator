#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${REQUESTS_CA_BUNDLE:-}" ]]; then
  cert_path="$REQUESTS_CA_BUNDLE"
else
  cert_path="$(uv run --extra dev --with pip-audit python -c 'import certifi; print(certifi.where())')"
fi

REQUESTS_CA_BUNDLE="$cert_path" uv run --extra dev --with pip-audit pip-audit "$@"

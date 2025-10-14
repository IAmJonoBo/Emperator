#!/usr/bin/env bash
set -euo pipefail

# Prevent Apple-specific metadata from entering the repository history.
# We scan staged files (NUL-separated) for common patterns that macOS writes.
PATTERN='(^|/)(\.DS_Store|\.AppleDouble|\.LSOverride|Icon.|\.DocumentRevisions-V100|\.fseventsd|\.Spotlight-V100|\.TemporaryItems|\.Trashes|\.VolumeIcon\.icns|\.com\.apple\.timemachine\.donotpresent|\.apdisk|_\..+)$'

if git diff --cached --name-only -z | grep -z -E "$PATTERN" >/dev/null; then
  echo "❌ Apple cruft detected in staged changes. Unstage and remove the files listed below:" >&2
  git diff --cached --name-only | grep -E "$PATTERN" | sed 's/^/ - /' >&2 || true
  exit 1
fi

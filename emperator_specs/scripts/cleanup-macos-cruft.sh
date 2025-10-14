#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=""
INCLUDE_GIT=false
INCLUDE_POETRY_ENV=false
INCLUDE_PYTHON_CACHE=false
INCLUDE_BUILD_ARTIFACTS=false
INCLUDE_NODE_MODULES=false
DEEP_CLEAN=false
EXTRA_PATHS=()
SEARCH_ROOTS=()

usage() {
	cat <<'EOF'
Usage: cleanup-macos-cruft.sh [OPTIONS]... [ROOT_DIR]

Removes macOS metadata artifacts and development cruft from the workspace.
By default, only macOS-specific files are removed. Use additional flags for
comprehensive cleanup.

macOS Cleanup Options:
  --include-git          Also clean .git directories (useful after archive extraction)
  --include-poetry-env   Clean the active Poetry virtual environment

Development Cleanup Options:
  --python-cache         Remove Python __pycache__ directories and .pyc files
  --build-artifacts      Remove build artifacts (.egg-info, dist/, build/, .tox/)
  --node-modules         Remove node_modules directories
  --deep-clean           Enable all cleanup options (equivalent to all flags above)

Additional Options:
  --extra-path PATH      Add additional search root (can be used multiple times)
  -h, --help             Show this help message

Examples:
  cleanup-macos-cruft.sh                           # Basic macOS cleanup
  cleanup-macos-cruft.sh --python-cache            # macOS + Python cache cleanup
  cleanup-macos-cruft.sh --deep-clean              # Complete cleanup
  cleanup-macos-cruft.sh --extra-path /tmp/project # Include additional directory
EOF
}

add_search_root() {
	local candidate="$1"
	if [[ -z ${candidate} ]]; then
		return
	fi
	for existing in "${SEARCH_ROOTS[@]}"; do
		if [[ ${existing} == "${candidate}" ]]; then
			return
		fi
	done
	SEARCH_ROOTS+=("${candidate}")
}

while [[ $# -gt 0 ]]; do
	case "$1" in
	--include-git)
		INCLUDE_GIT=true
		shift
		;;
	--include-poetry-env)
		INCLUDE_POETRY_ENV=true
		shift
		;;
	--python-cache)
		INCLUDE_PYTHON_CACHE=true
		shift
		;;
	--build-artifacts)
		INCLUDE_BUILD_ARTIFACTS=true
		shift
		;;
	--node-modules)
		INCLUDE_NODE_MODULES=true
		shift
		;;
	--deep-clean)
		DEEP_CLEAN=true
		INCLUDE_GIT=true
		INCLUDE_POETRY_ENV=true
		INCLUDE_PYTHON_CACHE=true
		INCLUDE_BUILD_ARTIFACTS=true
		INCLUDE_NODE_MODULES=true
		shift
		;;
	--extra-path)
		if [[ $# -lt 2 ]]; then
			echo "--extra-path requires a PATH argument" >&2
			exit 1
		fi
		EXTRA_PATHS+=("$2")
		shift 2
		;;
	-h | --help)
		usage
		exit 0
		;;
	--*)
		echo "Unknown option: $1" >&2
		usage >&2
		exit 1
		;;
	*)
		if [[ -n ${ROOT_DIR} ]]; then
			echo "Multiple root directories provided. Use one ROOT_DIR argument." >&2
			exit 1
		fi
		ROOT_DIR="$1"
		shift
		;;
	esac
done

ROOT_DIR="${ROOT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
if [[ ! -d ${ROOT_DIR} ]]; then
	echo "Provided root directory does not exist: ${ROOT_DIR}" >&2
	exit 1
fi

shopt -s nullglob dotglob

SEARCH_ROOTS=()

add_search_root() {
	local candidate="$1"
	if [[ -z ${candidate} ]]; then
		return
	fi
	for existing in "${SEARCH_ROOTS[@]}"; do
		if [[ ${existing} == "${candidate}" ]]; then
			return
		fi
	done
	SEARCH_ROOTS+=("${candidate}")
}

log_removal() {
	local path="$1"
	echo "Removed ${path}" >&2
}
add_search_root "${ROOT_DIR}"

for path in "${EXTRA_PATHS[@]}"; do
	add_search_root "${path}"
done

if [[ ${INCLUDE_POETRY_ENV} == true ]]; then
	if command -v poetry >/dev/null 2>&1; then
		poetry_env_path="$(poetry env info --no-ansi --path 2>/dev/null || true)"
		if [[ -n ${poetry_env_path} && -d ${poetry_env_path} ]]; then
			add_search_root "${poetry_env_path}"
		else
			echo "Poetry virtual environment not found; skipping --include-poetry-env" >&2
		fi
	else
		echo "Poetry command not available; skipping --include-poetry-env" >&2
	fi
fi

# Add uv virtual environment if detected
if [[ -d "${ROOT_DIR}/.venv" ]]; then
	if [[ ${INCLUDE_POETRY_ENV} == true || ${DEEP_CLEAN} == true ]]; then
		add_search_root "${ROOT_DIR}/.venv"
	fi
fi

cleanup_macos_cruft() {
	local search_root="$1"

	local MACOS_PATTERNS=(
		".DS_Store"
		"._*"
		".AppleDouble"
		"Icon?"
		"__MACOSX"
	)

	echo "Cleaning macOS cruft in: ${search_root}" >&2

	for pattern in "${MACOS_PATTERNS[@]}"; do
		if [[ ${INCLUDE_GIT} == true ]]; then
			FIND_EXPR=(-name "${pattern}" -print0)
		else
			FIND_EXPR=(-path "*/.git" -prune -o -name "${pattern}" -print0)
		fi

		while IFS= read -r -d '' path; do
			if [[ -d ${path} ]]; then
				rm -rf "${path}"
			else
				rm -f "${path}"
			fi
			log_removal "${path}"
		done < <(find "${search_root}" "${FIND_EXPR[@]}")
	done
}

cleanup_python_cache() {
	local search_root="$1"

	echo "Cleaning Python cache files in: ${search_root}" >&2

	# Remove __pycache__ directories
	find "${search_root}" -type d -name "__pycache__" -print0 | while IFS= read -r -d '' path; do
		rm -rf "${path}"
		log_removal "${path}"
	done

	# Remove .pyc and .pyo files
	find "${search_root}" -type f \( -name "*.pyc" -o -name "*.pyo" \) -print0 | while IFS= read -r -d '' path; do
		rm -f "${path}"
		log_removal "${path}"
	done
}

cleanup_build_artifacts() {
	local search_root="$1"

	echo "Cleaning build artifacts in: ${search_root}" >&2

	local BUILD_PATTERNS=(
		"*.egg-info"
		"build"
		"dist"
		".tox"
		".pytest_cache"
		".coverage"
		"coverage.xml"
		".mypy_cache"
		".ruff_cache"
		"htmlcov"
		"*.whl"
		".trunk"
		"site-packages"
	)

	for pattern in "${BUILD_PATTERNS[@]}"; do
		find "${search_root}" -maxdepth 3 -name "${pattern}" -print0 | while IFS= read -r -d '' path; do
			# Skip if this is inside .venv and we're not cleaning the venv specifically
			if [[ ${path} == *"/.venv/"* && ${search_root} != *"/.venv"* ]]; then
				continue
			fi
			if [[ -d ${path} ]]; then
				rm -rf "${path}"
			else
				rm -f "${path}"
			fi
			log_removal "${path}"
		done
	done

	# Clean up Jupyter notebook checkpoints
	find "${search_root}" -type d -name ".ipynb_checkpoints" -print0 | while IFS= read -r -d '' path; do
		rm -rf "${path}"
		log_removal "${path}"
	done

	# Clean up temporary files
	find "${search_root}" -maxdepth 2 \( -name "*.tmp" -o -name "*.temp" -o -name "*~" \) -print0 | while IFS= read -r -d '' path; do
		rm -f "${path}"
		log_removal "${path}"
	done
}

cleanup_node_modules() {
	local search_root="$1"

	echo "Cleaning Node.js modules in: ${search_root}" >&2

	find "${search_root}" -type d -name "node_modules" -print0 | while IFS= read -r -d '' path; do
		rm -rf "${path}"
		log_removal "${path}"
	done
}

for search_root in "${SEARCH_ROOTS[@]}"; do
	if [[ ! -d ${search_root} ]]; then
		echo "Skipping missing search root: ${search_root}" >&2
		continue
	fi

	# Always clean macOS cruft
	cleanup_macos_cruft "${search_root}"

	# Conditional cleanup based on flags
	if [[ ${INCLUDE_PYTHON_CACHE} == true ]]; then
		cleanup_python_cache "${search_root}"
	fi

	if [[ ${INCLUDE_BUILD_ARTIFACTS} == true ]]; then
		cleanup_build_artifacts "${search_root}"
	fi

	if [[ ${INCLUDE_NODE_MODULES} == true ]]; then
		cleanup_node_modules "${search_root}"
	fi
done

echo ""
echo "Cleanup completed!" >&2

shopt -u nullglob dotglob

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

. "$SCRIPT_DIR/ensure-uv-venv.sh"
ensure_uv_venv "$SCRIPT_DIR/.."

"$SCRIPT_DIR/run-registry-docker.sh" \
  /bin/sh -lc 'cd /workspace/.github/workflows && uv run --no-project --with pytest --with jsonschema pytest tests/ -v "$@"' \
  run-workflows-tests "$@"

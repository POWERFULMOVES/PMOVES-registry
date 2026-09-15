#!/usr/bin/env bash
# ensure-uv-venv — uv owns the registry tooling venv.
#
# All agents share this registry and run its tooling, so the venv contract is
# shared too: if VIRTUAL_ENV is unset, warn loudly and let uv create/sync the
# managed .venv beside the Python project. Warn-only by design: Docker
# wrappers and CI manage their own environments and must keep working when
# uv is absent on the host.
ensure_uv_venv() {
  local project_dir="${1:-}"

  if [ -n "${VIRTUAL_ENV:-}" ]; then
    return 0
  fi

  if ! command -v uv >/dev/null 2>&1; then
    echo "[ensure-uv-venv] warn: VIRTUAL_ENV not set and uv not on PATH; install uv (https://docs.astral.sh/uv/) so the registry venv is uv-managed" >&2
    return 0
  fi

  echo "[ensure-uv-venv] warn: VIRTUAL_ENV not set; letting uv manage the venv" >&2

  if [ -n "$project_dir" ] && [ -f "$project_dir/pyproject.toml" ]; then
    if ! (cd "$project_dir" && uv venv); then
      echo "[ensure-uv-venv] warn: uv venv failed for $project_dir; continuing without it" >&2
    fi
  fi
}

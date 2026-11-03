#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

CONFIG_FILE="${1:-configs/default.yaml}"
if (($# > 0)); then
  shift
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  printf 'Configuration introuvable : %s\n' "$CONFIG_FILE" >&2
  exit 2
fi

exec poetry run web-capture --config "$CONFIG_FILE" "$@"

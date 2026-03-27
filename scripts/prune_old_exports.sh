#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="${SQUEEZE_CN_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
EXPORTS_DIR="$PROJECT_ROOT/exports"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

if [[ ! -d "$EXPORTS_DIR" ]]; then
  echo "Exports directory not found: $EXPORTS_DIR" >&2
  exit 1
fi

find "$EXPORTS_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -print -exec rm -rf {} +

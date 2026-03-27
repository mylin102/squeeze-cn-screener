#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="${SQUEEZE_CN_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_BIN="${SQUEEZE_CN_PYTHON:-$PROJECT_ROOT/.venv/bin/python}"
LIMIT="${SQUEEZE_CN_LIMIT:-300}"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/daily_scan.log"

mkdir -p "$LOG_DIR" "$PROJECT_ROOT/exports"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  echo "Set SQUEEZE_CN_PYTHON or create a virtualenv at $PROJECT_ROOT/.venv" >&2
  exit 1
fi

cd "$PROJECT_ROOT"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting daily China scan"
  PYTHONPATH=src "$PYTHON_BIN" -m squeeze.cli scan --limit "$LIMIT" --export
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Daily China scan finished"
} >> "$LOG_FILE" 2>&1

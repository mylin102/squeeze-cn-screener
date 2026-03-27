#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="${SQUEEZE_CN_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OSSUTIL_BIN="${OSSUTIL_BIN:-ossutil}"
OSS_BUCKET="${OSS_BUCKET:-}"
OSS_PREFIX="${OSS_PREFIX:-squeeze-cn/exports}"
SOURCE_DIR="$PROJECT_ROOT/exports"

if [[ -z "$OSS_BUCKET" ]]; then
  echo "OSS_BUCKET is required" >&2
  exit 1
fi

if ! command -v "$OSSUTIL_BIN" >/dev/null 2>&1; then
  echo "ossutil not found: $OSSUTIL_BIN" >&2
  exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Exports directory not found: $SOURCE_DIR" >&2
  exit 1
fi

"$OSSUTIL_BIN" cp -r "$SOURCE_DIR/" "oss://$OSS_BUCKET/$OSS_PREFIX/"

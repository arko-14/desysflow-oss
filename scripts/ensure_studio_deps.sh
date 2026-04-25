#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STUDIO_DIR="$ROOT_DIR/studio"
CHECK_ONLY="${1:-}"

critical_files=(
  "node_modules/vite/dist/node/cli.js"
  "node_modules/rolldown/dist/parse-ast-index.mjs"
  "node_modules/vitest/dist/cli.js"
)

studio_deps_healthy() {
  local rel
  for rel in "${critical_files[@]}"; do
    if [ ! -f "$STUDIO_DIR/$rel" ]; then
      return 1
    fi
  done
  return 0
}

reinstall_studio_deps() {
  echo "Studio dependencies are missing or incomplete. Reinstalling cleanly..."
  rm -rf "$STUDIO_DIR/node_modules"
  cd "$STUDIO_DIR"
  if [ -f "package-lock.json" ]; then
    npm ci
  else
    npm install
  fi
}

if [ "$CHECK_ONLY" = "--check-only" ]; then
  if studio_deps_healthy; then
    exit 0
  fi
  exit 1
fi

if ! studio_deps_healthy; then
  reinstall_studio_deps
fi

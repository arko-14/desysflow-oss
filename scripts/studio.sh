#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/studio"

ensure_studio_deps() {
  if [ ! -f "node_modules/vite/dist/node/cli.js" ]; then
    echo "Studio dependencies are missing or stale. Reinstalling..."
    npm install
  fi
}

if [ -f "../.env.example" ]; then
  set -a
  . ../.env.example
  set +a
fi

export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://localhost:8000}"

ensure_studio_deps

npm run dev

#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/ui"

if [ -f "../.env" ]; then
  set -a
  . ../.env
  set +a
fi

export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://localhost:8000}"

npm run dev

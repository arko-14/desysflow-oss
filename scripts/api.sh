#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

export DESYSFLOW_STORAGE_ROOT="${DESYSFLOW_STORAGE_ROOT:-./desysflow}"
export CHAT_STORE_BACKEND="${CHAT_STORE_BACKEND:-sqlite}"
export MEM0_ENABLED="${MEM0_ENABLED:-false}"
export LLM_PROVIDER="${LLM_PROVIDER:-ollama}"
export LLM_MODEL="${LLM_MODEL:-gpt-oss:20b-cloud}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-$LLM_MODEL}"
export OLLAMA_CRITIC_MODEL="${OLLAMA_CRITIC_MODEL:-$OLLAMA_MODEL}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

mkdir -p "$DESYSFLOW_STORAGE_ROOT"

uv run python scripts/check_model.py
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 600

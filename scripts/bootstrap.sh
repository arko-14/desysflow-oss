#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it first: https://docs.astral.sh/uv/"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required."
  exit 1
fi

echo "Creating local environment..."
uv venv
. .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .

echo "Installing UI packages..."
(
  cd ui
  npm install
)

provider_default="ollama"
model_default="gpt-oss:20b-cloud"
base_url_default="http://localhost:11434"

printf "Model provider [ollama/openai/anthropic] (default: %s): " "$provider_default"
read -r provider
provider="${provider:-$provider_default}"

model="$model_default"
base_url="$base_url_default"
api_key=""

case "$provider" in
  ollama)
    printf "Ollama model (default: %s): " "$model_default"
    read -r model
    model="${model:-$model_default}"
    printf "Ollama base URL (default: %s): " "$base_url_default"
    read -r base_url
    base_url="${base_url:-$base_url_default}"
    ;;
  openai)
    printf "OpenAI model (default: gpt-5.4): "
    read -r model
    model="${model:-gpt-5.4}"
    printf "OpenAI API key: "
    read -r api_key
    ;;
  anthropic)
    printf "Anthropic model (default: claude-opus-4-1-20250805): "
    read -r model
    model="${model:-claude-opus-4-1-20250805}"
    printf "Anthropic API key: "
    read -r api_key
    ;;
  *)
    echo "Unsupported provider: $provider"
    exit 1
    ;;
esac

cat > .env <<EOF
DESYSFLOW_STORAGE_ROOT=./desysflow
CHAT_STORE_BACKEND=sqlite
MEM0_ENABLED=false
LLM_PROVIDER=$provider
LLM_MODEL=$model
OLLAMA_MODEL=$model
OLLAMA_BASE_URL=$base_url
OLLAMA_CRITIC_MODEL=$model
OPENAI_MODEL=$model
ANTHROPIC_MODEL=$model
OPENAI_API_KEY=$api_key
ANTHROPIC_API_KEY=$api_key
VITE_API_PROXY_TARGET=http://localhost:8000
EOF

echo "Saved local config to .env"
echo "Checking model availability..."
if ! uv run python scripts/check_model.py; then
  echo "Model check failed. Update .env or install the Ollama model before running DesysFlow."
  exit 1
fi

echo "Cold start complete."
echo "CLI: ./letsvibedesign cli"
echo "UI + API: ./letsvibedesign dev"

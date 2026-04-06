# Getting Started

## Prerequisites

- Python 3.11+
- `uv` installed and available in `PATH`
- Node.js and npm

## 1. Initial Setup

Run the single bootstrap entrypoint:

```bash
./letsvibedesign
```

This will:
- Create `.venv`
- Install Python dependencies
- Install UI dependencies
- Ask for model provider/model
- Write local `.env`
- Validate model availability

## 2. Run Modes

```bash
./letsvibedesign cli   # CLI workflow
./letsvibedesign dev   # API + UI
./letsvibedesign api   # API only
./letsvibedesign ui    # UI only
./letsvibedesign check # model availability check
```

## 3. Backend and UI URLs

- API docs: `http://localhost:8000/docs`
- UI: `http://localhost:5173`

## 4. Configuration

Environment variables are stored in local `.env`. Typical keys:
- `LLM_PROVIDER`
- `LLM_MODEL`
- `OLLAMA_BASE_URL`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DESYSFLOW_STORAGE_ROOT`

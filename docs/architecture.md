# Architecture

## System Overview

DesysFlow consists of three primary layers:
- CLI orchestration (`desysflow_cli`)
- API service (`FastAPI`)
- UI workspace (`React + Vite`)

## Backend Flow

The design pipeline in `graph/workflow.py` follows these major phases:
1. requirements extraction
2. template selection
3. architecture generation
4. edge-case injection
5. primary architecture selection
6. diagram generation and quality pass
7. report generation
8. cloud-infra mapping

## Key Modules

- `agents/`: generation and review agents
- `api/`: HTTP routes
- `services/`: storage, session, LLM, search
- `schemas/`: API contracts
- `graph/`: orchestration logic
- `utils/`: parser, formatting, memory helpers
- `ui/`: frontend app

## Data Storage

Default local storage under `./desysflow`:
- chat/session databases (SQLite)
- versioned design artifacts
- session notes and artifacts

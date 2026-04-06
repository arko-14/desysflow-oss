# Project Overview

DesysFlow OSS is an open-source, local-first system design workspace focused on practical design generation from real codebases.

## Scope

Current scope includes:
- source-aware architecture generation
- versioned technical artifacts
- CLI-first workflows for fast iteration
- local UI for browsing and follow-up prompts
- local persistence for session and conversation history

## Design Principles

- Keep workflows local by default
- Produce deterministic, reviewable markdown outputs
- Preserve version history of architecture decisions
- Prefer practical implementation detail over abstract output

## Packaging

- Python package metadata in `pyproject.toml`
- CLI entrypoint: `desysflow`
- helper launcher: `./letsvibedesign`

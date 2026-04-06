# CLI Guide

## Command Summary

```bash
desysflow chat
desysflow design
desysflow redesign
desysflow history
desysflow resume <session_id>
```

## `chat`

Terminal-first session workflow backed by local SQLite.

```bash
desysflow chat --source . --out ./desysflow --project desysflow-oss
```

In-chat commands:
- `/design <goal>`: generate or refine design artifacts
- `/history`: show recent messages
- `/exit`: end session

## `design`

Generate a versioned design package from current source.

```bash
desysflow design --source . --out ./desysflow --project desysflow-oss
```

## `redesign`

Compatibility alias for explicit refinement with focus.

```bash
desysflow redesign --source . --out ./desysflow --project desysflow-oss --focus "improve reliability"
```

## Interactive Prompts

When flags are omitted in an interactive terminal, CLI asks for:
- language (`python`, `typescript`, `go`, `java`, `rust`)
- cloud target (`local`, `aws`, `gcp`, `azure`, `hybrid`)
- style (`minimal`, `balanced`, `detailed`)
- web-search mode (`auto`, `on`, `off`)

## Output and Persistence

Local data locations:
- `desysflow/.desysflow_cli.db`
- `desysflow/.desysflow_session.db`
- `desysflow/.desysflow_chat.db`
- `desysflow/sessions/`
- `desysflow/session_artifacts/`

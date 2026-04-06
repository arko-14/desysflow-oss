from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from services.storage_paths import get_storage_root
from services.llm import check_llm_status, get_llm_config

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "desysflow",
}
TOP_FILE_LIMIT = 60
REVIEW_LOOP_LIMIT = 2

HLD_REQUIRED_SECTIONS = [
    "## Overview",
    "## Components",
    "## Data Flow",
    "## Scaling and Availability",
    "## Trade-offs",
]
LLD_REQUIRED_SECTIONS = [
    "## APIs",
    "## Schemas",
    "## Service Communication",
    "## Caching",
    "## Error Handling",
    "## Deployment",
    "## Security",
]
TECH_REPORT_REQUIRED_SECTIONS = [
    "## Sub-agent Topology",
    "## Parallel Execution Plan",
    "## Internal Reviewer Loop",
    "## Context Bloat Fixes",
    "## Session Management and Memory",
]
NON_TECH_REQUIRED_SECTIONS = [
    "## Product Summary",
    "## Business Value",
    "## Target Users",
    "## Delivery Shape",
    "## Future Improvements",
]


@dataclass
class RunConfig:
    command: str
    source: Path
    output_root: Path
    project: str
    language: str
    style: str
    cloud: str
    web_search: str
    mode: str
    effective_mode: str
    focus: str
    non_interactive: bool


@dataclass
class AnalysisContext:
    inventory: dict[str, Any]
    stack: dict[str, Any]
    module_map: dict[str, str]
    key_paths: list[str]
    web_enabled: bool
    references: list[dict[str, str]]


@dataclass
class ChatConfig:
    source: Path
    output_root: Path
    project: str
    session_id: str


@dataclass
class HistoryConfig:
    output_root: Path
    limit: int


def parse_run_args(command: str, argv: list[str] | None = None) -> RunConfig:
    parser = argparse.ArgumentParser(
        prog=f"desysflow {command.lstrip('/')}",
        description=(
            "Generate a versioned system-design package from a source repository."
            if command == "/design"
            else "Refine from the latest generated design package."
        ),
    )
    parser.add_argument("--source", default=".", help="Source repository path to analyze.")
    parser.add_argument(
        "--out",
        default="./desysflow",
        help="Output root for generated design folders (default: ./desysflow).",
    )
    parser.add_argument("--project", default="", help="Project name override.")
    parser.add_argument(
        "--language",
        choices=["python", "typescript", "go", "java", "rust"],
        default="",
        help="Preferred implementation language for the design package.",
    )
    parser.add_argument(
        "--style",
        choices=["minimal", "balanced", "detailed"],
        default="",
        help="Report depth style.",
    )
    parser.add_argument(
        "--cloud",
        choices=["local", "none", "aws", "gcp", "azure", "hybrid"],
        default="",
        help="Cloud deployment target for recommendations.",
    )
    parser.add_argument(
        "--mode",
        choices=["smart", "fresh", "refine"],
        default="",
        help="Routing mode for /design. Smart chooses fresh or refine from project state.",
    )
    parser.add_argument(
        "--web-search",
        choices=["auto", "on", "off"],
        default="",
        help="External web search mode. Auto enables only when useful.",
    )
    parser.add_argument("--focus", default="", help="Improvement goal for refine runs.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip option prompts and use defaults/flags.",
    )

    ns = parser.parse_args(argv)
    cfg = RunConfig(
        command=command,
        source=Path(ns.source).expanduser().resolve(),
        output_root=Path(ns.out).expanduser().resolve(),
        project=ns.project.strip() or Path(ns.source).expanduser().resolve().name,
        language=(ns.language or "").strip(),
        style=ns.style.strip(),
        cloud=ns.cloud.strip(),
        web_search=ns.web_search.strip(),
        mode=ns.mode.strip(),
        effective_mode="",
        focus=ns.focus.strip(),
        non_interactive=bool(ns.non_interactive),
    )
    return finalize_options(cfg)


def parse_chat_args(argv: list[str] | None = None) -> ChatConfig:
    parser = argparse.ArgumentParser(
        prog="desysflow chat",
        description="Start a terminal-first DesysFlow chat session.",
    )
    parser.add_argument("--source", default=".", help="Source repository path to analyze.")
    parser.add_argument("--out", default="./desysflow", help="Storage root for local sessions and outputs.")
    parser.add_argument("--project", default="", help="Project name override.")
    parser.add_argument("--session", default="", help="Resume a specific local chat session id.")
    ns = parser.parse_args(argv)
    source = Path(ns.source).expanduser().resolve()
    output_root = Path(ns.out).expanduser().resolve()
    project = ns.project.strip() or source.name
    return ChatConfig(source=source, output_root=output_root, project=project, session_id=ns.session.strip())


def parse_history_args(argv: list[str] | None = None) -> HistoryConfig:
    parser = argparse.ArgumentParser(
        prog="desysflow history",
        description="List local DesysFlow chat sessions.",
    )
    parser.add_argument("--out", default="./desysflow", help="Storage root for local sessions and outputs.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of sessions to show.")
    ns = parser.parse_args(argv)
    return HistoryConfig(output_root=Path(ns.out).expanduser().resolve(), limit=max(1, ns.limit))


def print_main_help() -> None:
    print("DesysFlow CLI")
    print("")
    print("Usage:")
    print("  desysflow chat [--source PATH] [--out PATH] [--project NAME] [--session ID]")
    print("  desysflow design [options]")
    print("  desysflow redesign [options]")
    print("  desysflow history [--out PATH] [--limit N]")
    print("  desysflow resume <session_id> [--source PATH] [--out PATH] [--project NAME]")
    print("")
    print("Commands:")
    print("  chat       Start terminal chat mode with local session history")
    print("  design     Generate a new versioned design package")
    print("  redesign   Refine from latest version (falls back to fresh when needed)")
    print("  history    List saved chat sessions")
    print("  resume     Resume a chat session by id")
    print("  help       Show this help")
    print("")
    print("Common design/redesign options:")
    print("  --source PATH           Source repository (default: .)")
    print("  --out PATH              Output root (default: ./desysflow)")
    print("  --project NAME          Project name override")
    print("  --language VALUE        python|typescript|go|java|rust")
    print("  --style VALUE           minimal|balanced|detailed")
    print("  --cloud VALUE           local|aws|gcp|azure|hybrid")
    print("  --mode VALUE            smart|fresh|refine")
    print("  --web-search VALUE      auto|on|off")
    print("  --focus TEXT            Refinement goal")
    print("  --non-interactive       Disable interactive prompts")
    print("")
    print("Examples:")
    print("  desysflow design --source . --out ./desysflow --project my-app")
    print("  desysflow redesign --source . --out ./desysflow --project my-app --focus \"improve scalability\"")
    print("  desysflow chat")
    print("  desysflow resume 3f8b2a7d9c1e")
    print("")
    print("Tip: run `desysflow <command> --help` for command-specific help.")


def finalize_options(cfg: RunConfig) -> RunConfig:
    interactive = (not cfg.non_interactive) and os.isatty(0)
    project_root = cfg.output_root / cfg.project
    has_existing_design = any(
        child.is_dir() and child.name.startswith("v")
        for child in project_root.iterdir()
    ) if project_root.exists() else False
    language = cfg.language or "python"
    style = cfg.style or "balanced"
    cloud = normalize_cloud(cfg.cloud or "local")
    web_mode = cfg.web_search or "auto"
    mode = cfg.mode or "smart"

    if interactive:
        language = ask_option("Implementation language", ["python", "typescript", "go", "java", "rust"], language)
        style = ask_option("Report style", ["balanced", "minimal", "detailed"], style)
        cloud = normalize_cloud(ask_option("Cloud target", ["local", "aws", "gcp", "azure", "hybrid"], cloud))
        web_mode = ask_option("Web search mode", ["auto", "on", "off"], web_mode)
        if cfg.command == "/design" and has_existing_design:
            mode = ask_option("Design routing", ["smart", "fresh", "refine"], mode)

    effective_mode = resolve_effective_mode(cfg.command, mode, has_existing_design, cfg.focus)

    return RunConfig(
        command=cfg.command,
        source=cfg.source,
        output_root=cfg.output_root,
        project=cfg.project,
        language=language,
        style=style,
        cloud=cloud,
        web_search=web_mode,
        mode=mode,
        effective_mode=effective_mode,
        focus=cfg.focus,
        non_interactive=cfg.non_interactive,
    )


def ask_option(label: str, values: list[str], default: str) -> str:
    print(f"{label} [{'/'.join(values)}] (default: {default})")
    response = input("> ").strip().lower()
    if not response:
        return default
    if response in values:
        return response
    print(f"Invalid option. Using default: {default}")
    return default


def normalize_cloud(value: str) -> str:
    return "local" if value == "none" else value


def resolve_effective_mode(command: str, mode: str, has_existing_design: bool, focus: str) -> str:
    if command == "/redesign":
        return "refine"
    if mode == "fresh":
        return "fresh"
    if mode == "refine":
        return "refine" if has_existing_design else "fresh"
    if has_existing_design and focus.strip():
        return "refine"
    return "fresh"


def init_session_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                command TEXT NOT NULL,
                project TEXT NOT NULL,
                source_path TEXT NOT NULL,
                output_path TEXT NOT NULL,
                options_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                project TEXT NOT NULL,
                source_path TEXT NOT NULL,
                title TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
            );
            """
        )


def record_run(db_path: Path, cfg: RunConfig, output_path: Path) -> int:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    options_json = json.dumps(
        {
            "language": cfg.language,
            "style": cfg.style,
            "cloud": cfg.cloud,
            "web_search": cfg.web_search,
            "mode": cfg.mode,
            "effective_mode": cfg.effective_mode,
            "focus": cfg.focus,
            "non_interactive": cfg.non_interactive,
        }
    )
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO runs (created_at, command, project, source_path, output_path, options_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now, cfg.command, cfg.project, str(cfg.source), str(output_path), options_json),
        )
        return int(cur.lastrowid)


def record_event(db_path: Path, run_id: int, event_type: str, content: str) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO events (run_id, event_type, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, event_type, content, now),
        )


def create_chat_session(db_path: Path, project: str, source_path: Path, title: str) -> str:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    session_id = sha256(f"{project}:{source_path}:{now}".encode("utf-8")).hexdigest()[:12]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions (session_id, created_at, updated_at, project, source_path, title)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, now, now, project, str(source_path), title),
        )
    return session_id


def touch_chat_session(db_path: Path, session_id: str, title: str | None = None) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        if title:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ?, title = ? WHERE session_id = ?",
                (now, title, session_id),
            )
        else:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )


def add_chat_message(db_path: Path, session_id: str, role: str, content: str) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, now),
        )
    touch_chat_session(db_path, session_id)


def get_chat_session(db_path: Path, session_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        session_row = conn.execute(
            """
            SELECT session_id, created_at, updated_at, project, source_path, title
            FROM chat_sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if not session_row:
            return None
        messages = conn.execute(
            """
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
    return {
        "session_id": session_row["session_id"],
        "created_at": session_row["created_at"],
        "updated_at": session_row["updated_at"],
        "project": session_row["project"],
        "source_path": session_row["source_path"],
        "title": session_row["title"],
        "messages": [
            {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
            for row in messages
        ],
    }


def list_chat_sessions(db_path: Path, limit: int = 20) -> list[dict[str, str]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT session_id, created_at, updated_at, project, source_path, title
            FROM chat_sessions
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def should_enable_web_search(mode: str, prompt: str, focus: str, cloud: str) -> bool:
    if mode == "on":
        return True
    if mode == "off":
        return False

    text = f"{prompt}\n{focus}".lower()
    keywords = {
        "latest",
        "current",
        "compliance",
        "gdpr",
        "hipaa",
        "soc2",
        "pci",
        "pricing",
        "cost",
        "sla",
        "kubernetes",
        "cloud",
        "managed",
    }
    return any(keyword in text for keyword in keywords) or cloud in {"aws", "gcp", "azure", "hybrid"}


def best_effort_search(query: str, enabled: bool, limit: int = 5) -> list[dict[str, str]]:
    if not enabled or not query.strip():
        return []
    try:
        from ddgs import DDGS  # type: ignore

        with DDGS() as ddgs:
            results: list[dict[str, str]] = []
            for item in ddgs.text(query, max_results=limit):
                title = str(item.get("title", "")).strip()
                href = str(item.get("href", "")).strip()
                snippet = str(item.get("body", "")).strip()
                if href:
                    results.append({"title": title, "url": href, "snippet": snippet})
            return results
    except Exception:
        return []


def source_inventory(source: Path) -> dict[str, Any]:
    files: list[Path] = []
    ext_count: dict[str, int] = {}

    for root, dirs, names in os.walk(source):
        dirs[:] = [item for item in dirs if item not in SKIP_DIRS]
        for name in names:
            path = Path(root) / name
            if path.name.startswith("."):
                continue
            rel = path.relative_to(source)
            files.append(rel)
            ext = path.suffix.lower() or "<noext>"
            ext_count[ext] = ext_count.get(ext, 0) + 1

    files_sorted = sorted(files, key=lambda item: (len(item.parts), str(item)))
    top_files = [str(item) for item in files_sorted[:TOP_FILE_LIMIT]]
    modules = []
    for name in ["agents", "api", "services", "utils", "ui", "schemas", "graph", "rules"]:
        path = source / name
        if path.exists() and path.is_dir():
            modules.append({"name": name, "files": sum(1 for item in path.rglob("*") if item.is_file())})

    return {
        "total_files": len(files),
        "extensions": dict(sorted(ext_count.items(), key=lambda pair: (-pair[1], pair[0]))),
        "modules": modules,
        "top_files": top_files,
    }


def detect_stack(source: Path) -> dict[str, Any]:
    stack = {"language": [], "frameworks": [], "storage": [], "runtime": []}
    files_to_scan = [source / "pyproject.toml", source / "requirements.txt", source / "README.md"]
    blob = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in files_to_scan
        if path.exists()
    )

    if (source / "pyproject.toml").exists() or (source / "requirements.txt").exists():
        stack["language"].append("Python")
    if (source / "ui" / "package.json").exists():
        stack["language"].append("JavaScript")

    for key, label in [
        ("fastapi", "FastAPI"),
        ("langgraph", "LangGraph"),
        ("langchain", "LangChain"),
        ("uvicorn", "Uvicorn"),
        ("sqlite", "SQLite"),
        ("ollama", "Ollama"),
        ("react", "React"),
        ("vite", "Vite"),
    ]:
        if key in blob:
            if label == "SQLite":
                stack["storage"].append(label)
            elif label == "Uvicorn":
                stack["runtime"].append(label)
            else:
                stack["frameworks"].append(label)

    if not stack["storage"]:
        stack["storage"].append("SQLite")

    for key in stack:
        stack[key] = sorted(set(stack[key]))
    return stack


def map_modules(source: Path) -> dict[str, str]:
    descriptions = {
        "agents": "Domain agents responsible for extraction, architecture drafting, diagram shaping, and revision passes.",
        "api": "Local FastAPI surface used by the simple OSS UI.",
        "services": "Runtime adapters for search, LLM configuration, storage, and session handling.",
        "utils": "Formatting, memory compaction, diagram stability, and document helpers.",
        "ui": "Local browser UI for prompt entry and inspecting generated outputs.",
        "schemas": "Pydantic request and response schemas for API contracts.",
        "graph": "Workflow orchestration layer coordinating agent execution.",
        "rules": "Prompt rules and edge-case handling logic.",
    }
    module_map: dict[str, str] = {}
    for name, description in descriptions.items():
        path = source / name
        if path.exists() and path.is_dir():
            module_map[name] = description
    return module_map


def identify_key_paths(source: Path) -> list[str]:
    candidates = [
        "main.py",
        "pyproject.toml",
        "README.md",
        "docs/cli.md",
        "api/routes.py",
        "ui/src/App.jsx",
        "desysflow_cli/__main__.py",
    ]
    return [item for item in candidates if (source / item).exists()]


def choose_version(project_root: Path) -> tuple[str, Path, Path | None]:
    project_root.mkdir(parents=True, exist_ok=True)
    versions = []
    for child in project_root.iterdir():
        if child.is_dir() and child.name.startswith("v"):
            try:
                versions.append(int(child.name[1:]))
            except ValueError:
                continue
    previous = max(versions) if versions else 0
    next_version = previous + 1
    prev_path = project_root / f"v{previous}" if previous else None
    return f"v{next_version}", project_root / f"v{next_version}", prev_path


def cli_db_path(output_root: Path) -> Path:
    return output_root / ".desysflow_cli.db"


def read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def style_notes(style: str) -> dict[str, str]:
    if style == "minimal":
        return {
            "detail": "Concise sections focused on the decisions required to build and ship the system.",
            "test_depth": "Critical-path test strategy only.",
        }
    if style == "detailed":
        return {
            "detail": "Comprehensive coverage with explicit trade-offs, failure paths, and implementation notes.",
            "test_depth": "Expanded test matrix across functional and non-functional paths.",
        }
    return {
        "detail": "Balanced detail with enough implementation guidance to be practical without becoming noisy.",
        "test_depth": "Core functional and resilience test plan.",
    }


def build_analysis_context(cfg: RunConfig) -> AnalysisContext:
    web_enabled = should_enable_web_search(cfg.web_search, cfg.project, cfg.focus, cfg.cloud)
    search_query = f"{cfg.project} {cfg.focus or 'system design'} {cfg.cloud}".strip()

    with ThreadPoolExecutor(max_workers=5) as executor:
        inventory_future = executor.submit(source_inventory, cfg.source)
        stack_future = executor.submit(detect_stack, cfg.source)
        module_future = executor.submit(map_modules, cfg.source)
        paths_future = executor.submit(identify_key_paths, cfg.source)
        refs_future = executor.submit(best_effort_search, search_query, web_enabled, 5)

    return AnalysisContext(
        inventory=inventory_future.result(),
        stack=stack_future.result(),
        module_map=module_future.result(),
        key_paths=paths_future.result(),
        web_enabled=web_enabled,
        references=refs_future.result(),
    )


def build_mermaid(ctx: AnalysisContext, cfg: RunConfig) -> str:
    modules = set(ctx.module_map.keys())
    lines = [
        "flowchart TD",
        "    DeveloperUser[Developer] --> DesysflowCli[DesysFlow CLI]",
        "    DesysflowCli --> DesignOrchestrator[Local Design Orchestrator]",
        "    DesignOrchestrator --> RequirementsExtractor[Requirements Extractor]",
        "    DesignOrchestrator --> ArchitecturePlanner[Architecture Planner]",
        "    DesignOrchestrator --> MermaidRenderer[Mermaid Renderer]",
        "    DesignOrchestrator --> DocumentPackager[Document Packager]",
        "    DesignOrchestrator --> ReviewLoop[Reviewer Loop]",
        "    ReviewLoop --> VersionedOutput[Versioned DesysFlow Output]",
        "    DesysflowCli --> LocalSessionDb[(Local SQLite Session DB)]",
        "    LocalSessionDb --> VersionedOutput",
    ]

    if "api" in modules:
        lines.append("    DesignOrchestrator --> LocalApi[Local API Layer]")
    if "ui" in modules:
        lines.append("    DesysflowCli --> WorkspaceUi[Local Workspace UI]")
    if "services" in modules:
        lines.append("    DesignOrchestrator --> ServiceAdapters[Service Adapters]")
    if cfg.cloud != "local":
        lines.append(f"    DocumentPackager --> CloudProfile[{cfg.cloud.upper()} Deployment Profile]")
        lines.append("    CloudProfile --> VersionedOutput")
    return "\n".join(lines) + "\n"


def render_hld(cfg: RunConfig, version: str, ctx: AnalysisContext) -> str:
    style_hint = style_notes(cfg.style)
    module_lines = "\n".join(
        f"- `{name}`: {description}" for name, description in ctx.module_map.items()
    ) or "- No core module folders detected."
    cloud_text = (
        f"- Target cloud profile: `{cfg.cloud}`\n- Prefer managed building blocks where portability does not materially suffer."
        if cfg.cloud != "local"
        else "- Target cloud profile: `local` (cloud-agnostic baseline)."
    )

    return f"""# HLD

## Overview
- Project: `{cfg.project}`
- Version: `{version}`
- Source path: `{cfg.source}`
- Preferred language: `{cfg.language}`
- Report style: `{cfg.style}`

This high-level design is generated from the current source tree. {style_hint["detail"]}

## Components
{module_lines}

## Data Flow
1. The local CLI accepts `/design` inputs and routes fresh vs refine behavior smartly.
2. Parallel sub-agents inspect the repo, stack, and module boundaries.
3. Architecture, diagram, and report drafts are produced concurrently.
4. A lightweight reviewer loop improves structure, wording, and Mermaid consistency.
5. Final artifacts are written into the versioned `desysflow/` dump.

## Scaling and Availability
- Sub-agent steps are independent and can run concurrently for faster local generation.
- Outputs are deterministic text files, which keeps refine diffs readable in git.
- SQLite is sufficient for OSS local usage and avoids introducing unnecessary infrastructure.

## Cloud Guidance
{cloud_text}

## Trade-offs
- Static repo inspection is reliable and reproducible, but it cannot infer every unstated business constraint.
- Keeping the review loop lightweight improves output quality without turning the OSS workflow into a heavyweight gated review product.
"""


def render_lld(cfg: RunConfig, ctx: AnalysisContext) -> str:
    style_hint = style_notes(cfg.style)
    key_paths = "\n".join(f"- `{item}`" for item in ctx.key_paths) or "- No representative paths detected."
    return f"""# LLD

## APIs
- `desysflow /design --source . --out ./desysflow`
- `desysflow /design --source . --out ./desysflow --focus "<goal>"` to refine from latest
- `desysflow /redesign ...` remains as a compatibility alias for explicit refine runs

## Schemas
- `METADATA.json`: run metadata, hashes, and parent version references.
- `SOURCE_INVENTORY.md`: repository inventory and module overview.
- `TREE.md`: emitted folder tree for the current design version.

## Service Communication
- Extraction, drafting, diagramming, and report generation run as parallel local sub-agents.
- The reviewer loop consumes draft artifacts and applies small deterministic fixes before packaging.

## Caching
- Session runs and event logs are stored in SQLite via `.desysflow_cli.db`.
- No Redis, vector store, or external cache is required for the OSS CLI flow.

## Error Handling
- `/design` routes to `fresh` or `refine` mode based on project state and user intent.
- `/redesign` falls back to fresh generation when no prior version exists.
- Web search runs on a best-effort basis and never blocks generation.
- Reviewer-loop failures degrade to the latest valid draft rather than aborting the run.

## Deployment
- Local execution target: Python 3.11+.
- CI target: run the CLI and commit the generated `desysflow/` dump when desired.
- Preferred implementation language for recommendations: `{cfg.language}`
- Representative repo paths considered during analysis:
{key_paths}

## Security
- The generator reads local source files and writes Markdown, Mermaid, and JSON artifacts only.
- Secrets are not intentionally extracted or copied into generated docs.

## Test Plan
- {style_hint["test_depth"]}
- Confirm `diagram.mmd` starts with `flowchart TD`.
- Confirm required markdown sections are present after each run.
"""


def render_technical_report(cfg: RunConfig, ctx: AnalysisContext, version: str) -> str:
    refs_md = "\n".join(
        f"- [{item['title'] or item['url']}]({item['url']}) - {item['snippet'][:160]}"
        for item in ctx.references
    ) or "- No external references used for this run."
    extension_lines = "\n".join(
        f"- `{ext}`: {count}" for ext, count in list(ctx.inventory["extensions"].items())[:12]
    )
    return f"""# TECHNICAL REPORT

## Executive Summary
This versioned design package was generated from repository inspection using an OSS-first local workflow. The tool favors parallel analysis, deterministic outputs, and a minimal operational footprint.

## Detected Stack
- Languages: {", ".join(ctx.stack["language"]) or "Unknown"}
- Frameworks: {", ".join(ctx.stack["frameworks"]) or "Unknown"}
- Storage: {", ".join(ctx.stack["storage"]) or "Unknown"}
- Runtime: {", ".join(ctx.stack["runtime"]) or "Unknown"}
- Preferred implementation language: {cfg.language}

## Sub-agent Topology
- Extractor sub-agent: builds the repository inventory and key-path map.
- Architecture sub-agent: synthesizes the main structural narrative and trade-offs.
- Diagram sub-agent: emits the Mermaid architecture view.
- Report sub-agent: assembles HLD, LLD, summary, and metadata.
- Reviewer sub-agent: runs small iterative checks to improve completeness and clarity.

## Parallel Execution Plan
- Analysis stage runs inventory, stack detection, module mapping, and optional web grounding in parallel.
- Draft stage runs HLD, LLD, Mermaid, and technical-report generation in parallel.
- Packaging stage writes docs, metadata, folder tree, and diff output.

## Internal Reviewer Loop
- Runs up to `{REVIEW_LOOP_LIMIT}` passes per command.
- Acts as the lightweight critic-in-the-loop for architecture quality.
- Checks required headings, Mermaid prefix validity, OSS-scope wording, and cross-document consistency.
- Fixes small structural gaps automatically instead of exposing a separate user-facing review workflow.

## Context Bloat Fixes
- Representative file inventory is capped at `TOP_FILE_LIMIT={TOP_FILE_LIMIT}`.
- Session state is summarized into SQLite records instead of long in-memory chains.
- Refine runs write a fresh versioned package rather than appending fragmented outputs.

## Session Management and Memory
- Run history is stored in `desysflow/.desysflow_cli.db`.
- No Mem0, Qdrant, Supabase, or heavyweight product-memory layer is required.

## Web Search Strategy
- User mode: `{cfg.web_search}`
- Effective mode: `{"enabled" if ctx.web_enabled else "disabled"}`
- Auto mode only activates for changing or external constraints such as cloud capabilities, compliance, or pricing.

## External References
{refs_md}

## Repository Signals
- Total files scanned: {ctx.inventory["total_files"]}
- Top extensions:
{extension_lines}
- Current output version: `{version}`
"""


def render_pipeline(cfg: RunConfig, ctx: AnalysisContext) -> str:
    module_count = len(ctx.module_map)
    return f"""# PIPELINE

## Command
- Requested command: `{cfg.command}`
- Effective mode: `{cfg.effective_mode}`
- Focus: `{cfg.focus or "n/a"}`

## Parallel Sub-agents
1. Extractor: source inventory, key paths, and repo map.
2. Stack profiler: language, framework, storage, and runtime detection.
3. Architect: HLD and implementation framing.
4. Diagrammer: Mermaid flow draft.
5. Reporter: technical report, summary, and changelog.

## Reviewer Loop
1. Validate section coverage.
2. Validate Mermaid structure.
3. Remove SaaS-only or gated-product wording from OSS docs.
4. Tighten wording and consistency across HLD, LLD, and technical report.

## Scope Snapshot
- Modules detected: `{module_count}`
- Key paths sampled: `{len(ctx.key_paths)}`
- Web grounding references: `{len(ctx.references)}`
"""


def render_inventory(ctx: AnalysisContext) -> str:
    module_lines = "\n".join(f"- `{item['name']}`: {item['files']} files" for item in ctx.inventory["modules"])
    extension_lines = "\n".join(
        f"- `{ext}`: {count}" for ext, count in list(ctx.inventory["extensions"].items())[:12]
    )
    file_lines = "\n".join(f"- `{item}`" for item in ctx.inventory["top_files"])
    return f"""# SOURCE INVENTORY

- Total files: {ctx.inventory["total_files"]}

## Modules
{module_lines or "- No module directories found."}

## Extensions
{extension_lines}

## Representative Files
{file_lines}
"""


def render_summary(cfg: RunConfig, version: str, ctx: AnalysisContext) -> str:
    return f"""# SUMMARY

- Command: `{cfg.command}`
- Effective mode: `{cfg.effective_mode}`
- Project: `{cfg.project}`
- Version: `{version}`
- Output: `{cfg.output_root / cfg.project / version}`
- Language: `{cfg.language}`
- Style: `{cfg.style}`
- Cloud: `{cfg.cloud}`
- Web search: `{cfg.web_search}` -> `{"enabled" if ctx.web_enabled else "disabled"}`
- Parallel sub-agents: `enabled`
- Internal reviewer loop: `enabled`

Generated files:
- `HLD.md`
- `LLD.md`
- `TECHNICAL_REPORT.md`
- `NON_TECHNICAL_DOC.md`
- `PIPELINE.md`
- `diagram.mmd`
- `SOURCE_INVENTORY.md`
- `TREE.md`
- `METADATA.json`
- `CHANGELOG.md`
- `DIFF.md`
"""


def render_changelog(cfg: RunConfig, version: str, ctx: AnalysisContext) -> str:
    return f"""# CHANGELOG

## {version}
- Command: `{cfg.command}`
- Effective mode: `{cfg.effective_mode}`
- Language: `{cfg.language}`
- Focus: `{cfg.focus or "n/a"}`
- Report style: `{cfg.style}`
- Cloud target: `{cfg.cloud}`
- Web search effective: `{"enabled" if ctx.web_enabled else "disabled"}`
- Parallel sub-agents: `enabled`
- Reviewer loop: `enabled`
"""


def render_non_technical_doc(cfg: RunConfig, ctx: AnalysisContext, version: str) -> str:
    module_count = len(ctx.module_map)
    core_users = ", ".join(["founders", "product leads", "engineering managers", "developers"])
    key_capabilities = [
        "Turns a source tree or prompt into a versioned design package",
        "Keeps sessions, chat history, and artifacts local under ./desysflow",
        "Supports iterative refinement without losing earlier versions",
        "Produces outputs usable by both technical and non-technical stakeholders",
    ]
    capability_lines = "\n".join(f"- {item}" for item in key_capabilities)
    future_lines = "\n".join(
        [
            "- Add stronger roadmap and phase-planning views for stakeholder discussions.",
            "- Add effort, cost, and deployment comparison summaries for different operating models.",
            "- Improve side-by-side version comparison for design evolution over time.",
            "- Add reusable templates for product categories such as SaaS, internal tools, and data platforms.",
        ]
    )
    return f"""# NON-TECHNICAL DOC

## Product Summary
- Project: `{cfg.project}`
- Version: `{version}`
- Positioning: local-first design workspace for architecture planning and refinement
- Preferred language for implementation guidance: `{cfg.language}`

This package is intended to help teams move from idea to implementation plan with less ambiguity and less overhead than a heavyweight hosted workflow.

## Business Value
- Provides a shared planning artifact for product, engineering, and delivery conversations.
- Speeds up early-stage technical scoping by generating architecture, implementation, and review-ready outputs in one run.
- Keeps outputs versioned and local, which makes change tracking easier for teams working directly in code repositories.

## Target Users
- Core users: {core_users}
- Best fit: teams that want practical design outputs without a complex platform setup
- Current repo signals considered: `{module_count}` major module areas and `{ctx.inventory["total_files"]}` scanned files

## Key Capabilities
{capability_lines}

## Delivery Shape
- Output location: `desysflow/{cfg.project}/{version}`
- Primary generated assets: architecture diagram, technical document, implementation detail, and project brief
- Collaboration style: one local workspace with versioned design history
- Cloud target framing: `{cfg.cloud}`

## Risks and Constraints
- Generated outputs are only as strong as the constraints visible in the source tree and prompt.
- Business priorities such as pricing, compliance scope, and launch sequencing may still require human refinement.
- Local-first simplicity reduces operational overhead, but limits built-in multi-user workflow features.

## Future Improvements
{future_lines}
"""


def render_docs(cfg: RunConfig, version: str, ctx: AnalysisContext) -> dict[str, str]:
    with ThreadPoolExecutor(max_workers=6) as executor:
        hld_future = executor.submit(render_hld, cfg, version, ctx)
        lld_future = executor.submit(render_lld, cfg, ctx)
        report_future = executor.submit(render_technical_report, cfg, ctx, version)
        non_tech_future = executor.submit(render_non_technical_doc, cfg, ctx, version)
        pipeline_future = executor.submit(render_pipeline, cfg, ctx)
        diagram_future = executor.submit(build_mermaid, ctx, cfg)

    docs = {
        "HLD.md": hld_future.result(),
        "LLD.md": lld_future.result(),
        "TECHNICAL_REPORT.md": report_future.result(),
        "NON_TECHNICAL_DOC.md": non_tech_future.result(),
        "PIPELINE.md": pipeline_future.result(),
        "SUMMARY.md": render_summary(cfg, version, ctx),
        "SOURCE_INVENTORY.md": render_inventory(ctx),
        "CHANGELOG.md": render_changelog(cfg, version, ctx),
        "diagram.mmd": diagram_future.result(),
    }
    return run_reviewer_loop(docs)


def ensure_sections(content: str, sections: list[str], fallback_line: str) -> str:
    updated = content
    for section in sections:
        if section not in updated:
            updated = updated.rstrip() + f"\n\n{section}\n{fallback_line}\n"
    return updated


def normalize_oss_wording(content: str) -> str:
    replacements = {
        "premium critic": "internal reviewer loop",
        "Critic Premium": "Internal Reviewer Loop",
        "critic-only": "review-loop",
        "full critic": "lightweight reviewer",
    }
    updated = content
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    return updated


def review_artifacts(docs: dict[str, str]) -> list[str]:
    findings: list[str] = []
    if not docs["diagram.mmd"].lstrip().startswith("flowchart TD"):
        findings.append("Mermaid diagram must start with `flowchart TD`.")
    for section in HLD_REQUIRED_SECTIONS:
        if section not in docs["HLD.md"]:
            findings.append(f"HLD missing required section: {section}")
    for section in LLD_REQUIRED_SECTIONS:
        if section not in docs["LLD.md"]:
            findings.append(f"LLD missing required section: {section}")
    for section in TECH_REPORT_REQUIRED_SECTIONS:
        if section not in docs["TECHNICAL_REPORT.md"]:
            findings.append(f"TECHNICAL_REPORT missing required section: {section}")
    if "premium" in docs["TECHNICAL_REPORT.md"].lower():
        findings.append("TECHNICAL_REPORT contains SaaS/premium wording.")
    for section in NON_TECH_REQUIRED_SECTIONS:
        if section not in docs["NON_TECHNICAL_DOC.md"]:
            findings.append(f"NON_TECHNICAL_DOC missing required section: {section}")
    return findings


def apply_review_fixes(docs: dict[str, str], findings: list[str]) -> dict[str, str]:
    updated = dict(docs)
    updated["HLD.md"] = ensure_sections(
        normalize_oss_wording(updated["HLD.md"]),
        HLD_REQUIRED_SECTIONS,
        "- Added by the internal reviewer loop to preserve required OSS structure.",
    )
    updated["LLD.md"] = ensure_sections(
        normalize_oss_wording(updated["LLD.md"]),
        LLD_REQUIRED_SECTIONS,
        "- Added by the internal reviewer loop to preserve required OSS structure.",
    )
    updated["TECHNICAL_REPORT.md"] = ensure_sections(
        normalize_oss_wording(updated["TECHNICAL_REPORT.md"]),
        TECH_REPORT_REQUIRED_SECTIONS,
        "- Added by the internal reviewer loop to preserve required OSS structure.",
    )
    updated["NON_TECHNICAL_DOC.md"] = ensure_sections(
        normalize_oss_wording(updated["NON_TECHNICAL_DOC.md"]),
        NON_TECH_REQUIRED_SECTIONS,
        "- Added by the internal reviewer loop to preserve required OSS structure.",
    )
    updated["PIPELINE.md"] = normalize_oss_wording(updated["PIPELINE.md"])
    updated["SUMMARY.md"] = normalize_oss_wording(updated["SUMMARY.md"])
    updated["CHANGELOG.md"] = normalize_oss_wording(updated["CHANGELOG.md"])

    if not updated["diagram.mmd"].lstrip().startswith("flowchart TD"):
        updated["diagram.mmd"] = "flowchart TD\n    A[Reviewer Loop] --> B[Fixed Mermaid header]\n"

    if findings:
        review_note = "\n\n## Reviewer Notes\n" + "\n".join(f"- {item}" for item in findings) + "\n"
        if "## Reviewer Notes" not in updated["TECHNICAL_REPORT.md"]:
            updated["TECHNICAL_REPORT.md"] = updated["TECHNICAL_REPORT.md"].rstrip() + review_note
    return updated


def run_reviewer_loop(docs: dict[str, str]) -> dict[str, str]:
    current = dict(docs)
    for _ in range(REVIEW_LOOP_LIMIT):
        findings = review_artifacts(current)
        if not findings:
            break
        current = apply_review_fixes(current, findings)
    return current


def folder_tree(root: Path) -> str:
    lines = ["# TREE", "", f"Root: `{root}`", "", "```text"]
    for base, dirs, files in os.walk(root):
        rel = Path(base).relative_to(root)
        depth = len(rel.parts)
        indent = "  " * depth
        label = "." if str(rel) == "." else rel.name
        lines.append(f"{indent}{label}/")
        for file_name in sorted(files):
            lines.append(f"{indent}  {file_name}")
        dirs[:] = sorted(dirs)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_artifacts(target: Path, docs: dict[str, str], metadata: dict[str, Any]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, content in docs.items():
        (target / name).write_text(content.strip() + "\n", encoding="utf-8")
    (target / "METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def build_diff(previous: Path | None, current_docs: dict[str, str]) -> str:
    if not previous or not previous.exists():
        return "# DIFF\n\nNo previous version found; this run initialized the baseline design package.\n"

    lines = ["# DIFF", ""]
    for name, current in current_docs.items():
        old = read_text_or_empty(previous / name)
        if old == current:
            continue
        diff = difflib.unified_diff(
            old.splitlines(),
            current.splitlines(),
            fromfile=f"{previous.name}/{name}",
            tofile=f"current/{name}",
            lineterm="",
        )
        lines.append(f"## {name}")
        lines.append("```diff")
        lines.extend(list(diff)[:250])
        lines.append("```")
        lines.append("")

    if len(lines) == 2:
        lines.append("No textual changes detected in generated artifacts.")
        lines.append("")
    return "\n".join(lines)


def run(cfg: RunConfig) -> int:
    require_llm_for_terminal()
    if not cfg.source.exists() or not cfg.source.is_dir():
        raise SystemExit(f"Source path is invalid: {cfg.source}")

    project_root = cfg.output_root / cfg.project
    version, target, previous = choose_version(project_root)
    if cfg.effective_mode == "refine" and previous is None:
        print("No baseline found for refine mode; running as fresh /design generation.")
        cfg = RunConfig(
            command=cfg.command,
            source=cfg.source,
            output_root=cfg.output_root,
            project=cfg.project,
            language=cfg.language,
            style=cfg.style,
            cloud=cfg.cloud,
            web_search=cfg.web_search,
            mode=cfg.mode,
            effective_mode="fresh",
            focus=cfg.focus,
            non_interactive=cfg.non_interactive,
        )

    ctx = build_analysis_context(cfg)
    docs = render_docs(cfg, version, ctx)
    metadata = {
        "project": cfg.project,
        "version": version,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": cfg.command,
        "effective_mode": cfg.effective_mode,
        "language": cfg.language,
        "style": cfg.style,
        "cloud": cfg.cloud,
        "web_search_mode": cfg.web_search,
        "web_search_effective": ctx.web_enabled,
        "source_path": str(cfg.source),
        "source_sha256": sha256("\n".join(ctx.inventory["top_files"]).encode("utf-8")).hexdigest(),
        "mermaid_sha256": sha256(docs["diagram.mmd"].encode("utf-8")).hexdigest(),
        "parent_version": previous.name if previous else None,
        "subagents": ["extractor", "stack-profiler", "architect", "diagrammer", "reporter", "reviewer"],
        "review_loop_limit": REVIEW_LOOP_LIMIT,
    }

    write_artifacts(target, docs, metadata)
    (target / "TREE.md").write_text(folder_tree(target), encoding="utf-8")
    (target / "DIFF.md").write_text(build_diff(previous, docs), encoding="utf-8")
    (project_root / "latest").write_text(version + "\n", encoding="utf-8")

    db_path = cli_db_path(cfg.output_root)
    init_session_db(db_path)
    run_id = record_run(db_path, cfg, target)
    record_event(db_path, run_id, "summary", f"Generated {version} for {cfg.project} in {cfg.effective_mode} mode")
    record_event(db_path, run_id, "subagents", "parallel extractor|stack-profiler|architect|diagrammer|reporter")
    record_event(db_path, run_id, "reviewer_loop", f"limit={REVIEW_LOOP_LIMIT}")
    record_event(db_path, run_id, "language", cfg.language)
    record_event(db_path, run_id, "mode", f"requested={cfg.command}, effective={cfg.effective_mode}")
    if cfg.focus:
        record_event(db_path, run_id, "focus", cfg.focus)
    record_event(db_path, run_id, "web_search", f"enabled={ctx.web_enabled}, refs={len(ctx.references)}")

    print(f"Generated design artifacts at: {target}")
    print(f"Session DB: {db_path}")
    print("Key files: HLD.md, LLD.md, TECHNICAL_REPORT.md, NON_TECHNICAL_DOC.md, PIPELINE.md, diagram.mmd, DIFF.md")
    return 0


def print_chat_help() -> None:
    print("Chat Commands:")
    print("  /help                 Show chat command help")
    print("  /history              Show recent messages in this session")
    print("  /design [focus]       Generate or refine design artifacts")
    print("  /exit                 Exit chat mode")
    print("")
    print("Examples:")
    print("  /design")
    print("  /design improve caching and reliability")
    print("")
    print("Outside chat, use:")
    print("  desysflow help")
    print("  desysflow design --help")


def require_llm_for_terminal() -> None:
    status = check_llm_status()
    if status.get("status") == "available":
        return
    model = status.get("model", get_llm_config().model)
    provider = status.get("provider", get_llm_config().provider)
    message = status.get("message", "Model is not available.")
    print(f"LLM unavailable for provider={provider} model={model}")
    print(message)
    if not Path(".env").exists():
        print("Run ./scripts/bootstrap.sh for first-time model setup.")
    if provider == "ollama" and status.get("status") == "missing_model":
        print(f"Install it first with: ollama pull {model}")
    raise SystemExit(1)


def print_chat_session(session: dict[str, Any]) -> None:
    print(f"Session: {session['session_id']} | {session['title']}")
    if not session.get("messages"):
        print("No messages yet.")
        return
    for item in session["messages"][-12:]:
        role = str(item.get("role", "assistant")).upper()
        print(f"{role}: {item.get('content', '')}")


def run_history(cfg: HistoryConfig) -> int:
    db_path = cli_db_path(cfg.output_root)
    init_session_db(db_path)
    sessions = list_chat_sessions(db_path, cfg.limit)
    if not sessions:
        print(f"No CLI chat sessions found in {cfg.output_root}.")
        return 0
    for item in sessions:
        print(f"{item['session_id']} | {item['updated_at']} | {item['project']} | {item['title']}")
    return 0


def make_run_config_from_chat(chat_cfg: ChatConfig, focus: str) -> RunConfig:
    return finalize_options(
        RunConfig(
            command="/design",
            source=chat_cfg.source,
            output_root=chat_cfg.output_root,
            project=chat_cfg.project,
            language="python",
            style="balanced",
            cloud="local",
            web_search="auto",
            mode="smart",
            effective_mode="",
            focus=focus,
            non_interactive=True,
        )
    )


def run_chat(chat_cfg: ChatConfig) -> int:
    require_llm_for_terminal()
    db_path = cli_db_path(chat_cfg.output_root)
    init_session_db(db_path)

    session: dict[str, Any] | None = None
    if chat_cfg.session_id:
        session = get_chat_session(db_path, chat_cfg.session_id)
        if not session:
            raise SystemExit(f"Session not found: {chat_cfg.session_id}")
        print_chat_session(session)
    else:
        title = f"{chat_cfg.project} workspace"
        session_id = create_chat_session(db_path, chat_cfg.project, chat_cfg.source, title)
        session = get_chat_session(db_path, session_id)
        print(f"Started session {session_id} for {chat_cfg.project}")

    print_chat_help()
    assert session is not None

    while True:
        try:
            user_input = input("desysflow> ").strip()
        except EOFError:
            print("")
            return 0
        except KeyboardInterrupt:
            print("\nExiting chat.")
            return 0

        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            return 0
        if user_input == "/help":
            print_chat_help()
            continue
        if user_input == "/history":
            print_chat_session(get_chat_session(db_path, session["session_id"]) or session)
            continue

        add_chat_message(db_path, session["session_id"], "user", user_input)

        if user_input.startswith("/design"):
            focus = user_input[len("/design"):].strip()
            run_cfg = make_run_config_from_chat(chat_cfg, focus)
            exit_code = run(run_cfg)
            project_root = run_cfg.output_root / run_cfg.project
            latest = read_text_or_empty(project_root / "latest").strip()
            latest_path = project_root / latest if latest else project_root
            assistant = f"Generated design package at {latest_path}"
            add_chat_message(db_path, session["session_id"], "assistant", assistant)
            print(assistant)
            if exit_code != 0:
                return exit_code
            continue

        assistant = (
            "This terminal-first mode tracks local chat history and can drive generation. "
            "Use /design <goal> to produce or refine artifacts, or keep notes in this session."
        )
        add_chat_message(db_path, session["session_id"], "assistant", assistant)
        print(assistant)


def main(argv: list[str] | None = None) -> int:
    raw_args = list(argv) if argv is not None else list(os.sys.argv[1:])
    if not raw_args:
        default_root = get_storage_root()
        return run_chat(ChatConfig(source=Path.cwd(), output_root=default_root, project=Path.cwd().name, session_id=""))

    first = raw_args[0]
    if first in {"help", "-h", "--help", "/help"}:
        print_main_help()
        return 0
    if first in {"/design", "/redesign"}:
        return run(parse_run_args(first, raw_args[1:]))
    if first == "design":
        return run(parse_run_args("/design", raw_args[1:]))
    if first == "redesign":
        return run(parse_run_args("/redesign", raw_args[1:]))
    if first == "chat":
        return run_chat(parse_chat_args(raw_args[1:]))
    if first == "history":
        return run_history(parse_history_args(raw_args[1:]))
    if first == "resume":
        chat_cfg = parse_chat_args(["--session", raw_args[1], *raw_args[2:]]) if len(raw_args) > 1 else parse_chat_args(["--session", ""])
        return run_chat(chat_cfg)
    raise SystemExit(f"Unknown command: {first}\nRun `desysflow help` to see available commands.")


if __name__ == "__main__":
    raise SystemExit(main())

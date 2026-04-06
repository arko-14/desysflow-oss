"""Session memory and context-compaction utilities."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from services.storage_paths import get_storage_root

MAX_CHAT_MESSAGES = 10
MAX_ARTIFACT_INLINE_CHARS = 1800
ARTIFACT_DIR = "session_artifacts"
SESSION_NOTE_DIR = "sessions"


def now_utc_iso() -> str:
    """Return UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def init_session_state() -> Dict[str, Any]:
    """Initialize trackable session state metadata."""
    ts = now_utc_iso()
    return {
        "status": "created",
        "created_at": ts,
        "updated_at": ts,
        "run_count": 0,
        "last_error": "",
        "last_correction": "",
        "history": [{"at": ts, "status": "created"}],
    }


def mark_session_status(
    session_state: Dict[str, Any],
    status: str,
    *,
    error: str = "",
    correction: str = "",
) -> Dict[str, Any]:
    """Update session status and append timeline history."""
    ts = now_utc_iso()
    session_state["status"] = status
    session_state["updated_at"] = ts
    if error:
        session_state["last_error"] = error
    if correction:
        session_state["last_correction"] = correction
    if status == "completed":
        session_state["run_count"] = int(session_state.get("run_count", 0)) + 1
    session_state.setdefault("history", []).append({"at": ts, "status": status})
    return session_state


def build_repo_context_snapshot() -> Dict[str, Any]:
    """Capture a small local repo snapshot for session context."""
    cwd = Path.cwd()
    branch = _run_capture(["git", "branch", "--show-current"])
    status = _run_capture(["git", "status", "--short"])
    recent_commits = _run_capture(["git", "log", "--oneline", "-5"])
    top_entries = sorted(path.name for path in cwd.iterdir())[:20]
    return {
        "workspace_root": str(cwd),
        "git_branch": branch or "unknown",
        "git_status": status or "clean_or_unavailable",
        "recent_commits": recent_commits or "unavailable",
        "top_entries": top_entries,
    }


def init_session_memory(user_input: str, repo_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Create structured in-session memory."""
    repo = repo_context or build_repo_context_snapshot()
    return {
        "session_title": _title_from_input(user_input),
        "current_state": "Session initialized",
        "task_specification": user_input,
        "files_and_functions": [
            "graph/workflow.py::run_workflow",
            "api/routes.py::/design",
            "api/routes.py::/design/followup",
        ],
        "repo_context": repo,
        "workflow": [],
        "errors_and_corrections": [],
        "codebase_and_docs": [],
        "learnings": [],
        "key_results": [],
        "worklog": [f"{now_utc_iso()} Session created"],
        "rolling_chat_summary": "",
        "artifact_refs": {},
    }


def compact_chat_history(
    chat_history: List[Dict[str, str]],
    memory: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Keep recent chat turns and summarize older context."""
    if len(chat_history) <= MAX_CHAT_MESSAGES:
        return chat_history

    overflow = chat_history[:-MAX_CHAT_MESSAGES]
    kept = chat_history[-MAX_CHAT_MESSAGES:]
    summary_lines = []
    for msg in overflow:
        role = msg.get("role", "unknown")
        content = _truncate(msg.get("content", ""), 160)
        summary_lines.append(f"{role}: {content}")

    existing = memory.get("rolling_chat_summary", "")
    merged = "\n".join(filter(None, [existing, *summary_lines]))
    memory["rolling_chat_summary"] = _truncate(merged, 3000)
    memory.setdefault("worklog", []).append(
        f"{now_utc_iso()} Compacted chat history from {len(chat_history)} messages"
    )
    return kept


def update_memory_after_run(
    memory: Dict[str, Any],
    result: Dict[str, Any],
    *,
    followup_message: str = "",
    warnings: List[str] | None = None,
) -> Dict[str, Any]:
    """Update structured memory after a completed run."""
    requirements = result.get("requirements", {})
    revised = result.get("revised_architecture", {})
    critic_feedback = result.get("critic_feedback", [])
    hld = result.get("hld_report", {})

    memory["current_state"] = "Design generated and reviewed"
    if followup_message:
        memory["task_specification"] = (
            f"{memory.get('task_specification', '')}\nFollow-up: {followup_message}"
        )
        memory.setdefault("workflow", []).append(
            {
                "at": now_utc_iso(),
                "step": "followup_requested",
                "message": _truncate(followup_message, 240),
            }
        )

    summary = hld.get("system_overview", "") or "Architecture generated."
    memory.setdefault("key_results", []).append(_truncate(summary, 240))
    memory.setdefault("workflow", []).append(
        {
            "at": now_utc_iso(),
            "step": "run_completed",
            "requirements_keys": sorted(list(requirements.keys())),
            "services_count": len(revised.get("services", []) or []),
            "critic_findings": len(critic_feedback),
        }
    )

    for finding in critic_feedback[:4]:
        memory.setdefault("learnings", []).append(_truncate(str(finding), 200))

    for warning in warnings or []:
        memory.setdefault("codebase_and_docs", []).append(_truncate(str(warning), 220))

    memory["files_and_functions"] = _dedupe_preserve_order(memory.get("files_and_functions", []))[:20]
    memory["codebase_and_docs"] = _dedupe_preserve_order(memory.get("codebase_and_docs", []))[:20]
    memory.setdefault("worklog", []).append(f"{now_utc_iso()} Run completed")
    memory["learnings"] = _dedupe_preserve_order(memory.get("learnings", []))[:20]
    memory["key_results"] = _dedupe_preserve_order(memory.get("key_results", []))[:20]
    return memory


def record_error_and_correction(
    memory: Dict[str, Any],
    *,
    error: str,
    correction: str,
) -> Dict[str, Any]:
    """Append an error/correction item into memory."""
    item = {
        "at": now_utc_iso(),
        "error": _truncate(error, 500),
        "correction": _truncate(correction, 500),
    }
    memory.setdefault("errors_and_corrections", []).append(item)
    memory.setdefault("worklog", []).append(f"{item['at']} Error recorded")
    return memory


def store_artifact_ref(
    session_id: str,
    name: str,
    payload: Any,
) -> Tuple[str, str]:
    """Store large payload to disk and return (preview, file_ref)."""
    text = _json_text(payload)
    if len(text) <= MAX_ARTIFACT_INLINE_CHARS:
        return text, ""

    artifact_dir = get_storage_root() / ARTIFACT_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    file_path = artifact_dir / f"{session_id}_{name}_{digest}.json"
    if not file_path.exists():
        file_path.write_text(text, encoding="utf-8")
    preview = _truncate(text, 700)
    return preview, str(file_path)


def build_followup_prompt(session: Dict[str, Any], message: str) -> str:
    """Build compact follow-up prompt with session memory."""
    latest_result = session.get("latest_result", {}) or {}
    memory = session.get("memory", {}) or {}
    session_id = session.get("session_id", "session")

    arch_preview, arch_ref = store_artifact_ref(
        session_id,
        "revised_architecture",
        latest_result.get("revised_architecture", {}),
    )
    req_preview, req_ref = store_artifact_ref(
        session_id,
        "requirements",
        latest_result.get("requirements", {}),
    )

    memory_md = memory_to_markdown(memory)
    if len(memory_md) > 2200:
        memory_md = _truncate(memory_md, 2200)

    ref_notes = []
    if arch_ref:
        ref_notes.append(f"Architecture artifact: {arch_ref}")
    if req_ref:
        ref_notes.append(f"Requirements artifact: {req_ref}")
    refs_text = "\n".join(ref_notes) if ref_notes else "No external artifact references."

    return (
        "You are continuing an existing system design conversation.\n\n"
        f"Session memory:\n{memory_md}\n\n"
        f"Original user request:\n{session.get('initial_input', '')}\n\n"
        f"Current architecture preview:\n{arch_preview}\n\n"
        f"Current requirements preview:\n{req_preview}\n\n"
        f"Artifact references:\n{refs_text}\n\n"
        f"User follow-up request:\n{message}\n\n"
        "Regenerate the full design while preserving relevant context and applying requested changes."
    )


def memory_to_markdown(memory: Dict[str, Any]) -> str:
    """Render structured memory into compact markdown for prompts."""
    repo_context = memory.get("repo_context", {}) or {}
    repo_lines = [
        f"- Workspace Root: {repo_context.get('workspace_root', 'unknown')}",
        f"- Git Branch: {repo_context.get('git_branch', 'unknown')}",
        f"- Git Status: {_truncate(str(repo_context.get('git_status', 'unknown')), 220)}",
        f"- Recent Commits: {_truncate(str(repo_context.get('recent_commits', 'unknown')), 220)}",
    ]
    top_entries = repo_context.get("top_entries", [])
    if isinstance(top_entries, list) and top_entries:
        repo_lines.append(f"- Top Entries: {', '.join(str(item) for item in top_entries[:12])}")
    repo_text = "\n".join(repo_lines)

    files_and_functions = "\n".join(
        f"- {item}" for item in (memory.get("files_and_functions", [])[-8:])
    ) or "- none"
    workflow_items = memory.get("workflow", [])
    workflow_lines = []
    for item in workflow_items[-5:]:
        if isinstance(item, dict):
            workflow_lines.append(
                "- "
                + _truncate(
                    ", ".join(f"{key}={value}" for key, value in item.items() if value not in ("", [], {}, None)),
                    220,
                )
            )
    workflow_text = "\n".join(workflow_lines) or "- none"

    errors = memory.get("errors_and_corrections", [])
    errors_lines = []
    for item in errors[-4:]:
        errors_lines.append(
            f"- {item.get('at', '')}: {item.get('error', '')} | fix: {item.get('correction', '')}"
        )
    errors_text = "\n".join(errors_lines) if errors_lines else "- none"

    codebase_and_docs = "\n".join(
        f"- {x}" for x in (memory.get("codebase_and_docs", [])[-6:])
    ) or "- none"
    learnings = "\n".join(f"- {x}" for x in (memory.get("learnings", [])[-5:])) or "- none"
    key_results = "\n".join(f"- {x}" for x in (memory.get("key_results", [])[-5:])) or "- none"
    worklog = "\n".join(f"- {x}" for x in (memory.get("worklog", [])[-6:])) or "- none"
    rolling = memory.get("rolling_chat_summary", "")
    rolling_block = rolling if rolling else "none"

    return (
        f"# Session Title\n{memory.get('session_title', '')}\n\n"
        f"## Current State\n{memory.get('current_state', '')}\n\n"
        f"## Task Specification\n{_truncate(memory.get('task_specification', ''), 700)}\n\n"
        f"## Repo Context\n{repo_text}\n\n"
        f"## Files and Functions\n{files_and_functions}\n\n"
        f"## Workflow\n{workflow_text}\n\n"
        f"## Errors & Corrections\n{errors_text}\n\n"
        f"## Codebase and System Documentation\n{codebase_and_docs}\n\n"
        f"## Learnings\n{learnings}\n\n"
        f"## Key Results\n{key_results}\n\n"
        f"## Worklog\n{worklog}\n\n"
        f"## Rolling Chat Summary\n{rolling_block}\n"
    )


def write_session_note(
    session_id: str,
    session: Dict[str, Any],
) -> str:
    """Persist a readable local session note under ./desysflow."""
    notes_dir = get_storage_root() / SESSION_NOTE_DIR
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = notes_dir / f"{session_id}.md"

    memory = session.get("memory", {}) or {}
    latest_result = session.get("latest_result", {}) or {}
    history = session.get("chat_history", []) or []
    recent_chat = []
    for item in history[-6:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "unknown"))
        content = _truncate(str(item.get("content", "")), 240)
        recent_chat.append(f"- {role}: {content}")
    recent_chat_text = "\n".join(recent_chat) or "- none"

    note = (
        f"# Session {session_id}\n\n"
        f"## Initial Input\n{session.get('initial_input', '')}\n\n"
        f"## Preferred Language\n{session.get('preferred_language', '')}\n\n"
        f"## Diagram Style\n{session.get('diagram_style', '')}\n\n"
        f"## Recent Chat\n{recent_chat_text}\n\n"
        f"## Latest Mermaid Version\n{latest_result.get('mermaid_version', 0)}\n\n"
        f"## Session Memory\n{memory_to_markdown(memory)}\n"
    )
    path.write_text(note, encoding="utf-8")
    return str(path)


def _title_from_input(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "System Design Session"
    return _truncate(cleaned, 70)


def _json_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, indent=2, ensure_ascii=True)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _run_capture(argv: List[str]) -> str:
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return ""
    output = (completed.stdout or "").strip()
    if output:
        return output
    return (completed.stderr or "").strip()

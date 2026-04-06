"""
Mem0 integration helpers with safe fallback behavior.
"""

from __future__ import annotations

import logging
import os
import threading
from importlib.util import find_spec
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Mem0Config:
    """Resolved runtime configuration for Mem0 OSS."""

    enabled: bool
    llm_provider: str
    llm_model: str
    llm_base_url: str
    embedder_provider: str
    embedder_model: str
    qdrant_host: str
    qdrant_port: int
    qdrant_collection: str
    embedder_dims: int
    redis_url: str


def get_mem0_config() -> Mem0Config:
    """Load Mem0 configuration from environment variables."""
    return Mem0Config(
        enabled=os.getenv("MEM0_ENABLED", "true").lower() in {"1", "true", "yes"},
        llm_provider=os.getenv("MEM0_LLM_PROVIDER", "ollama"),
        llm_model=os.getenv("MEM0_LLM_MODEL", os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")),
        llm_base_url=os.getenv("MEM0_LLM_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
        embedder_provider=os.getenv("MEM0_EMBEDDER_PROVIDER", "ollama"),
        embedder_model=os.getenv("MEM0_EMBEDDER_MODEL", "nomic-embed-text"),
        qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
        qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
        qdrant_collection=os.getenv("MEM0_QDRANT_COLLECTION", "desysflow_memories"),
        embedder_dims=int(os.getenv("MEM0_EMBEDDER_DIMS", "768")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )


_MEM0_CLIENT = None
_MEM0_LOCK = threading.Lock()
_MEM0_INIT_ERROR = ""
_MEM0_INIT_ATTEMPTED = False


def _build_mem0_config_payload(cfg: Mem0Config) -> Dict[str, Any]:
    return {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": cfg.qdrant_host,
                "port": cfg.qdrant_port,
                "collection_name": cfg.qdrant_collection,
                "embedding_model_dims": cfg.embedder_dims,
            },
        },
        "history_db_path": ":memory:",
        "llm": {
            "provider": cfg.llm_provider,
            "config": {
                "model": cfg.llm_model,
                "ollama_base_url": cfg.llm_base_url,
            },
        },
        "embedder": {
            "provider": cfg.embedder_provider,
            "config": {
                "model": cfg.embedder_model,
                "ollama_base_url": cfg.llm_base_url,
                "embedding_dims": cfg.embedder_dims,
            },
        },
    }


def _instantiate_mem0(payload: Dict[str, Any]) -> Any:
    memory_cls = None
    import_error = None

    try:
        from mem0 import Memory as MemoryClass
        memory_cls = MemoryClass
    except Exception as exc:
        import_error = exc
        try:
            from mem0ai import Memory as MemoryClass
            memory_cls = MemoryClass
        except Exception:
            raise import_error

    # Compatibility across mem0 versions.
    for builder in ("from_config", "from_config_dict"):
        fn = getattr(memory_cls, builder, None)
        if callable(fn):
            return fn(payload)
    try:
        return memory_cls(config=payload)
    except TypeError:
        return memory_cls(payload)


def get_mem0_client() -> Any:
    """Return singleton Mem0 client or None when unavailable/disabled."""
    global _MEM0_CLIENT, _MEM0_INIT_ERROR, _MEM0_INIT_ATTEMPTED
    if _MEM0_CLIENT is not None:
        return _MEM0_CLIENT

    cfg = get_mem0_config()
    if not cfg.enabled:
        return None
    if _MEM0_INIT_ATTEMPTED:
        return None

    with _MEM0_LOCK:
        if _MEM0_CLIENT is not None:
            return _MEM0_CLIENT
        if _MEM0_INIT_ATTEMPTED:
            return None
        if find_spec("mem0") is None and find_spec("mem0ai") is None:
            _MEM0_INIT_ERROR = "Mem0 module not installed"
            _MEM0_INIT_ATTEMPTED = True
            logger.info("Mem0 not installed; long-term memory is disabled.")
            return None
        try:
            payload = _build_mem0_config_payload(cfg)
            _MEM0_CLIENT = _instantiate_mem0(payload)
            _MEM0_INIT_ERROR = ""
            _MEM0_INIT_ATTEMPTED = True
            return _MEM0_CLIENT
        except Exception as exc:
            _MEM0_INIT_ERROR = str(exc)
            _MEM0_INIT_ATTEMPTED = True
            text = str(exc)
            if (
                "Failed to connect to Ollama" in text
                or "Connection refused" in text
                or "timed out" in text
                or "qdrant" in text.lower()
            ):
                logger.info("Mem0 unavailable in current runtime (service reachability): %s", exc)
            else:
                logger.warning("Mem0 unavailable, continuing without it: %s", exc)
            return None


def add_memory_messages(session_id: str, messages: List[Dict[str, str]]) -> bool:
    """Persist messages into Mem0 if available."""
    client = get_mem0_client()
    if not client:
        return False
    try:
        client.add(messages, user_id=session_id)
        return True
    except Exception as exc:
        logger.warning("Mem0 add failed: %s", exc)
        return False


def search_memory(session_id: str, query: str, limit: int = 4) -> List[str]:
    """Retrieve relevant memory snippets from Mem0."""
    client = get_mem0_client()
    if not client:
        return []
    try:
        result = client.search(query=query, user_id=session_id, limit=limit)
        return _normalize_search_results(result)
    except Exception as exc:
        logger.warning("Mem0 search failed: %s", exc)
        return []


def memory_status(probe: bool = True) -> Dict[str, str]:
    """Expose lightweight Mem0 health/status details."""
    cfg = get_mem0_config()
    if not cfg.enabled:
        return {"status": "disabled", "enabled": "false"}

    # Fast status for startup logs without forcing service probes.
    if not probe:
        if find_spec("mem0") is None and find_spec("mem0ai") is None:
            return {"status": "not_installed", "enabled": "true"}
        return {"status": "configured", "enabled": "true"}

    client = get_mem0_client()
    if client:
        return {"status": "available", "enabled": str(cfg.enabled).lower()}
    return {"status": "unavailable", "enabled": "true", "error": _MEM0_INIT_ERROR[:120]}


def _normalize_search_results(result: Any) -> List[str]:
    if not result:
        return []
    if isinstance(result, dict):
        items = result.get("results") or result.get("data") or []
    elif isinstance(result, list):
        items = result
    else:
        items = []

    lines: List[str] = []
    for item in items[:8]:
        if isinstance(item, str):
            lines.append(item)
            continue
        if not isinstance(item, dict):
            continue
        memory_text = (
            item.get("memory")
            or item.get("text")
            or item.get("content")
            or item.get("value")
            or ""
        )
        if memory_text:
            lines.append(str(memory_text))
    return lines[:8]

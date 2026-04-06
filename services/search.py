"""
Optional smart web-search integration for externally grounded design review.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
_missing_search_lib_logged = False

_SEARCH_TRIGGER_PATTERNS = [
    r"\blatest\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\brecent\b",
    r"\bcompare\b",
    r"\bpricing\b",
    r"\bcost\b",
    r"\bsecurity standard\b",
    r"\bcompliance\b",
    r"\bdocs?\b",
    r"\bdocumentation\b",
    r"\brfc\b",
    r"\bkubernetes\b",
    r"\bpostgres\b",
    r"\bredis\b",
    r"\bqdrant\b",
    r"\baws\b",
    r"\bgcp\b",
    r"\bazure\b",
    r"\bclaude\b",
    r"\bgemini\b",
    r"\bgpt\b",
    r"\bollama\b",
    r"\bversion\b",
]


@dataclass(frozen=True)
class SearchConfig:
    enabled: bool
    max_results: int


def get_search_config() -> SearchConfig:
    return SearchConfig(
        enabled=os.getenv("WEB_SEARCH_ENABLED", "true").lower() in {"1", "true", "yes"},
        max_results=int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5")),
    )


def should_use_web_search(text: str) -> bool:
    """Heuristic gate so the system does not browse every time."""
    normalized = text.lower()
    if len(normalized) < 40:
        return False
    return any(re.search(pattern, normalized) for pattern in _SEARCH_TRIGGER_PATTERNS)


def search_web(query: str, max_results: int | None = None) -> List[Dict[str, str]]:
    """Run web search with best-effort failure handling."""
    cfg = get_search_config()
    if not cfg.enabled:
        return []

    limit = max_results or cfg.max_results
    try:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=limit))
        normalized: List[Dict[str, str]] = []
        for item in results[:limit]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "title": str(item.get("title", "")).strip(),
                    "href": str(item.get("href", "")).strip(),
                    "body": str(item.get("body", "")).strip(),
                }
            )
        return normalized
    except Exception as exc:
        global _missing_search_lib_logged
        if "No module named 'duckduckgo_search'" in str(exc) or "No module named 'ddgs'" in str(exc):
            if not _missing_search_lib_logged:
                logger.warning(
                    "Web search disabled: install 'ddgs' (fallback: duckduckgo-search) to enable grounding. Error: %s",
                    exc,
                )
                _missing_search_lib_logged = True
        else:
            logger.warning("Web search unavailable or failed: %s", exc)
        return []


def format_search_results(results: List[Dict[str, str]]) -> str:
    if not results:
        return ""
    lines: List[str] = []
    for idx, item in enumerate(results, start=1):
        title = item.get("title", "") or "Untitled"
        href = item.get("href", "")
        body = item.get("body", "")
        lines.append(f"{idx}. {title}\nURL: {href}\nSnippet: {body}")
    return "\n\n".join(lines)

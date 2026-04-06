"""
Critic feedback categorization utilities.
"""

from __future__ import annotations

from typing import Dict, List

_SEVERITY_KEYWORDS = {
    "critical": [
        "single point of failure",
        "data loss",
        "outage",
        "breach",
        "critical",
        "no authentication",
        "no encryption",
    ],
    "warning": [
        "risk",
        "missing",
        "bottleneck",
        "concern",
        "cost",
        "latency",
        "throughput",
    ],
}

_CATEGORY_KEYWORDS = {
    "scalability": ["scal", "throughput", "load", "partition", "shard", "capacity"],
    "security": ["security", "auth", "encrypt", "tls", "token", "firewall"],
    "operational": ["deploy", "rollback", "operational", "migration", "runbook"],
    "observability": ["monitor", "observ", "tracing", "metric", "alert", "log"],
    "cost": ["cost", "budget", "expensive", "billing", "waste"],
}


def _detect_severity(text: str) -> str:
    lower = text.lower()
    for keyword in _SEVERITY_KEYWORDS["critical"]:
        if keyword in lower:
            return "critical"
    for keyword in _SEVERITY_KEYWORDS["warning"]:
        if keyword in lower:
            return "warning"
    return "info"


def _detect_category(text: str) -> str:
    lower = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lower:
                return category
    return "general"


def build_critic_summary(findings: List[str]) -> Dict[str, object]:
    """Create structured critic summary with severity/category metadata."""
    items: List[Dict[str, str]] = []
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    category_counts: Dict[str, int] = {}

    for finding in findings:
        text = str(finding)
        severity = _detect_severity(text)
        category = _detect_category(text)

        items.append(
            {
                "text": text,
                "severity": severity,
                "category": category,
            }
        )
        severity_counts[severity] += 1
        category_counts[category] = category_counts.get(category, 0) + 1

    return {
        "counts": {
            "severity": severity_counts,
            "category": category_counts,
            "total": len(items),
        },
        "items": items,
    }

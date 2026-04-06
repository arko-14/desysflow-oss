"""
Deterministic edge-case injection engine — no LLM involved.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _parse_traffic_number(traffic_str: str) -> int:
    """Best-effort extraction of a numeric traffic value from a string.

    Handles formats like '5M', '5 million', '100k', '500000', etc.
    Returns 0 if parsing fails.
    """
    text = traffic_str.lower().replace(",", "").strip()

    # Match patterns like '5m', '5 million', '100k', etc.
    match = re.search(r"([\d.]+)\s*(b|billion|m|million|k|thousand)?", text)
    if not match:
        return 0

    num = float(match.group(1))
    suffix = match.group(2) or ""

    multipliers = {
        "b": 1_000_000_000,
        "billion": 1_000_000_000,
        "m": 1_000_000,
        "million": 1_000_000,
        "k": 1_000,
        "thousand": 1_000,
    }

    return int(num * multipliers.get(suffix, 1))


def inject_edge_cases(
    requirements: Dict[str, Any],
    architectures: List[Dict[str, Any]],
) -> List[str]:
    """Apply deterministic rules to produce edge-case warnings.

    Rules
    -----
    • traffic > 100 000  →  hot-partition risk, DB connection exhaustion
    • consistency == 'strong'  →  leader-election latency risk
    """
    edge_cases: List[str] = []

    traffic_str = str(requirements.get("traffic_estimate", "0"))
    traffic_num = _parse_traffic_number(traffic_str)

    consistency = str(requirements.get("consistency_requirement", "")).lower()

    if traffic_num > 100_000:
        edge_cases.append(
            "Hot-partition risk: At {} estimated traffic, uneven key "
            "distribution may cause hot partitions in distributed stores.".format(
                traffic_str
            )
        )
        edge_cases.append(
            "DB connection exhaustion risk: Connection pools may saturate "
            "under {} traffic without proper pooling and back-pressure.".format(
                traffic_str
            )
        )
        logger.info("Injected high-traffic edge cases (traffic=%d)", traffic_num)

    if "strong" in consistency:
        edge_cases.append(
            "Leader-election latency risk: Strong consistency requires "
            "consensus protocols (Raft / Paxos) which add latency during "
            "leader elections and network partitions."
        )
        logger.info("Injected strong-consistency edge case")

    if not edge_cases:
        edge_cases.append(
            "No critical edge cases detected for the given requirements."
        )

    return edge_cases

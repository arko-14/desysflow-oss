"""
Helpers to keep follow-up diagrams stable across iterations.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_NODE_ID_RE = r"[A-Za-z][A-Za-z0-9_-]*"
_HEADER_RE = re.compile(r"^\s*(flowchart|graph)\s+([A-Za-z]+)\s*$", re.IGNORECASE)
_EDGE_RE = re.compile(rf"^\s*({_NODE_ID_RE})\s*--.*>\s*(.+?)\s*$")
_LABEL_RE = re.compile(r"\|([^|]+)\|")
_FIRST_ID_RE = re.compile(rf"^\s*({_NODE_ID_RE})")


def _normalize_lines(code: str) -> List[str]:
    return [
        part.strip()
        for line in (code or "").splitlines()
        for part in line.split(";")
        if part.strip()
    ]


def _parse_nodes(code: str) -> Tuple[str, List[Tuple[str, str]], Dict[str, str], List[Tuple[str, str, str]]]:
    lines = _normalize_lines(code)
    header = "flowchart TD"
    nodes: List[Tuple[str, str]] = []
    node_by_id: Dict[str, str] = {}
    edges: List[Tuple[str, str, str]] = []

    for line in lines:
        h = _HEADER_RE.match(line)
        if h:
            header = f"{h.group(1)} {h.group(2)}"
            continue

        edge_match = _EDGE_RE.match(line)
        if edge_match:
            src = edge_match.group(1)
            target_fragment = edge_match.group(2)
            t = _FIRST_ID_RE.match(target_fragment)
            if t:
                tgt = t.group(1)
                label_match = _LABEL_RE.search(line)
                label = label_match.group(1).strip() if label_match else ""
                edges.append((src, tgt, label))
            continue

        node_match = re.match(rf"^\s*({_NODE_ID_RE})\s*(.*)$", line)
        if not node_match:
            continue
        node_id = node_match.group(1)
        rest = node_match.group(2).strip()
        label = node_id

        quoted = re.search(r'\["([^"]+)"\]', rest)
        if quoted:
            label = quoted.group(1).strip()
        else:
            bracket = re.search(r"\[([^\]]+)\]", rest)
            if bracket:
                label = bracket.group(1).strip()
            else:
                paren = re.search(r"\(([^)]+)\)", rest)
                if paren:
                    label = paren.group(1).strip()
                else:
                    curly = re.search(r"\{([^}]+)\}", rest)
                    if curly:
                        label = curly.group(1).strip()

        if node_id not in node_by_id:
            node_by_id[node_id] = label
            nodes.append((node_id, label))

    # Ensure edge nodes exist in node set.
    for src, tgt, _ in edges:
        if src not in node_by_id:
            node_by_id[src] = src
            nodes.append((src, src))
        if tgt not in node_by_id:
            node_by_id[tgt] = tgt
            nodes.append((tgt, tgt))

    return header, nodes, node_by_id, edges


def _contains_removal_intent(text: str) -> bool:
    return bool(re.search(r"\b(remove|delete|drop|deprecate|retire|replace)\b", text or "", re.IGNORECASE))


def stabilize_followup_mermaid(previous_code: str, new_code: str, followup_message: str) -> str:
    """
    Preserve core diagram structure on follow-up changes.

    - Default: keep previous nodes/edges and add new ones.
    - When follow-up intent includes remove/delete/drop/replace: allow removals.
    """
    if not previous_code or not new_code:
        return new_code or previous_code

    prev_header, prev_nodes, prev_by_id, prev_edges = _parse_nodes(previous_code)
    new_header, new_nodes, new_by_id, new_edges = _parse_nodes(new_code)
    if not prev_nodes or not new_nodes:
        return new_code

    removal_mode = _contains_removal_intent(followup_message)

    prev_label_to_id = {label: node_id for node_id, label in prev_nodes}
    merged_nodes: List[Tuple[str, str]] = list(prev_nodes)
    merged_by_id: Dict[str, str] = dict(prev_by_id)
    new_to_merged_id: Dict[str, str] = {}

    for node_id, label in new_nodes:
        if label in prev_label_to_id:
            new_to_merged_id[node_id] = prev_label_to_id[label]
            continue
        target_id = node_id
        if target_id in merged_by_id:
            suffix = 2
            while f"{target_id}_{suffix}" in merged_by_id:
                suffix += 1
            target_id = f"{target_id}_{suffix}"
        new_to_merged_id[node_id] = target_id
        if not removal_mode:
            merged_by_id[target_id] = label
            merged_nodes.append((target_id, label))

    def map_edge(edge: Tuple[str, str, str]) -> Tuple[str, str, str] | None:
        src, tgt, label = edge
        mapped_src = new_to_merged_id.get(src, src if src in merged_by_id else None)
        mapped_tgt = new_to_merged_id.get(tgt, tgt if tgt in merged_by_id else None)
        if not mapped_src or not mapped_tgt:
            return None
        return (mapped_src, mapped_tgt, label)

    mapped_new_edges = [item for edge in new_edges if (item := map_edge(edge))]
    if removal_mode:
        # In removal mode, rebuild around the new graph while keeping stable ids for common labels.
        keep_ids = set()
        for src, tgt, _ in mapped_new_edges:
            keep_ids.add(src)
            keep_ids.add(tgt)
        for node_id, label in new_nodes:
            mapped = new_to_merged_id.get(node_id)
            if mapped:
                keep_ids.add(mapped)
                merged_by_id[mapped] = label
        merged_nodes = [(node_id, merged_by_id[node_id]) for node_id in merged_by_id if node_id in keep_ids]
        merged_edges = mapped_new_edges
    else:
        seen_edges = set()
        merged_edges: List[Tuple[str, str, str]] = []
        for edge in prev_edges + mapped_new_edges:
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            merged_edges.append(edge)

    header = new_header or prev_header
    lines = [header]
    for node_id, label in merged_nodes:
        safe = str(label).replace('"', '\\"')
        lines.append(f'    {node_id}["{safe}"]')
    for src, tgt, label in merged_edges:
        if label:
            lines.append(f"    {src} -->|{label}| {tgt}")
        else:
            lines.append(f"    {src} --> {tgt}")
    return "\n".join(lines)

"""
Mermaid Diagram Generator Agent — produces flowchart TD from final architecture.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

from schemas.models import AgentState
from services.llm import get_llm
from utils.parser import normalize_llm_text

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a principal solutions architect and diagramming expert.

Given a system architecture JSON, generate a Mermaid flowchart diagram.

Rules:
- Use `flowchart TD` (top-down) syntax
- Make it look like a professional technical architecture diagram:
  - Use layered subgraphs: Clients, Edge/Gateway, Application Services, Async/Streaming, Data Stores, Observability/Security
  - Label every node clearly with role + technology (e.g. "API Gateway (Nginx/ALB)")
  - Show dependencies and data flow with labeled arrows
  - Include databases, caches, queues, and external services
  - Include at least one conditional/decision node for critical path logic (e.g. cache hit/miss, auth pass/fail)
  - Include edge-case/failure paths (timeouts, retries, DLQ/circuit-breaker/rate-limit) where relevant
  - Include read/write or sync/async distinctions on edges where useful
- Ensure almost all major components are connected by explicit edges; avoid isolated nodes
- Do NOT wrap in markdown code fences — return raw Mermaid syntax only
- Use valid Mermaid identifiers (letters/numbers/underscore/hyphen) and avoid special chars in node IDs

Example format:
flowchart TD
    A[API Gateway] --> B[Auth Service]
    A --> C[Core Service]
    C --> D[(PostgreSQL)]
    C --> E[Redis Cache]

Respond with ONLY the Mermaid diagram — nothing else."""


def _sanitise_mermaid(raw: str) -> str:
    """Clean up LLM output to extract valid Mermaid syntax."""
    # Remove markdown fences if present
    cleaned = re.sub(r"```(?:mermaid)?\s*\n?", "", raw)
    cleaned = re.sub(r"```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    # Ensure it starts with flowchart
    if not cleaned.lower().startswith("flowchart"):
        cleaned = "flowchart TD\n" + cleaned

    return cleaned


def _clean_label(value: Any, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _fallback_mermaid_from_architecture(architecture: Dict[str, Any]) -> str:
    services = [_clean_label(item, "Application Service") for item in architecture.get("services", [])[:4]]
    databases = [_clean_label(item, "Primary Database") for item in architecture.get("databases", [])[:2]]
    queues = [_clean_label(item, "Async Queue") for item in architecture.get("message_queues", [])[:1]]
    caches = [_clean_label(item, "Redis Cache") for item in architecture.get("caching_layer", [])[:1]]
    scale = _clean_label(architecture.get("scaling_strategy"), "Horizontal scaling with stateless services.")

    lines = [
        "flowchart TD",
        "    user[Client / User]",
        "    gateway[Edge / API Gateway]",
        "    user -->|HTTPS request| gateway",
        "",
        "    subgraph app[Application Services]",
    ]
    if services:
        for idx, svc in enumerate(services, 1):
            lines.append(f'        svc{idx}["{svc.replace(chr(34), chr(39))}"]')
        lines.append("    end")
        lines.append(f"    gateway -->|route| svc1")
        for idx in range(1, len(services)):
            lines.append(f"    svc{idx} -->|internal call| svc{idx + 1}")
    else:
        lines.append('        svc1["Core Application Service"]')
        lines.append("    end")
        lines.append("    gateway -->|route| svc1")

    if caches:
        lines.extend([
            "",
            "    subgraph cache[Cache Layer]",
            f'        cache1["{caches[0].replace(chr(34), chr(39))}"]',
            "    end",
            "    svc1 -->|cache read/write| cache1",
        ])

    if databases:
        lines.extend(["", "    subgraph data[Data Stores]"])
        for idx, db in enumerate(databases, 1):
            lines.append(f'        db{idx}[("{db.replace(chr(34), chr(39))}")]')
        lines.append("    end")
        lines.append("    svc1 -->|read/write| db1")

    if queues:
        lines.extend([
            "",
            "    subgraph async[Async Processing]",
            f'        queue1["{queues[0].replace(chr(34), chr(39))}"]',
            '        worker["Background Worker"]',
            "    end",
            "    svc1 -->|publish| queue1",
            "    queue1 -->|consume| worker",
        ])
        if databases:
            lines.append("    worker -->|persist result| db1")

    lines.extend([
        "",
        "    decision{Cache hit?}",
        "    gateway --> decision",
        "    decision -->|yes| svc1",
        "    decision -->|no| svc1",
        '    obs["Observability / Alerts"]',
        "    svc1 -. metrics/logs .-> obs",
    ])
    if queues:
        lines.extend([
            '    dlq["DLQ / Retry Queue"]',
            "    worker -. failure .-> dlq",
        ])
    lines.append(f'    note["Scaling: {scale.replace(chr(34), chr(39))}"]')
    lines.append("    svc1 -. policy .-> note")
    return "\n".join(lines)


def diagram_generator(state: AgentState) -> Dict[str, Any]:
    """LangGraph node — generate Mermaid diagram from final architecture."""
    revised = state.get("revised_architecture", {})
    architectures = state.get("architectures", [])
    requirements = state.get("requirements", {})
    edge_cases = state.get("edge_cases", [])
    critic_feedback = state.get("critic_feedback", [])

    # Prefer revised architecture, fall back to first variant
    architecture = revised if revised else (architectures[0] if architectures else {})

    logger.info("Generating Mermaid diagram")

    user_content = (
        f"Architecture:\n{json.dumps(architecture, indent=2)}\n\n"
        f"Requirements:\n{json.dumps(requirements, indent=2)}\n\n"
        f"Edge cases:\n{json.dumps(edge_cases, indent=2)}\n\n"
        f"Critic feedback:\n{json.dumps(critic_feedback, indent=2)}\n\n"
        "Generate a Mermaid flowchart TD diagram for this architecture."
    )

    llm = get_llm()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        response = llm.invoke(messages)
        raw = normalize_llm_text(
            response.content if hasattr(response, "content") else response
        )
        logger.debug("Diagram response: %s", raw[:500])

        mermaid_code = _sanitise_mermaid(raw)
        if len(mermaid_code.splitlines()) < 4:
            raise ValueError("Model returned an incomplete Mermaid diagram")
        logger.info("Mermaid diagram generated (%d chars)", len(mermaid_code))
        return {"mermaid_code": mermaid_code}

    except Exception as exc:
        logger.warning("Diagram generation fallback used: %s", exc)
        return {"mermaid_code": _fallback_mermaid_from_architecture(architecture)}


_CLOUD_DIAGRAM_PROMPT = """You are a principal architect specialising in {provider} cloud architecture.

Given a system architecture JSON, generate a Mermaid flowchart diagram that uses
{provider}-specific managed service names (e.g. for AWS use "ECS", "RDS", "SQS" etc.).

Rules:
- Use `flowchart TD` (top-down) syntax
- Replace generic component names with the {provider} managed service equivalents
- Produce a professional technical diagram with layered subgraphs:
  Clients, Edge, Compute/Services, Async/Eventing, Data Stores, Observability/Security
- Label every node clearly with the {provider} service name
- Show dependencies and data flow with labeled arrows
- Include databases, caches, queues, and external services
- Include conditional nodes and edge-case/failure paths where appropriate
- Ensure main components are connected by explicit edges
- Do NOT wrap in markdown code fences — return raw Mermaid syntax only

Respond with ONLY the Mermaid diagram — nothing else."""


def generate_cloud_diagram(
    architecture: dict,
    provider: str,
    requirements: dict | None = None,
) -> str:
    """Generate a Mermaid diagram tailored to a specific cloud provider."""
    provider_labels = {
        "aws": "AWS",
        "gcp": "Google Cloud Platform (GCP)",
        "azure": "Microsoft Azure",
        "digitalocean": "DigitalOcean",
        "on_prem": "On-Premises / Self-Hosted",
        "local": "Local / Docker",
    }
    label = provider_labels.get(provider, provider.upper())

    user_content = (
        f"Target cloud provider: {label}\n\n"
        f"Architecture:\n{json.dumps(architecture, indent=2)}\n\n"
    )
    if requirements:
        user_content += f"Requirements:\n{json.dumps(requirements, indent=2)}\n\n"
    user_content += f"Generate a Mermaid flowchart TD diagram using {label} managed services."

    llm = get_llm()
    messages = [
        {"role": "system", "content": _CLOUD_DIAGRAM_PROMPT.format(provider=label)},
        {"role": "user", "content": user_content},
    ]

    try:
        response = llm.invoke(messages)
        raw = normalize_llm_text(
            response.content if hasattr(response, "content") else response
        )
        mermaid_code = _sanitise_mermaid(raw)
        if len(mermaid_code.splitlines()) < 4:
            raise ValueError("Model returned an incomplete Mermaid diagram")
        logger.info("Cloud diagram (%s) generated (%d chars)", provider, len(mermaid_code))
        return mermaid_code
    except Exception as exc:
        logger.warning("Cloud diagram fallback used: %s", exc)
        return _fallback_mermaid_from_architecture(architecture)

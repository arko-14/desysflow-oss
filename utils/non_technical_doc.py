"""Non-technical project brief builder."""

from __future__ import annotations

from typing import Any, Dict, List


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def build_non_technical_doc(result: Dict[str, Any]) -> Dict[str, Any]:
    """Build a product/business-facing summary from workflow outputs."""
    hld = result.get("hld_report", {}) or {}
    requirements = result.get("requirements", {}) or {}
    tech_stack = result.get("tech_stack", {}) or {}
    cloud_infra = result.get("cloud_infrastructure", {}) or {}
    revised = result.get("revised_architecture", {}) or {}

    components = _as_list(hld.get("components"))
    feature_candidates = _as_list(requirements.get("critical_features"))
    if not feature_candidates:
        feature_candidates = [item.get("name", "") for item in components if isinstance(item, dict)]
    feature_candidates = [str(item) for item in feature_candidates if str(item).strip()][:6]

    business_value = [
        "Provides a local-first workflow for turning product ideas and source code into clear architecture outputs.",
        "Reduces ambiguity between product intent, implementation constraints, and deployment direction.",
        "Creates reusable project memory so refinement sessions improve over time instead of restarting from scratch.",
    ]

    audience = [
        "Founders and product leads aligning scope before implementation",
        "Engineering managers planning delivery and architecture direction",
        "Developers who need a practical design baseline before coding",
    ]

    future_improvements = [
        "Shareable stakeholder views for roadmap, delivery phases, and decision logs",
        "Stronger effort and cost framing for different deployment profiles",
        "Project templates tuned for specific domains such as SaaS, data systems, and internal tools",
        "Higher-quality artifact comparison across design versions and refinements",
    ]

    if cloud_infra:
        future_improvements.append("Business-friendly cloud option comparison for local, hybrid, and managed deployments")

    return {
        "title": "Project Brief",
        "summary": hld.get("system_overview", "") or "A local workspace for generating and refining system design outputs.",
        "business_value": business_value,
        "target_users": audience,
        "key_capabilities": feature_candidates,
        "delivery_shape": {
            "preferred_language": requirements.get("preferred_language", ""),
            "scale_expectation": requirements.get("traffic_estimate", ""),
            "latency_target": requirements.get("latency_requirement", ""),
            "budget_constraint": requirements.get("budget_constraint", ""),
            "deployment_preference": ", ".join(cloud_infra.keys()) if isinstance(cloud_infra, dict) else "",
        },
        "go_to_market_notes": [
            "Best positioned as a local product for architecture planning, design communication, and iterative technical scoping.",
            "Strong fit for teams that want practical outputs without a heavy hosted workflow or complex setup.",
        ],
        "delivery_risks": _as_list(hld.get("trade_offs"))[:5],
        "future_improvements": future_improvements,
        "platform_notes": {
            "languages": _as_list(tech_stack.get("languages")),
            "frameworks": _as_list(tech_stack.get("frameworks")),
            "services": _as_list(revised.get("services")),
        },
    }

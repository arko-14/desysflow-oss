"""
Deterministic architecture templates — no LLM involved.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from schemas.models import Requirements

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "event_driven": {
        "description": "Event-driven / real-time streaming architecture",
        "core_services": [
            "API Gateway",
            "Event Ingestion Service",
            "Stream Processor",
            "State Store",
            "Notification Service",
        ],
        "recommended_databases": ["Apache Cassandra", "Redis", "TimescaleDB"],
        "recommended_queues": ["Apache Kafka", "Apache Pulsar"],
        "recommended_caching": ["Redis Cluster", "Memcached"],
        "scaling_hint": "Horizontal auto-scaling with partition-based sharding",
    },
    "ml_pipeline": {
        "description": "Machine-learning / data pipeline architecture",
        "core_services": [
            "API Gateway",
            "Feature Store",
            "Training Pipeline Orchestrator",
            "Model Serving (online)",
            "Batch Inference Engine",
            "Experiment Tracker",
        ],
        "recommended_databases": ["PostgreSQL", "Delta Lake", "Redis"],
        "recommended_queues": ["Apache Kafka", "RabbitMQ"],
        "recommended_caching": ["Redis", "Local LRU Cache"],
        "scaling_hint": "GPU-auto-scaling for training; CPU horizontal scaling for serving",
    },
    "web_scale": {
        "description": "General-purpose web-scale microservices architecture",
        "core_services": [
            "API Gateway",
            "Auth Service",
            "Core Business Service",
            "Background Worker",
            "Admin Dashboard",
        ],
        "recommended_databases": ["PostgreSQL", "MongoDB", "Redis"],
        "recommended_queues": ["RabbitMQ", "Amazon SQS"],
        "recommended_caching": ["Redis", "CDN Edge Cache"],
        "scaling_hint": "Horizontal pod auto-scaling behind a load balancer",
    },
}


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------

def select_template(requirements: Requirements) -> str:
    """Deterministically choose a template key based on extracted requirements.

    Rules:
      • If latency hints at real-time AND traffic is high → event_driven
      • If critical features mention ML/AI/model/training → ml_pipeline
      • Else → web_scale
    """
    latency = requirements.latency_requirement.lower()
    traffic = requirements.traffic_estimate.lower()
    features_text = " ".join(requirements.critical_features).lower()

    is_realtime = any(kw in latency for kw in ["real-time", "realtime", "low", "<", "ms"])
    is_high_traffic = any(kw in traffic for kw in ["m", "million", "100k", "billion", "b"])

    is_ml = any(
        kw in features_text
        for kw in ["ml", "machine learning", "model", "training", "inference", "ai"]
    )

    if is_ml:
        selected = "ml_pipeline"
    elif is_realtime and is_high_traffic:
        selected = "event_driven"
    else:
        selected = "web_scale"

    logger.info("Template selected: %s", selected)
    return selected

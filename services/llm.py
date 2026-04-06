"""Centralised LLM service with provider-aware runtime checks."""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_PROVIDER = "ollama"
_DEFAULT_MODEL = "gpt-oss:20b-cloud"
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_TIMEOUT = 120


@dataclass(frozen=True)
class LLMConfig:
    """Resolved runtime configuration for the selected LLM provider."""

    provider: str
    model: str
    temperature: float
    base_url: str
    timeout: int
    api_key: str


@dataclass(frozen=True)
class CriticLLMConfig:
    """Resolved runtime configuration for judge/critic LLM."""

    provider: str
    model: str
    temperature: float
    base_url: str
    timeout: int
    api_key: str


def get_llm_config() -> LLMConfig:
    provider = os.getenv("LLM_PROVIDER", _DEFAULT_PROVIDER).strip().lower() or _DEFAULT_PROVIDER
    if provider == "openai":
        return LLMConfig(
            provider=provider,
            model=os.getenv("OPENAI_MODEL", os.getenv("LLM_MODEL", "gpt-5.4")).strip() or "gpt-5.4",
            temperature=float(os.getenv("OPENAI_TEMPERATURE", os.getenv("LLM_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
            timeout=int(os.getenv("OPENAI_TIMEOUT", os.getenv("LLM_TIMEOUT", str(_DEFAULT_TIMEOUT)))),
            api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        )
    if provider == "anthropic":
        return LLMConfig(
            provider=provider,
            model=os.getenv("ANTHROPIC_MODEL", os.getenv("LLM_MODEL", "claude-opus-4-1")).strip() or "claude-opus-4-1",
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", os.getenv("LLM_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))),
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").strip(),
            timeout=int(os.getenv("ANTHROPIC_TIMEOUT", os.getenv("LLM_TIMEOUT", str(_DEFAULT_TIMEOUT)))),
            api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        )
    return LLMConfig(
        provider="ollama",
        model=os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", _DEFAULT_MODEL)).strip() or _DEFAULT_MODEL,
        temperature=float(os.getenv("OLLAMA_TEMPERATURE", os.getenv("LLM_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip(),
        timeout=int(os.getenv("OLLAMA_TIMEOUT", os.getenv("LLM_TIMEOUT", str(_DEFAULT_TIMEOUT)))),
        api_key="",
    )


def get_critic_llm_config() -> CriticLLMConfig:
    base = get_llm_config()
    if base.provider == "openai":
        return CriticLLMConfig(
            provider=base.provider,
            model=os.getenv("OPENAI_CRITIC_MODEL", os.getenv("LLM_CRITIC_MODEL", base.model)).strip() or base.model,
            temperature=float(os.getenv("OPENAI_CRITIC_TEMPERATURE", os.getenv("LLM_CRITIC_TEMPERATURE", "0.1"))),
            base_url=base.base_url,
            timeout=int(os.getenv("OPENAI_CRITIC_TIMEOUT", os.getenv("LLM_CRITIC_TIMEOUT", "300"))),
            api_key=base.api_key,
        )
    if base.provider == "anthropic":
        return CriticLLMConfig(
            provider=base.provider,
            model=os.getenv("ANTHROPIC_CRITIC_MODEL", os.getenv("LLM_CRITIC_MODEL", base.model)).strip() or base.model,
            temperature=float(os.getenv("ANTHROPIC_CRITIC_TEMPERATURE", os.getenv("LLM_CRITIC_TEMPERATURE", "0.1"))),
            base_url=base.base_url,
            timeout=int(os.getenv("ANTHROPIC_CRITIC_TIMEOUT", os.getenv("LLM_CRITIC_TIMEOUT", "300"))),
            api_key=base.api_key,
        )
    return CriticLLMConfig(
        provider="ollama",
        model=os.getenv("OLLAMA_CRITIC_MODEL", os.getenv("LLM_CRITIC_MODEL", base.model)).strip() or base.model,
        temperature=float(os.getenv("OLLAMA_CRITIC_TEMPERATURE", os.getenv("LLM_CRITIC_TEMPERATURE", "0.1"))),
        base_url=base.base_url,
        timeout=int(os.getenv("OLLAMA_CRITIC_TIMEOUT", os.getenv("LLM_CRITIC_TIMEOUT", "300"))),
        api_key="",
    )


def check_llm_status() -> dict[str, str]:
    cfg = get_llm_config()
    if cfg.provider == "ollama":
        return _check_ollama_status(cfg)
    if cfg.provider == "openai":
        if not cfg.api_key:
            return _status(cfg, "unavailable", "OPENAI_API_KEY is not set.")
        return _status(cfg, "available", "OpenAI configuration present.")
    if cfg.provider == "anthropic":
        if not cfg.api_key:
            return _status(cfg, "unavailable", "ANTHROPIC_API_KEY is not set.")
        return _status(cfg, "available", "Anthropic configuration present.")
    return _status(cfg, "unavailable", f"Unsupported provider: {cfg.provider}")


def is_llm_available() -> bool:
    return check_llm_status().get("status") == "available"


def get_llm():
    cfg = get_llm_config()
    logger.info(
        "Initialising LLM provider=%s model=%s temperature=%s base_url=%s timeout=%ss",
        cfg.provider,
        cfg.model,
        cfg.temperature,
        cfg.base_url,
        cfg.timeout,
    )
    if cfg.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            timeout=cfg.timeout,
        )
    if cfg.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=cfg.model,
            temperature=cfg.temperature,
            anthropic_api_key=cfg.api_key,
            base_url=cfg.base_url,
            timeout=cfg.timeout,
        )
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=cfg.model,
        temperature=cfg.temperature,
        base_url=cfg.base_url,
        num_predict=4096,
        timeout=cfg.timeout,
    )


def get_critic_llm():
    cfg = get_critic_llm_config()
    logger.info(
        "Initialising critic LLM provider=%s model=%s temperature=%s base_url=%s timeout=%ss",
        cfg.provider,
        cfg.model,
        cfg.temperature,
        cfg.base_url,
        cfg.timeout,
    )
    if cfg.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cfg.model,
            temperature=cfg.temperature,
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            timeout=cfg.timeout,
        )
    if cfg.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=cfg.model,
            temperature=cfg.temperature,
            anthropic_api_key=cfg.api_key,
            base_url=cfg.base_url,
            timeout=cfg.timeout,
        )
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=cfg.model,
        temperature=cfg.temperature,
        base_url=cfg.base_url,
        num_predict=8192,
        timeout=cfg.timeout,
    )


def _check_ollama_status(cfg: LLMConfig) -> dict[str, str]:
    parsed = urlparse(cfg.base_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    try:
        with socket.create_connection((host, port), timeout=1.5):
            pass
    except OSError:
        return _status(cfg, "unavailable", f"Ollama is not reachable at {cfg.base_url}.")

    try:
        response = httpx.get(f"{cfg.base_url.rstrip('/')}/api/tags", timeout=5.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return _status(cfg, "unavailable", f"Could not inspect Ollama models: {exc}")

    models = payload.get("models", [])
    names = {
        str(item.get("name", "")).strip()
        for item in models
        if isinstance(item, dict) and item.get("name")
    }
    if cfg.model not in names:
        return _status(cfg, "missing_model", f"Ollama model '{cfg.model}' is not installed.")
    return _status(cfg, "available", "Ollama model is installed and reachable.")


def _status(cfg: LLMConfig, status: str, message: str) -> dict[str, str]:
    return {
        "status": status,
        "provider": cfg.provider,
        "model": cfg.model,
        "base_url": cfg.base_url,
        "message": message,
    }

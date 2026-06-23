"""
LLM client abstraction.

Supports OpenAI, Anthropic, Ollama, Azure OpenAI, and NVIDIA NIM
(OpenAI-compatible) providers.
"""

from __future__ import annotations

import time
from typing import Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings


# ---------------------------------------------------------------------------
# LLM Client interface
# ---------------------------------------------------------------------------

class LLMClient:
    """Abstract base for LLM providers."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        """Send a prompt to the LLM and return the response text."""
        raise NotImplementedError

    @property
    def provider_name(self) -> str:
        """Return the provider name for logging/display."""
        return self.__class__.__name__


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------

class OpenAIClient(LLMClient):
    """OpenAI GPT-4o / GPT-4 / GPT-3.5 client."""

    def __init__(self) -> None:
        import openai
        self._client = openai.OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        logger.info("OpenAIClient initialised (model={})", self._model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Anthropic implementation
# ---------------------------------------------------------------------------

class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model
        logger.info("AnthropicClient initialised (model={})", self._model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        resp = self._client.messages.create(**kwargs)
        return resp.content[0].text if resp.content else ""


# ---------------------------------------------------------------------------
# Ollama implementation (OpenAI-compatible)
# ---------------------------------------------------------------------------

class OllamaClient(LLMClient):
    """Ollama client via OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        import openai
        self._client = openai.OpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",  # Ollama doesn't require a real key
        )
        self._model = settings.ollama_model
        logger.info("OllamaClient initialised (model={}, base_url={})", self._model, settings.ollama_base_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Azure OpenAI implementation
# ---------------------------------------------------------------------------

class AzureOpenAIClient(LLMClient):
    """Azure OpenAI client."""

    def __init__(self) -> None:
        import openai
        self._client = openai.AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-15-preview",
        )
        self._model = settings.azure_openai_deployment
        logger.info("AzureOpenAIClient initialised (deployment={})", self._model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# NVIDIA NIM implementation (OpenAI-compatible)
# ---------------------------------------------------------------------------

class NvidiaNIMClient(LLMClient):
    """NVIDIA NIM via OpenAI-compatible endpoint (api.build.nvidia.com)."""

    def __init__(self) -> None:
        import openai
        self._client = openai.OpenAI(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
        )
        self._model = settings.nvidia_model
        logger.info("NvidiaNIMClient initialised (model={})", self._model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    Factory function for creating an LLM client by provider name.

    Parameters
    ----------
    provider:
        One of "openai", "anthropic", "ollama", "azure", "nvidia".
        If ``None``, uses ``settings.llm_provider``.

    Returns
    -------
    LLMClient
        An instance of the appropriate client class.
    """
    provider = (provider or settings.llm_provider).lower()

    registry = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "ollama": OllamaClient,
        "azure": AzureOpenAIClient,
        "nvidia": NvidiaNIMClient,
    }

    cls = registry.get(provider)
    if cls is None:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            f"Available: {list(registry.keys())}"
        )

    logger.info("Creating LLM client via factory: provider={}", provider)
    return cls()

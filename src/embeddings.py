"""
Embedding provider abstraction.

Supports sentence-transformers (local) and OpenAI embeddings via a
unified ``EmbeddingProvider`` interface with a factory constructor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, List, Optional, Type

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts and return a list of vectors."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...

    @classmethod
    def create(cls, provider: Optional[str] = None, **kwargs) -> EmbeddingProvider:
        """
        Factory method.

        Parameters
        ----------
        provider:
            One of ``"sentence-transformers"``, ``"openai"``, or ``None``
            (defaults to the value of ``settings.embedding_model`` heuristics).
        **kwargs:
            Passed through to the concrete provider constructor.
        """
        if provider is None:
            provider = cls._detect_provider()
        logger.info("Creating EmbeddingProvider: {}", provider)

        provider_map: Dict[str, Type[EmbeddingProvider]] = {
            "sentence-transformers": SentenceTransformerProvider,
            "openai": OpenAIEmbeddingProvider,
        }

        cls_ = provider_map.get(provider)
        if cls_ is None:
            raise ValueError(
                f"Unknown embedding provider '{provider}'. "
                f"Supported: {list(provider_map.keys())}"
            )
        return cls_(**kwargs)

    @staticmethod
    def _detect_provider() -> str:
        """Heuristic: if the configured model starts with 'sentence-transformers/', use local."""
        model_name = settings.embedding_model
        if model_name.startswith("sentence-transformers/"):
            return "sentence-transformners"
        # Default to sentence-transformers for now; can be overridden.
        return "sentence-transformers"


# ---------------------------------------------------------------------------
# Sentence-Transformers Provider
# ---------------------------------------------------------------------------

class SentenceTransformerProvider(EmbeddingProvider):
    """Local embeddings via sentence-transformers."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self._model_name = model_name or settings.embedding_model
        logger.info("Loading sentence-transformers model: {}", self._model_name)
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._model_name)
        self._dim: int = self._model.get_sentence_embedding_dimension()
        logger.info(
            "SentenceTransformer model loaded (dim={})", self._dim
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def embed_query(self, text: str) -> List[float]:
        emb = self._model.encode(text, show_progress_bar=False)
        return emb.tolist()

    @property
    def dimension(self) -> int:
        return self._dim


# ---------------------------------------------------------------------------
# OpenAI Embedding Provider
# ---------------------------------------------------------------------------

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API-based embeddings."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._model = model or "text-embedding-ada-002"
        api_key = api_key or settings.openai_api_key
        if not api_key:
            raise ValueError(
                "OpenAI API key is required for OpenAIEmbeddingProvider. "
                "Set OPENAI_API_KEY in your .env file."
            )

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        self._client = OpenAI(api_key=api_key)
        self._dim: int = self._resolve_dimension()
        logger.info(
            "OpenAI embedding provider initialised (model={}, dim={})",
            self._model,
            self._dim,
        )

    def _resolve_dimension(self) -> int:
        """Return the known dimension for the chosen model."""
        dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return dimensions.get(self._model, 1536)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self._model, input=texts
        )
        # Sort by index to ensure order is preserved
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [d.embedding for d in sorted_data]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def embed_query(self, text: str) -> List[float]:
        response = self._client.embeddings.create(
            model=self._model, input=[text]
        )
        return response.data[0].embedding

    @property
    def dimension(self) -> int:
        return self._dim
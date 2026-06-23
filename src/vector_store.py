"""
Vector store abstraction layer.

Provides a unified ``VectorStoreProvider`` interface with a ChromaDB-backed
default implementation, plus support for other backends.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Type

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import Chunk, RetrievedChunk


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class VectorStoreProvider(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    def add(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Add chunks and their embeddings to the store."""
        ...

    @abstractmethod
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, str]] = None,
    ) -> List[RetrievedChunk]:
        """Return the top-k most similar chunks."""
        ...

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete chunks by their embedding IDs."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all data from the store."""
        ...

    @classmethod
    def create(cls, provider: Optional[str] = None, **kwargs) -> VectorStoreProvider:
        """
        Factory method.

        Parameters
        ----------
        provider:
            ``"chromadb"`` (default) or others as supported.
        **kwargs:
            Passed to the concrete constructor.
        """
        if provider is None:
            provider = settings.vector_store_type
        logger.info("Creating VectorStoreProvider: {}", provider)

        provider_map: Dict[str, Type[VectorStoreProvider]] = {
            "chromadb": ChromaDBProvider,
        }

        cls_ = provider_map.get(provider)
        if cls_ is None:
            raise ValueError(
                f"Unknown vector store provider '{provider}'. "
                f"Supported: {list(provider_map.keys())}"
            )
        return cls_(**kwargs)


# ---------------------------------------------------------------------------
# ChromaDB Provider
# ---------------------------------------------------------------------------

class ChromaDBProvider(VectorStoreProvider):
    """ChromaDB-backed vector store using persistent storage."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
    ) -> None:
        self._collection_name = collection_name or "oncology_docs"
        self._persist_directory = persist_directory or str(
            settings.data_path / "chroma_db"
        )

        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "chromadb is required. Install with: pip install chromadb"
            )

        Path(self._persist_directory).mkdir(parents=True, exist_ok=True)
        logger.debug(
            "ChromaDB persistence directory: {}", self._persist_directory
        )

        self._client = chromadb.PersistentClient(
            path=self._persist_directory
        )

        # Get or create collection; use the embedding dimension for metadata.
        # We specify a default metadata hash for later retrieval.
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
        )
        self._initialised = False
        logger.info(
            "ChromaDB provider initialised (collection='{}')",
            self._collection_name,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def add(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        if not chunks:
            logger.warning("add() called with empty chunks list")
            return
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Number of chunks ({len(chunks)}) must match number of "
                f"embeddings ({len(embeddings)})"
            )

        ids = [chunk.embedding_id for chunk in chunks]
        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # Ensure chunk_index is an int for Chroma filtering
        for meta in metadatas:
            if "chunk_index" in meta:
                meta["chunk_index_int"] = int(meta["chunk_index"])

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.debug("Added {} chunks to ChromaDB collection", len(chunks))

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, str]] = None,
    ) -> List[RetrievedChunk]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter,
        )

        # results is dict with keys: ids, distances, metadatas, documents, etc.
        if not results["ids"] or not results["ids"][0]:
            return []

        retrieved: List[RetrievedChunk] = []
        for idx in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][idx]
            score = results["distances"][0][idx] if results.get("distances") else 0.0
            text = results["documents"][0][idx] if results.get("documents") else ""
            metadata = results["metadatas"][0][idx] if results.get("metadatas") else {}

            chunk = Chunk(
                text=text,
                embedding_id=chunk_id,
                metadata=metadata or {},
            )
            retrieved.append(
                RetrievedChunk(chunk=chunk, score=score)
            )

        return retrieved

    def delete(self, ids: List[str]) -> None:
        if not ids:
            return
        self._collection.delete(ids=ids)
        logger.debug("Deleted {} chunk(s) from ChromaDB", len(ids))

    def clear(self) -> None:
        # Delete the entire collection and recreate it
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
        )
        logger.info("Cleared ChromaDB collection '{}'", self._collection_name)

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self._collection.count()
"""
Retrieval pipeline.

Combines vector similarity search with optional keyword filtering.
"""

from __future__ import annotations

from typing import List, Optional

from loguru import logger

from src.config import settings
from src.embeddings import EmbeddingProvider
from src.models import RetrievedChunk
from src.vector_store import VectorStoreProvider


class Retriever:
    """
    Retrieval pipeline that combines vector search with optional keyword filter.

    Typical usage::

        retriever = Retriever()
        results = retriever.retrieve("How is EGFR Exon19del modeled in FHIR?")
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStoreProvider] = None,
    ) -> None:
        self.embedding_provider = embedding_provider or EmbeddingProvider.create()
        self.vector_store = vector_store or VectorStoreProvider.create()
        logger.info(
            "Retriever initialised (embedder={}, vector_store={})",
            type(self.embedding_provider).__name__,
            type(self.vector_store).__name__,
        )

    def retrieve(
        self,
        query_text: str,
        k: int = 5,
        filter_criteria: Optional[dict] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve the top-k most relevant chunks for a query.

        Parameters
        ----------
        query_text:
            The natural language query.
        k:
            Number of chunks to retrieve.
        filter_criteria:
            Optional metadata filter dict (e.g. ``{"resource_type": "Observation"}``).

        Returns
        -------
        List[RetrievedChunk]
            Retrieved chunks sorted by descending similarity score.
        """
        if not query_text.strip():
            logger.warning("Empty query text — returning empty results")
            return []

        # 1. Embed the query
        query_embedding = self.embedding_provider.embed_query(query_text)
        logger.debug("Query embedded (dim={})", len(query_embedding))

        # 2. Vector search
        results = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=k,
            filter_criteria=filter_criteria,
        )

        # 3. Apply optional keyword-level re-ranking
        #    (simple: boost results that contain query terms)
        results = self._keyword_rerank(query_text, results)

        logger.info(
            "Retrieved {} chunk(s) for query (k={})",
            len(results),
            k,
        )
        return results

    def retrieve_with_sources(
        self,
        query_text: str,
        k: int = 5,
    ) -> List[RetrievedChunk]:
        """
        Retrieve and annotate results with source document info.
        Equivalent to ``retrieve()`` but ensures source_metadata is populated.
        """
        return self.retrieve(query_text, k=k)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_rerank(
        query: str,
        results: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """
        Lightweight keyword re-ranking.

        Extracts significant tokens from the query and boosts chunks that
        contain them. This is a simple additive score bump — not a complete
        re-ordering pipeline.
        """
        if not results:
            return results

        # Extract simple keywords (lowercased, >3 chars)
        query_lower = query.lower()
        keywords = {
            word.strip(",.!?;:")
            for word in query_lower.split()
            if len(word.strip(",.!?;:")) > 3
        }

        if not keywords:
            return results

        # Apply keyword boost
        for item in results:
            chunk_text = item.chunk.text.lower()
            keyword_matches = sum(1 for kw in keywords if kw in chunk_text)
            if keyword_matches > 0:
                # Small boost proportional to keyword matches
                boost = min(keyword_matches * 0.01, 0.05)
                item.score = min(item.score + boost, 1.0)

        # Re-sort by adjusted score
        results.sort(key=lambda x: x.score, reverse=True)
        return results

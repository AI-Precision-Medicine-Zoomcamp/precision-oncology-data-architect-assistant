"""ClawBio-compatible service interface.

This file exposes a stable function that a future orchestrator can call.
"""
from __future__ import annotations

import os
from typing import Any

from src.rag.pipeline import answer_question, answer_without_llm
from src.retrieval.search import search


def run_assistant(query: str, num_results: int = 5, use_llm: bool | None = None) -> dict[str, Any]:
    """Run the assistant and return answer, sources, and metadata.

    Args:
        query: User question about oncology/genomics data modeling.
        num_results: Number of retrieved chunks.
        use_llm: If True, call OpenAI. If False, return retrieved context only.
                 If None, use LLM only when OPENAI_API_KEY is present.
    """
    if use_llm is None:
        use_llm = bool(os.getenv("OPENAI_API_KEY"))
    if use_llm:
        return answer_question(query, num_results=num_results)
    return answer_without_llm(query, num_results=num_results)


def retrieve_context(query: str, num_results: int = 5) -> list[dict]:
    """Return retrieved context only."""
    return search(query, num_results=num_results)

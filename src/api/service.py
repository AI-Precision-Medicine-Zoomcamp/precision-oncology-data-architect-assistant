"""ClawBio-compatible service interface.

This file exposes a stable function that a future orchestrator can call.
"""
from __future__ import annotations

from typing import Any

from src.rag.pipeline import (
    DEFAULT_PROMPT_VARIANT,
    answer_question,
    answer_without_llm,
    get_llm_provider,
    has_llm_key,
)
from src.retrieval.search import search


def run_assistant(
    query: str,
    num_results: int = 5,
    use_llm: bool | None = None,
    prompt_variant: str = DEFAULT_PROMPT_VARIANT,
) -> dict[str, Any]:
    """Run the assistant and return answer, sources, and metadata.

    Args:
        query: User question about oncology/genomics data modeling.
        num_results: Number of retrieved chunks.
        use_llm: If True, call the configured LLM provider. If False, return
                 retrieved context only. If None, use LLM when the selected
                 provider has an API key configured.
        prompt_variant: Named prompt strategy to use for generated answers.
    """
    if use_llm is None:
        use_llm = has_llm_key(get_llm_provider())
    if use_llm:
        return answer_question(
            query,
            num_results=num_results,
            prompt_variant=prompt_variant,
        )
    return answer_without_llm(
        query,
        num_results=num_results,
        prompt_variant=prompt_variant,
    )


def retrieve_context(query: str, num_results: int = 5) -> list[dict]:
    """Return retrieved context only."""
    return search(query, num_results=num_results)

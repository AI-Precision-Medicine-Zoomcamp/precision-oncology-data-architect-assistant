"""RAG pipeline for precision oncology data modeling questions."""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from monitoring.telemetry import log_query
from src.retrieval.search import search

SYSTEM_PROMPT = """You are a Precision Oncology Data Architect Assistant.
Answer questions about representing oncology and genomics data using FHIR R4, US Core, mCODE, and Genomics Reporting.
Stay within scope: data modeling, resource/profile selection, architecture, and example representation.
Do not provide clinical treatment recommendations, trial matching, or variant pathogenicity interpretation.
Use only the retrieved context. If context is insufficient, say what is missing.
Return practical guidance and include source URLs when available.
"""


def build_context(results: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        blocks.append(
            f"Source {i}: {r.get('source_name')}\n"
            f"Collection: {r.get('collection')}\n"
            f"URL: {r.get('source_url')}\n"
            f"Content:\n{r.get('content')}"
        )
    return "\n\n---\n\n".join(blocks)


def source_summary(results: list[dict]) -> list[dict]:
    return [
        {
            "name": r.get("source_name"),
            "url": r.get("source_url"),
            "collection": r.get("collection"),
            "chunk_id": r.get("id"),
        }
        for r in results
    ]


def answer_question(query: str, num_results: int = 5, model: str | None = None, log: bool = True) -> dict[str, Any]:
    load_dotenv()
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    results = search(query, num_results=num_results)
    context = build_context(results)
    prompt = f"Context:\n{context}\n\nQuestion:\n{query}\n\nAnswer:"

    client = OpenAI()
    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=prompt,
    )
    payload = {
        "answer": response.output_text,
        "sources": source_summary(results),
        "usage": getattr(response, "usage", None),
        "model": model,
    }
    if log:
        log_query(query=query, answer=payload["answer"], sources=payload["sources"], usage=payload["usage"])
    return payload


def answer_without_llm(query: str, num_results: int = 5) -> dict[str, Any]:
    """Fallback mode useful when OPENAI_API_KEY is not set."""
    results = search(query, num_results=num_results)
    return {
        "answer": "LLM is not enabled. Showing retrieved context only.",
        "sources": source_summary(results),
        "contexts": results,
        "usage": None,
        "model": None,
    }

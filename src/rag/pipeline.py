"""RAG pipeline for precision oncology data modeling questions."""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from monitoring.telemetry import log_query
from src.retrieval.search import search

PROMPT_VARIANTS = {
    "strict_grounded": """You are a Precision Oncology Data Architect Assistant.
Answer questions about representing oncology and genomics data using FHIR R4, US Core, mCODE, and Genomics Reporting.
Stay within scope: data modeling, resource/profile selection, architecture, and example representation.
Do not provide clinical treatment recommendations, trial matching, or variant pathogenicity interpretation.
Use only the retrieved context. If context is insufficient, say what is missing.
Return practical guidance and include source URLs when available.
""",
    "concise": """You are a Precision Oncology Data Architect Assistant.
Answer only data-modeling questions about FHIR R4, US Core, mCODE, and Genomics Reporting.
Use only the retrieved context, keep the answer concise, and cite source URLs when available.
If the retrieved context is insufficient or the question asks for treatment advice, say so.
""",
    "implementation_steps": """You are a Precision Oncology Data Architect Assistant.
Use only the retrieved context to answer healthcare data architecture questions.
Structure the answer as practical implementation guidance: relevant FHIR resources or profiles, important links between resources, terminology notes, and source URLs.
Stay out of clinical treatment recommendations, trial matching, and variant pathogenicity interpretation.
If context is insufficient, state what evidence is missing.
""",
}

DEFAULT_PROMPT_VARIANT = "strict_grounded"
SYSTEM_PROMPT = PROMPT_VARIANTS[DEFAULT_PROMPT_VARIANT]


def get_system_prompt(prompt_variant: str = DEFAULT_PROMPT_VARIANT) -> str:
    """Return the selected system prompt variant for answer generation."""
    if prompt_variant not in PROMPT_VARIANTS:
        valid = ", ".join(sorted(PROMPT_VARIANTS))
        raise ValueError(f"Unknown prompt_variant '{prompt_variant}'. Valid values: {valid}")
    return PROMPT_VARIANTS[prompt_variant]


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


def get_llm_provider() -> str:
    load_dotenv(override=True)
    return os.getenv("LLM_PROVIDER", "groq").lower().strip()


def has_llm_key(provider: str) -> bool:
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY"))
    if provider == "openrouter":
        return bool(os.getenv("OPENROUTER_API_KEY"))
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    return False


def generate_answer_with_groq(
    prompt: str,
    model: str | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> tuple[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not set.")

    model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content, getattr(response, "usage", None)


def generate_answer_with_openrouter(
    prompt: str,
    model: str | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> tuple[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set.")

    model = model or os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content, getattr(response, "usage", None)


def generate_answer_with_openai(
    prompt: str,
    model: str | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> tuple[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    return response.choices[0].message.content, getattr(response, "usage", None)


def generate_answer(
    prompt: str,
    model: str | None = None,
    prompt_variant: str = DEFAULT_PROMPT_VARIANT,
) -> tuple[str, Any, str]:
    provider = get_llm_provider()
    system_prompt = get_system_prompt(prompt_variant)

    if provider == "groq":
        answer, usage = generate_answer_with_groq(
            prompt,
            model=model,
            system_prompt=system_prompt,
        )
        return answer, usage, os.getenv("GROQ_MODEL", model or "llama-3.1-8b-instant")

    if provider == "openrouter":
        answer, usage = generate_answer_with_openrouter(
            prompt,
            model=model,
            system_prompt=system_prompt,
        )
        return answer, usage, os.getenv("OPENROUTER_MODEL", model or "meta-llama/llama-3.1-8b-instruct")

    if provider == "openai":
        answer, usage = generate_answer_with_openai(
            prompt,
            model=model,
            system_prompt=system_prompt,
        )
        return answer, usage, os.getenv("OPENAI_MODEL", model or "gpt-4o-mini")

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def answer_question(
    query: str,
    num_results: int = 5,
    model: str | None = None,
    log: bool = True,
    prompt_variant: str = DEFAULT_PROMPT_VARIANT,
) -> dict[str, Any]:
    load_dotenv(override=True)
    get_system_prompt(prompt_variant)

    results = search(query, num_results=num_results)
    context = build_context(results)
    prompt = f"Context:\n{context}\n\nQuestion:\n{query}\n\nAnswer:"

    provider = get_llm_provider()

    if not has_llm_key(provider):
        payload = answer_without_llm(
            query=query,
            num_results=num_results,
            prompt_variant=prompt_variant,
        )
        payload["answer"] = (
            f"LLM provider '{provider}' is selected, but the API key is not configured. "
            "Showing retrieved context only."
        )
        return payload

    try:
        answer, usage, used_model = generate_answer(
            prompt,
            model=model,
            prompt_variant=prompt_variant,
        )
    except Exception as exc:
        payload = answer_without_llm(
            query=query,
            num_results=num_results,
            prompt_variant=prompt_variant,
        )
        payload["answer"] = (
            f"LLM generation failed with provider '{provider}': {exc}\n\n"
            "Showing retrieved context only."
        )
        return payload

    payload = {
        "answer": answer,
        "sources": source_summary(results),
        "contexts": results,
        "usage": usage,
        "model": used_model,
        "provider": provider,
        "prompt_variant": prompt_variant,
    }

    if log:
        log_query(
            query=query,
            answer=payload["answer"],
            sources=payload["sources"],
            usage=payload["usage"],
            provider=payload["provider"],
            model=payload["model"],
        )

    return payload


def answer_without_llm(
    query: str,
    num_results: int = 5,
    prompt_variant: str = DEFAULT_PROMPT_VARIANT,
) -> dict[str, Any]:
    """Fallback mode useful when no LLM API key is set."""
    get_system_prompt(prompt_variant)
    results = search(query, num_results=num_results)

    return {
        "answer": "LLM is not enabled. Showing retrieved context only.",
        "sources": source_summary(results),
        "contexts": results,
        "usage": None,
        "model": None,
        "provider": None,
        "prompt_variant": prompt_variant,
    }

"""FastAPI entrypoint for the precision oncology assistant."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.api.service import retrieve_context, run_assistant


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    num_results: int = Field(default=5, ge=1, le=20)
    use_llm: bool | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    num_results: int = Field(default=5, ge=1, le=20)


app = FastAPI(
    title="Precision Oncology Data Architect Assistant",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/answer")
def answer(request: QueryRequest) -> dict[str, Any]:
    return run_assistant(
        query=request.query,
        num_results=request.num_results,
        use_llm=request.use_llm,
    )


@app.post("/search")
def search(request: SearchRequest) -> dict[str, Any]:
    return {
        "query": request.query,
        "results": retrieve_context(
            query=request.query,
            num_results=request.num_results,
        ),
    }

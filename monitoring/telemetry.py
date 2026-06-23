"""Simple local monitoring and feedback logging.

For Zoomcamp, this provides a minimal monitoring layer:
- stores user query
- stores retrieved source metadata
- stores answer preview
- stores optional user feedback

Logs are written to logs/queries.jsonl.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path("logs/queries.jsonl")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(event: dict[str, Any], path: Path = DEFAULT_LOG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"timestamp": utc_now(), **event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def log_query(query: str, answer: str, sources: list[dict], usage: Any | None = None, path: Path = DEFAULT_LOG_PATH) -> None:
    log_event(
        {
            "event_type": "query",
            "query": query,
            "answer_preview": answer[:1000],
            "sources": sources,
            "usage": str(usage) if usage else None,
        },
        path=path,
    )


def log_feedback(query: str, rating: str, comment: str | None = None, path: Path = DEFAULT_LOG_PATH) -> None:
    log_event(
        {
            "event_type": "feedback",
            "query": query,
            "rating": rating,
            "comment": comment or "",
        },
        path=path,
    )

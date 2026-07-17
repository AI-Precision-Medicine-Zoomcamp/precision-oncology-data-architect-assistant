"""Telemetry loading and aggregation for the local monitoring dashboard."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path("logs/queries.jsonl")


def load_events(path: Path = DEFAULT_LOG_PATH) -> list[dict[str, Any]]:
    """Load JSONL telemetry events, skipping blank lines."""
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                events.append(json.loads(line))
    return events


def event_type_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(event.get("event_type", "unknown")) for event in events))


def feedback_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return dict(
        Counter(
            str(event.get("rating", "unrated"))
            for event in events
            if event.get("event_type") == "feedback"
        )
    )


def source_collection_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    collections: Counter[str] = Counter()
    for event in events:
        for source in event.get("sources", []) or []:
            collections[str(source.get("collection", "unknown"))] += 1
    return dict(collections)


def query_volume_by_day(events: list[dict[str, Any]]) -> dict[str, int]:
    volume: Counter[str] = Counter()
    for event in events:
        if event.get("event_type") != "query":
            continue
        timestamp = str(event.get("timestamp", ""))
        volume[timestamp[:10] or "unknown"] += 1
    return dict(sorted(volume.items()))


def answer_length_buckets(events: list[dict[str, Any]]) -> dict[str, int]:
    buckets = Counter({"0-200": 0, "201-500": 0, "501-1000": 0, "1000+": 0})
    for event in events:
        if event.get("event_type") != "query":
            continue
        length = len(str(event.get("answer_preview", "")))
        if length <= 200:
            buckets["0-200"] += 1
        elif length <= 500:
            buckets["201-500"] += 1
        elif length <= 1000:
            buckets["501-1000"] += 1
        else:
            buckets["1000+"] += 1
    return dict(buckets)


def provider_usage_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    providers: Counter[str] = Counter()
    for event in events:
        if event.get("event_type") == "query":
            providers[str(event.get("provider") or "retrieval_only")] += 1
    return dict(providers)


def summarize(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_events": len(events),
        "event_types": event_type_counts(events),
        "feedback": feedback_counts(events),
        "source_collections": source_collection_counts(events),
        "query_volume_by_day": query_volume_by_day(events),
        "answer_length_buckets": answer_length_buckets(events),
        "provider_usage": provider_usage_counts(events),
    }

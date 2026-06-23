"""Deterministic retrieval evaluation for versioned oncology question sets."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Sequence


@dataclass(frozen=True)
class EvaluationRecord:
    """Ground truth and ranked retrieval output for one question."""

    question_id: str
    category: str
    relevant_chunk_ids: tuple[str, ...]
    retrieved_chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class MetricSummary:
    """Aggregate deterministic retrieval metrics."""

    count: int
    recall_at_k: float
    mean_reciprocal_rank: float
    ndcg_at_k: float


def recall_at_k(
    relevant_ids: Sequence[str], retrieved_ids: Sequence[str], k: int
) -> float:
    """Return the fraction of relevant IDs retrieved in the first *k* results."""
    relevant = set(relevant_ids)
    if not relevant:
        return 1.0
    found = relevant.intersection(retrieved_ids[:k])
    return len(found) / len(relevant)


def reciprocal_rank(
    relevant_ids: Sequence[str], retrieved_ids: Sequence[str]
) -> float:
    """Return reciprocal rank of the first relevant result."""
    relevant = set(relevant_ids)
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    relevant_ids: Sequence[str], retrieved_ids: Sequence[str], k: int
) -> float:
    """Return binary normalized discounted cumulative gain at *k*."""
    relevant = set(relevant_ids)
    if not relevant:
        return 1.0

    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(retrieved_ids[:k], start=1)
        if chunk_id in relevant
    )
    ideal_hits = min(len(relevant), k)
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )
    return dcg / ideal_dcg if ideal_dcg else 0.0


def summarize(records: Iterable[EvaluationRecord], k: int) -> MetricSummary:
    """Aggregate retrieval metrics over records."""
    records = list(records)
    if not records:
        return MetricSummary(0, 0.0, 0.0, 0.0)

    return MetricSummary(
        count=len(records),
        recall_at_k=mean(
            recall_at_k(r.relevant_chunk_ids, r.retrieved_chunk_ids, k)
            for r in records
        ),
        mean_reciprocal_rank=mean(
            reciprocal_rank(r.relevant_chunk_ids, r.retrieved_chunk_ids)
            for r in records
        ),
        ndcg_at_k=mean(
            ndcg_at_k(r.relevant_chunk_ids, r.retrieved_chunk_ids, k)
            for r in records
        ),
    )


def load_jsonl(path: Path) -> list[dict]:
    """Load non-empty JSON objects from a JSONL file."""
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} must contain an object")
            rows.append(row)
    return rows


def join_records(questions: list[dict], results: list[dict]) -> list[EvaluationRecord]:
    """Join ground truth and retrieval results by question ID."""
    result_by_id = {str(row["id"]): row for row in results}
    records: list[EvaluationRecord] = []

    for question in questions:
        question_id = str(question["id"])
        if question_id not in result_by_id:
            raise ValueError(f"Missing retrieval result for question {question_id}")
        relevant = question.get("relevant_chunk_ids")
        if not isinstance(relevant, list):
            raise ValueError(
                f"Question {question_id} must define relevant_chunk_ids"
            )
        retrieved = result_by_id[question_id].get("retrieved_chunk_ids")
        if not isinstance(retrieved, list):
            raise ValueError(
                f"Result {question_id} must define retrieved_chunk_ids"
            )
        records.append(
            EvaluationRecord(
                question_id=question_id,
                category=str(question.get("category", "uncategorized")),
                relevant_chunk_ids=tuple(map(str, relevant)),
                retrieved_chunk_ids=tuple(map(str, retrieved)),
            )
        )
    return records


def build_report(records: list[EvaluationRecord], k: int) -> dict:
    """Build overall and category-level metrics."""
    grouped: dict[str, list[EvaluationRecord]] = defaultdict(list)
    for record in records:
        grouped[record.category].append(record)

    return {
        "k": k,
        "overall": asdict(summarize(records, k)),
        "by_category": {
            category: asdict(summarize(category_records, k))
            for category, category_records in sorted(grouped.items())
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.k < 1:
        parser.error("--k must be at least 1")

    records = join_records(load_jsonl(args.questions), load_jsonl(args.results))
    report = build_report(records, args.k)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

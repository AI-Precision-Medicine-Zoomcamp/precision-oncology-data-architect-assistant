"""Deterministic retrieval evaluation for versioned oncology question sets."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

SOURCE_ALIASES = {
    "fhir": "fhir_r4_core",
}

INDEXED_COLLECTIONS = {"fhir_r4_core", "us_core", "mcode", "genomics_reporting"}


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


@dataclass(frozen=True)
class SourceEvaluationRecord:
    """Ground truth and ranked retrieval output for one CSV fixture question."""

    question_id: str
    category: str
    expected_sources: tuple[str, ...]
    retrieved_sources: tuple[str, ...]
    retrieved_chunk_ids: tuple[str, ...]


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


def parse_expected_sources(value: str) -> tuple[str, ...]:
    """Parse pipe-separated expected source labels from the CSV fixture."""
    return tuple(
        SOURCE_ALIASES.get(source.strip().lower(), source.strip().lower())
        for source in value.split("|")
        if source.strip()
    )


def load_csv_questions(path: Path) -> list[dict]:
    """Load evaluation questions from the tracked CSV fixture."""
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"id", "question", "expected_sources", "category"}
    if not rows:
        raise ValueError(f"{path} has no rows")
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    return rows


def source_recall_at_k(
    expected_sources: Sequence[str], retrieved_sources: Sequence[str], k: int
) -> float:
    """Return fraction of expected source labels seen in first *k* results."""
    expected = set(expected_sources)
    if not expected:
        return 1.0
    found = expected.intersection(source.lower() for source in retrieved_sources[:k])
    return len(found) / len(expected)


def source_reciprocal_rank(
    expected_sources: Sequence[str], retrieved_sources: Sequence[str]
) -> float:
    """Return reciprocal rank of the first result from an expected source."""
    expected = set(expected_sources)
    for rank, source in enumerate(retrieved_sources, start=1):
        if source.lower() in expected:
            return 1.0 / rank
    return 0.0


def source_ndcg_at_k(
    expected_sources: Sequence[str], retrieved_sources: Sequence[str], k: int
) -> float:
    """Return binary nDCG at *k* using source labels as relevance judgments."""
    expected = set(expected_sources)
    if not expected:
        return 1.0

    seen: set[str] = set()
    dcg = 0.0
    for rank, source in enumerate(retrieved_sources[:k], start=1):
        source = source.lower()
        if source in expected and source not in seen:
            dcg += 1.0 / math.log2(rank + 1)
            seen.add(source)
    ideal_hits = min(len(expected), k)
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )
    return dcg / ideal_dcg if ideal_dcg else 0.0


def summarize_source_records(
    records: Iterable[SourceEvaluationRecord], k: int
) -> MetricSummary:
    """Aggregate source-label retrieval metrics over CSV records."""
    records = list(records)
    if not records:
        return MetricSummary(0, 0.0, 0.0, 0.0)

    return MetricSummary(
        count=len(records),
        recall_at_k=mean(
            source_recall_at_k(r.expected_sources, r.retrieved_sources, k)
            for r in records
        ),
        mean_reciprocal_rank=mean(
            source_reciprocal_rank(r.expected_sources, r.retrieved_sources)
            for r in records
        ),
        ndcg_at_k=mean(
            source_ndcg_at_k(r.expected_sources, r.retrieved_sources, k)
            for r in records
        ),
    )


def build_source_report(records: list[SourceEvaluationRecord], k: int) -> dict:
    """Build overall and category-level metrics for live CSV evaluation."""
    grouped: dict[str, list[SourceEvaluationRecord]] = defaultdict(list)
    scored_records: list[SourceEvaluationRecord] = []
    excluded_records: list[SourceEvaluationRecord] = []
    for record in records:
        if set(record.expected_sources).issubset(INDEXED_COLLECTIONS):
            scored_records.append(record)
        else:
            excluded_records.append(record)

    for record in scored_records:
        grouped[record.category].append(record)

    return {
        "k": k,
        "relevance_granularity": "source_collection",
        "overall": asdict(summarize_source_records(scored_records, k)),
        "by_category": {
            category: asdict(summarize_source_records(category_records, k))
            for category, category_records in sorted(grouped.items())
        },
        "excluded_records": [
            {
                "question_id": record.question_id,
                "category": record.category,
                "expected_sources": record.expected_sources,
                "reason": "expected source is not an indexed collection",
            }
            for record in excluded_records
        ],
        "records": [
            {
                "question_id": record.question_id,
                "category": record.category,
                "expected_sources": record.expected_sources,
                "retrieved_sources": record.retrieved_sources[:k],
                "retrieved_chunk_ids": record.retrieved_chunk_ids[:k],
            }
            for record in scored_records
        ],
    }


def run_live_csv_evaluation(path: Path, k: int, strategy: str = "expanded") -> dict:
    """Run retrieval against the active local Minsearch index for CSV fixtures."""
    from src.retrieval.search import search

    records: list[SourceEvaluationRecord] = []
    for row in load_csv_questions(path):
        results = search(row["question"], num_results=k, strategy=strategy)
        records.append(
            SourceEvaluationRecord(
                question_id=str(row["id"]),
                category=str(row["category"]),
                expected_sources=parse_expected_sources(row["expected_sources"]),
                retrieved_sources=tuple(
                    str(result.get("collection", "")).lower()
                    for result in results
                ),
                retrieved_chunk_ids=tuple(str(result.get("id", "")) for result in results),
            )
        )
    report = build_source_report(records, k)
    report["strategy"] = strategy
    return report


def run_strategy_comparison(path: Path, k: int, strategies: Sequence[str]) -> dict:
    """Evaluate multiple retrieval strategies and pick the highest-recall run."""
    runs = {
        strategy: run_live_csv_evaluation(path, k, strategy=strategy)
        for strategy in strategies
    }
    best_strategy = max(
        runs,
        key=lambda strategy: (
            runs[strategy]["overall"]["recall_at_k"],
            runs[strategy]["overall"]["mean_reciprocal_rank"],
            runs[strategy]["overall"]["ndcg_at_k"],
        ),
    )
    return {
        "k": k,
        "comparison_type": "retrieval_strategy",
        "best_strategy": best_strategy,
        "strategies": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--strategy",
        choices=["baseline", "expanded"],
        default="expanded",
        help="Retrieval strategy used for live CSV evaluation.",
    )
    parser.add_argument(
        "--compare-strategies",
        action="store_true",
        help="Compare baseline retrieval against expanded/diversified retrieval.",
    )
    args = parser.parse_args()

    if args.k < 1:
        parser.error("--k must be at least 1")

    if args.results:
        records = join_records(load_jsonl(args.questions), load_jsonl(args.results))
        report = build_report(records, args.k)
    elif args.compare_strategies:
        report = run_strategy_comparison(args.questions, args.k, ("baseline", "expanded"))
    else:
        report = run_live_csv_evaluation(args.questions, args.k, args.strategy)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

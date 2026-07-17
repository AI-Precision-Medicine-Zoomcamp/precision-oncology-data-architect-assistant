"""Search the local knowledge base."""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

DEFAULT_INDEX = Path("data/indexes/minsearch_index.pkl")
DEFAULT_CHUNKS = Path("data/processed/chunks.jsonl")

DOMAIN_EXPANSIONS = {
    "mcode profiles": "mCODE Profiles PrimaryCancerCondition GenomicVariant TumorMarkerTest HumanSpecimen CancerStage",
    "nsclc": "non small cell lung cancer primary cancer condition mCODE Condition",
    "non-small cell": "non small cell lung cancer primary cancer condition mCODE Condition",
    "pd-l1": "PD-L1 molecular biomarker cell receptor ligand immune stain tumor marker test Observation",
    "pdl1": "PD-L1 molecular biomarker cell receptor ligand immune stain tumor marker test Observation",
    "biomarker": "molecular biomarker tumor marker test Observation Genomics Reporting mCODE",
    "bundle": "FHIR Bundle Patient Condition Specimen DiagnosticReport Observation mCODEPatientBundle",
    "molecular report": "Genomics Report DiagnosticReport Observation variant biomarker specimen",
    "genomic finding": "Genomics Reporting Variant Observation GenomicVariant DiagnosticReport",
    "tumor staging": "CancerStage TNMStageGroup TNM Clinical Stage Group mCODE",
}


def load_index(path: Path = DEFAULT_INDEX, chunks_path: Path = DEFAULT_CHUNKS):
    """Load the Minsearch index, rebuilding from chunks when possible."""
    if not path.exists():
        if not chunks_path.exists():
            raise FileNotFoundError(
                f"Missing search index at {path} and processed chunks at {chunks_path}. "
                "Run: python -m src.ingestion.download_sources && "
                "python -m src.ingestion.ingest_documents && "
                "python -m ingestion.index_to_vectordb"
            )
        from src.retrieval.build_index import build_index, load_chunks

        docs = load_chunks(chunks_path)
        index = build_index(docs)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(index, f)
        return index

    with path.open("rb") as f:
        return pickle.load(f)


def expand_query(query: str) -> str:
    """Add transparent domain synonyms for terse oncology/FHIR terms."""
    normalized = query.lower()
    expansions = [
        expansion
        for trigger, expansion in DOMAIN_EXPANSIONS.items()
        if trigger in normalized
    ]
    if not expansions:
        return query
    return f"{query} {' '.join(expansions)}"


def diversify_by_collection(results: list[dict], num_results: int) -> list[dict]:
    """Prefer collection diversity, then fill remaining slots by original rank."""
    selected: list[dict] = []
    selected_ids: set[str] = set()
    seen_collections: set[str] = set()

    for result in results:
        collection = str(result.get("collection", ""))
        result_id = str(result.get("id", ""))
        if collection and collection not in seen_collections:
            selected.append(result)
            selected_ids.add(result_id)
            seen_collections.add(collection)
        if len(selected) == num_results:
            return selected

    for result in results:
        result_id = str(result.get("id", ""))
        if result_id not in selected_ids:
            selected.append(result)
        if len(selected) == num_results:
            return selected

    return selected


def search(
    query: str,
    num_results: int = 5,
    collection: str | None = None,
    strategy: str = "expanded",
) -> list[dict]:
    if strategy not in {"baseline", "expanded"}:
        raise ValueError("strategy must be one of: baseline, expanded")

    index = load_index()
    boost = {"source_name": 2.5, "content": 1.0} if strategy == "expanded" else {"content": 1.0}
    filter_dict = {"collection": collection} if collection else {}
    query_text = expand_query(query) if strategy == "expanded" else query
    raw_results = index.search(
        query=query_text,
        boost_dict=boost,
        filter_dict=filter_dict,
        num_results=num_results if collection else max(num_results * 4, num_results),
    )
    if collection or strategy == "baseline":
        return raw_results
    return diversify_by_collection(raw_results, num_results)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--collection", default=None)
    parser.add_argument("--num-results", type=int, default=5)
    parser.add_argument("--strategy", choices=["baseline", "expanded"], default="expanded")
    args = parser.parse_args()

    for i, r in enumerate(
        search(args.query, args.num_results, args.collection, args.strategy),
        start=1,
    ):
        print(f"\n[{i}] {r.get('source_name')} | {r.get('collection')}")
        print(r.get("source_url", ""))
        print(r.get("content", "")[:700].replace("\n", " "))


if __name__ == "__main__":
    main()

"""Search the local knowledge base."""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

DEFAULT_INDEX = Path("data/indexes/minsearch_index.pkl")


def load_index(path: Path = DEFAULT_INDEX):
    with path.open("rb") as f:
        return pickle.load(f)


def search(query: str, num_results: int = 5, collection: str | None = None) -> list[dict]:
    index = load_index()
    boost = {"source_name": 1.5, "content": 1.0}
    filter_dict = {"collection": collection} if collection else {}
    return index.search(query=query, boost_dict=boost, filter_dict=filter_dict, num_results=num_results)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--collection", default=None)
    parser.add_argument("--num-results", type=int, default=5)
    args = parser.parse_args()

    for i, r in enumerate(search(args.query, args.num_results, args.collection), start=1):
        print(f"\n[{i}] {r.get('source_name')} | {r.get('collection')}")
        print(r.get("source_url", ""))
        print(r.get("content", "")[:700].replace("\n", " "))


if __name__ == "__main__":
    main()

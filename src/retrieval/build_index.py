"""Build a lightweight Minsearch index from processed chunks."""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

from minsearch import Index

DEFAULT_CHUNKS = Path("data/processed/chunks.jsonl")
DEFAULT_INDEX_DIR = Path("data/indexes")


def load_chunks(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_index(docs: list[dict]) -> Index:
    index = Index(
        text_fields=["content", "source_name"],
        keyword_fields=["collection", "source_url", "id"],
    )
    index.fit(docs)
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    args = parser.parse_args()

    docs = load_chunks(args.chunks)
    index = build_index(docs)
    args.index_dir.mkdir(parents=True, exist_ok=True)
    with (args.index_dir / "minsearch_index.pkl").open("wb") as f:
        pickle.dump(index, f)
    print(f"Built index with {len(docs)} chunks: {args.index_dir / 'minsearch_index.pkl'}")


if __name__ == "__main__":
    main()

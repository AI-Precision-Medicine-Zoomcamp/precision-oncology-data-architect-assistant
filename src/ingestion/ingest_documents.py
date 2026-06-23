"""Convert downloaded text pages into chunked JSONL documents."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_PROCESSED_DIR = Path("data/processed")


def chunk_text(text: str, size: int = 1600, overlap: int = 250) -> list[dict]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # Prefer ending at paragraph boundary near the end.
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary > start + size * 0.6:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"start": start, "end": end, "content": chunk})
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def read_metadata(txt_path: Path) -> dict:
    meta_path = txt_path.with_suffix(".metadata.json")
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {"name": txt_path.stem, "url": "", "collection": txt_path.parent.name}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--chunk-size", type=int, default=1600)
    parser.add_argument("--overlap", type=int, default=250)
    args = parser.parse_args()

    args.processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.processed_dir / "chunks.jsonl"
    docs = []
    for txt_path in sorted(args.raw_dir.glob("*/*.txt")):
        meta = read_metadata(txt_path)
        text = txt_path.read_text(encoding="utf-8", errors="ignore")
        for i, chunk in enumerate(chunk_text(text, args.chunk_size, args.overlap)):
            docs.append({
                "id": f"{meta.get('collection', txt_path.parent.name)}::{txt_path.stem}::{i}",
                "collection": meta.get("collection", txt_path.parent.name),
                "source_name": meta.get("name", txt_path.stem),
                "source_url": meta.get("url", ""),
                "chunk_index": i,
                "start": chunk["start"],
                "end": chunk["end"],
                "content": chunk["content"],
            })

    with out_path.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"Wrote {len(docs)} chunks to {out_path}")


if __name__ == "__main__":
    main()

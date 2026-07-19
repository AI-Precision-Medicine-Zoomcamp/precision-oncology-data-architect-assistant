"""Download public documentation pages for the RAG knowledge base.

Usage:
    python -m src.ingestion.download_sources
    python -m src.ingestion.download_sources --collection mcode
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from tqdm import tqdm

DEFAULT_MANIFEST = Path("data/source_manifest.yaml")
DEFAULT_RAW_DIR = Path("data/raw")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "source"


def html_to_text(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = soup.find("title")
    title_text = title.get_text(" ", strip=True) if title else ""
    body = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    text = "\n".join(lines)
    if title_text and title_text not in text[:500]:
        text = f"{title_text}\n\n{text}"
    return text


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def download_url(url: str, timeout: int = 30) -> tuple[str, str]:
    headers = {"User-Agent": "precision-oncology-rag/0.1 (+educational project)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    return resp.text, content_type


def save_source(collection: str, source: dict, raw_dir: Path, overwrite: bool = False) -> dict:
    name = source["name"]
    url = source["url"]
    collection_dir = raw_dir / collection
    collection_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(name)
    html_path = collection_dir / f"{stem}.html"
    txt_path = collection_dir / f"{stem}.txt"
    meta_path = collection_dir / f"{stem}.metadata.json"

    if txt_path.exists() and not overwrite:
        return {"collection": collection, "name": name, "url": url, "status": "exists", "text_path": str(txt_path)}

    html, content_type = download_url(url)
    text = html_to_text(html) if "html" in content_type or "<html" in html[:200].lower() else html
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

    html_path.write_text(html, encoding="utf-8")
    txt_path.write_text(text, encoding="utf-8")
    meta = {
        "collection": collection,
        "name": name,
        "url": url,
        "domain": urlparse(url).netloc,
        "content_type": content_type,
        "sha256": sha256,
        "text_path": str(txt_path),
        "html_path": str(html_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {**meta, "status": "downloaded"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--collection", default=None, help="Optional collection name, e.g. mcode")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    collections = manifest.get("collections", {})
    selected = {args.collection: collections[args.collection]} if args.collection else collections

    results = []
    for collection, cfg in selected.items():
        for source in tqdm(cfg.get("sources", []), desc=f"Downloading {collection}"):
            try:
                results.append(save_source(collection, source, args.raw_dir, args.overwrite))
            except Exception as e:
                results.append({"collection": collection, "name": source.get("name"), "url": source.get("url"), "status": "error", "error": str(e)})

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    (args.raw_dir / "download_report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r["status"] in {"downloaded", "exists"})
    print(f"Finished. {ok}/{len(results)} sources available. Report: {args.raw_dir / 'download_report.json'}")


if __name__ == "__main__":
    main()

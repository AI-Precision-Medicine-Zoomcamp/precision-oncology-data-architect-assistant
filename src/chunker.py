"""
Document chunking module.

Splits ``OncologyDocument`` objects into smaller ``Chunk`` instances
using either recursive character splitting or semantic chunking.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Callable, List, Optional

from loguru import logger

from src.models import Chunk, OncologyDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_embedding_id(doc_source: str, idx: int) -> str:
    """Produce a deterministic embedding ID based on source and chunk index."""
    raw = f"{doc_source}::chunk::{idx}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _default_overlap_fn(text: str, overlap_chars: int) -> str:
    """Return the last *overlap_chars* characters of *text*."""
    return text[-overlap_chars:] if len(text) > overlap_chars else text


def _recursive_split(
    text: str,
    size: int,
    overlap: int,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """
    Recursively split text using a list of separators (like LangChain's
    RecursiveCharacterTextSplitter).

    Prioritises splitting at separators in order: paragraph → sentence → word.
    Falls back to character-level if none of the separators are found.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    chunks: List[str] = []
    _recursive_chunk(text, size, overlap, separators, 0, chunks)
    return chunks


def _recursive_chunk(
    text: str,
    size: int,
    overlap: int,
    separators: List[str],
    sep_idx: int,
    out: List[str],
) -> None:
    """Internal recursion for recursive splitting."""
    if not text:
        return

    if len(text) <= size:
        out.append(text)
        return

    sep = separators[sep_idx] if sep_idx < len(separators) else ""

    if sep == "":
        # Hard character-level split with overlap
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunk = text[start:end]
            out.append(chunk)
            start += size - overlap
            if start >= len(text):
                break
        return

    # Try to split using the current separator
    parts = text.split(sep)
    if len(parts) == 1 and sep_idx + 1 < len(separators):
        # Separator not found — try finer separator
        _recursive_chunk(text, size, overlap, separators, sep_idx + 1, out)
        return

    # Build chunks greedily
    buffer = ""
    for part in parts:
        candidate = (buffer + sep + part).strip() if buffer else part
        if len(candidate) <= size:
            buffer = candidate
        else:
            if buffer:
                out.append(buffer.strip())
            # If part alone is still too big, recurse with finer separator
            if len(part) > size and sep_idx + 1 < len(separators):
                _recursive_chunk(part, size, overlap, separators, sep_idx + 1, out)
            else:
                buffer = part

    if buffer:
        out.append(buffer.strip())


def _semantic_split(
    text: str,
    size: int,
    overlap: int,
    sentence_fn: Optional[Callable[[str], List[str]]] = None,
) -> List[str]:
    """
    Split text into semantically coherent chunks by sentence boundary.

    Uses a simple sentence tokeniser by default (split on ``.`` + space).
    A custom *sentence_fn* can be provided for better NLP-based splitting.
    """
    if sentence_fn is None:
        sentences = _simple_sentencize(text)
    else:
        sentences = sentence_fn(text)

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for sent in sentences:
        sent_len = len(sent)
        # If a single sentence exceeds chunk size, we have to hard-split it
        if sent_len > size:
            # Flush current buffer first
            if current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            # Split the long sentence via recursive character split
            sub_chunks = _recursive_split(sent, size, overlap)
            chunks.extend(sub_chunks)
            continue

        if current_len + sent_len <= size:
            current.append(sent)
            current_len += sent_len + 1  # +1 for space
        else:
            if current:
                chunks.append(" ".join(current))
            # Keep overlap from the end of the previous chunk
            overlap_text = _default_overlap_fn(" ".join(current), overlap) if current else ""
            current = [overlap_text, sent] if overlap_text else [sent]
            current_len = len(overlap_text) + sent_len + 1 if overlap_text else sent_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def _simple_sentencize(text: str) -> List[str]:
    """Simple sentence tokeniser splitting on ``.`` + space / newline."""
    import re
    # Split on sentence-ending punctuation followed by space or newline
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# DocumentChunker
# ---------------------------------------------------------------------------

class DocumentChunker:
    """
    Split ``OncologyDocument`` objects into ``Chunk`` objects.

    Two strategies:
    - ``recursive``: recursive character splitting (paragraph → sentence → word)
    - ``semantic``: sentence-boundary-aware splitting

    Parameters
    ----------
    strategy:
        ``"recursive"`` (default) or ``"semantic"``.
    """

    def __init__(self, strategy: str = "recursive") -> None:
        if strategy not in ("recursive", "semantic"):
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        self.strategy = strategy
        logger.debug("DocumentChunker initialised with strategy='{}'", strategy)

    def chunk(
        self,
        documents: List[OncologyDocument],
        size: int = 1024,
        overlap: int = 128,
    ) -> List[Chunk]:
        """
        Chunk a list of documents.

        Parameters
        ----------
        documents:
            Documents to split.
        size:
            Maximum chunk size in characters.
        overlap:
            Number of characters of overlap between consecutive chunks.

        Returns
        -------
        List[Chunk]
        """
        if not documents:
            logger.warning("chunk() called with empty document list")
            return []

        all_chunks: List[Chunk] = []

        for doc in documents:
            text = doc.content.strip()
            if not text:
                continue

            if self.strategy == "recursive":
                raw_chunks = _recursive_split(text, size, overlap)
            else:
                raw_chunks = _semantic_split(text, size, overlap)

            for idx, chunk_text in enumerate(raw_chunks):
                # Skip fully empty chunks
                if not chunk_text.strip():
                    continue

                embedding_id = _make_embedding_id(doc.source, idx)
                meta = dict(doc.metadata)  # shallow copy
                meta["chunk_index"] = idx
                meta["doc_source"] = doc.source
                meta["chunk_strategy"] = self.strategy
                meta["chunk_size"] = size
                meta["chunk_overlap"] = overlap

                all_chunks.append(
                    Chunk(
                        text=chunk_text.strip(),
                        embedding_id=embedding_id,
                        metadata=meta,
                    )
                )

        logger.info(
            "Chunked {} documents into {} chunks (strategy={}, size={}, overlap={})",
            len(documents),
            len(all_chunks),
            self.strategy,
            size,
            overlap,
        )
        return all_chunks
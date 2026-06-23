"""
Full ingestion pipeline.

Orchestrates: load FHIR bundles → parse → chunk → embed → index to vector store.
Includes progress logging with tqdm.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from loguru import logger
from tqdm.auto import tqdm

from src.chunker import DocumentChunker
from src.config import settings
from src.embeddings import EmbeddingProvider
from src.fhir_parser import FhirBundleParser
from src.models import Chunk, OncologyDocument
from src.vector_store import VectorStoreProvider


# ---------------------------------------------------------------------------
# DataIngestionPipeline
# ---------------------------------------------------------------------------

class DataIngestionPipeline:
    """
    End-to-end ingestion pipeline.

    Typical usage::

        pipeline = DataIngestionPipeline()
        result = pipeline.run()

    Returns summary dict with document, chunk, and error counts.
    """

    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStoreProvider] = None,
        bundle_parser: Optional[FhirBundleParser] = None,
    ) -> None:
        self.chunker = chunker or DocumentChunker()
        self.embedding_provider = embedding_provider or EmbeddingProvider.create()
        self.vector_store = vector_store or VectorStoreProvider.create()
        self.bundle_parser = bundle_parser or FhirBundleParser()

        logger.info(
            "DataIngestionPipeline initialised "
            "(chunker={}, embedder={}, vector_store={})",
            type(self.chunker).__name__,
            type(self.embedding_provider).__name__,
            type(self.vector_store).__name__,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        fhir_bundle_paths: Optional[Sequence[Path]] = None,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
    ) -> Dict[str, int]:
        """
        Run the full ingestion pipeline.

        Parameters
        ----------
        fhir_bundle_paths:
            List of file **paths** or **directories** containing FHIR JSON bundles.
            If ``None``, uses ``settings.fhir_bundles_path``.
        chunk_size:
            Maximum chunk size in characters.
        chunk_overlap:
            Overlap between consecutive chunks.

        Returns
        -------
        Dict[str, int]
            Summary statistics: ``{"documents", "chunks", "errors"}``.
        """
        if fhir_bundle_paths is None:
            fhir_bundle_paths = [settings.fhir_bundles_path]

        # ---- Step 1: Resolve all bundle JSON files ----
        bundle_files: List[Path] = []
        for path in fhir_bundle_paths:
            p = Path(path)
            if p.is_dir():
                bundle_files.extend(sorted(p.glob("*.json")))
            elif p.is_file() and p.suffix == ".json":
                bundle_files.append(p)
            else:
                logger.warning("Skipping invalid path: {}", path)

        if not bundle_files:
            logger.warning("No FHIR bundle JSON files found to ingest")
            return {"documents": 0, "chunks": 0, "errors": 0}

        bundle_files = sorted(set(bundle_files))
        logger.info("Found {} FHIR bundle file(s) to ingest", len(bundle_files))

        # ---- Step 2: Parse each bundle ----
        all_documents: List[OncologyDocument] = []
        parse_errors = 0

        for fpath in tqdm(bundle_files, desc="Parsing FHIR bundles", unit="file"):
            try:
                docs = self.bundle_parser.parse_file(fpath)
                all_documents.extend(docs)
            except Exception as exc:
                logger.error("Failed to parse {}: {}", fpath, exc)
                parse_errors += 1

        if not all_documents:
            logger.warning("No documents extracted from FHIR bundles")
            return {"documents": 0, "chunks": 0, "errors": parse_errors}

        logger.info("Parsed {} document(s) from {} bundle(s)", len(all_documents), len(bundle_files) - parse_errors)

        # ---- Step 3: Chunk all documents ----
        chunks: List[Chunk] = self.chunker.chunk(
            all_documents,
            size=chunk_size,
            overlap=chunk_overlap,
        )

        if not chunks:
            logger.warning("No chunks produced from {} documents", len(all_documents))
            return {
                "documents": len(all_documents),
                "chunks": 0,
                "errors": parse_errors,
            }

        logger.info("Created {} chunk(s) from {} document(s)", len(chunks), len(all_documents))

        # ---- Step 4: Embed all chunks ----
        texts = [chunk.text for chunk in chunks]
        embeddings: List[List[float]] = []

        # Embed all in one batch (small dataset)
        try:
            embeddings = self.embedding_provider.embed(texts)
        except Exception as exc:
            logger.error("Embedding failed: {}", exc)
            embeddings = []

        if not embeddings or len(embeddings) != len(chunks):
            logger.warning("Embedding produced incomplete results (got {}/{}), skipping index", len(embeddings), len(chunks))
            return {
                "documents": len(all_documents),
                "chunks": len(chunks),
                "errors": parse_errors,
            }

        # ---- Step 5: Index to vector store ----
        self.vector_store.add(chunks, embeddings)
        logger.info(
            "Ingestion complete: {} documents → {} chunks → {} embeddings indexed",
            len(all_documents),
            len(chunks),
            len(embeddings),
        )

        return {
            "documents": len(all_documents),
            "chunks": len(chunks),
            "errors": parse_errors,
        }

    def run_single(
        self,
        file_path: Path,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
    ) -> Dict[str, int]:
        """Ingest a single FHIR bundle JSON file."""
        return self.run(
            fhir_bundle_paths=[file_path],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def clear_store(self) -> None:
        """Clear all data from the vector store."""
        self.vector_store.clear()
        logger.info("Vector store cleared")

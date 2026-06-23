"""
Precision Oncology Data Architect Assistant — Configuration Module.

Reads environment variables via pydantic-settings. All config is
accessible from a single ``Settings`` singleton instantiated at import time.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from loguru import logger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _resolve_path(value: str | Path) -> Path:
    """Return an absolute ``Path``, expanding ``~`` and ``$VAR`` references."""
    expanded = os.path.expandvars(os.path.expanduser(str(value)))
    return Path(expanded).resolve()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Application settings loaded from environment / ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────────────────
    llm_provider: Literal["openai", "anthropic", "ollama", "azure", "nvidia"] = Field(
        "openai", alias="LLM_PROVIDER"
    )

    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", alias="OPENAI_MODEL")

    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-3-opus-20240229", alias="ANTHROPIC_MODEL")

    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3", alias="OLLAMA_MODEL")

    azure_openai_endpoint: str = Field("", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field("", alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field("", alias="AZURE_OPENAI_DEPLOYMENT")

    nvidia_api_key: str = Field("", alias="NVIDIA_API_KEY")
    nvidia_model: str = Field(
        "nvidia/gpt-oss-120b-instruct", alias="NVIDIA_MODEL"
    )
    nvidia_base_url: str = Field(
        "https://api.build.nvidia.com/v1", alias="NVIDIA_BASE_URL"
    )

    # ── Embeddings ─────────────────────────────────────────────────────────
    embedding_model: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )

    # ── Vector Store ───────────────────────────────────────────────────────
    vector_store_type: Literal["chroma", "pinecone", "qdrant"] = Field(
        "chroma", alias="VECTOR_STORE_TYPE"
    )
    chroma_persist_dir: str = Field("./chroma_db", alias="CHROMA_PERSIST_DIR")

    pinecone_api_key: str = Field("", alias="PINECONE_API_KEY")
    pinecone_environment: str = Field("us-west1-gcp", alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("oncology-rag", alias="PINECONE_INDEX_NAME")

    qdrant_url: str = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field("", alias="QDRANT_API_KEY")

    # ── Ingestion ──────────────────────────────────────────────────────────
    data_dir: str = Field("./data", alias="DATA_DIR")
    fhir_bundles_dir: str = Field("./data/fhir_examples", alias="FHIR_BUNDLES_DIR")
    knowledge_graph_dir: str = Field("./data/knowledge_graph", alias="KNOWLEDGE_GRAPH_DIR")

    # Chunking strategy
    chunk_size: int = Field(1024, alias="CHUNK_SIZE", ge=64, le=8192)
    chunk_overlap: int = Field(128, alias="CHUNK_OVERLAP", ge=0)

    # ── Application ────────────────────────────────────────────────────────
    streamlit_port: int = Field(8501, alias="STREAMLIT_PORT", ge=1024, le=65535)
    api_port: int = Field(8000, alias="API_PORT", ge=1024, le=65535)
    api_host: str = Field("0.0.0.0", alias="API_HOST")

    # ── Evaluation ─────────────────────────────────────────────────────────
    evaluation_questions_path: str = Field(
        "./data/evaluation_questions", alias="EVALUATION_QUESTIONS_PATH"
    )
    openai_evaluation_model: str = Field("gpt-4o", alias="OPENAI_EVALUATION_MODEL")

    # ------------------------------------------------------------------
    # Derived / computed properties
    # ------------------------------------------------------------------

    @property
    def chroma_persist_path(self) -> Path:
        """Absolute path to the ChromaDB persistence directory."""
        return _resolve_path(self.chroma_persist_dir)

    @property
    def data_path(self) -> Path:
        """Absolute path to the data root."""
        return _resolve_path(self.data_dir)

    @property
    def fhir_bundles_path(self) -> Path:
        """Absolute path to FHIR example bundles."""
        return _resolve_path(self.fhir_bundles_dir)

    @property
    def knowledge_graph_path(self) -> Path:
        """Absolute path to knowledge graph data."""
        return _resolve_path(self.knowledge_graph_dir)

    @property
    def evaluation_questions_path_resolved(self) -> Path:
        """Absolute path to evaluation questions directory."""
        return _resolve_path(self.evaluation_questions_path)

    # ------------------------------------------------------------------
    # Field validators
    # ------------------------------------------------------------------

    @field_validator("chunk_overlap")
    @classmethod
    def _validate_overlap(cls, v: int, info) -> int:
        """Overlap must be less than chunk size."""
        # Access other fields via the info.data dict when available
        chunk_size = info.data.get("chunk_size", 1024)
        if v >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) must be < chunk_size ({chunk_size})"
            )
        return v

    def model_post_init(self, __context) -> None:
        """Log the effective configuration on construction."""
        # Ensure the chroma persist directory exists
        self.chroma_persist_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Settings loaded | "
            f"llm_provider={self.llm_provider} | "
            f"embedding_model={self.embedding_model} | "
            f"vector_store={self.vector_store_type} | "
            f"chunk_size={self.chunk_size} overlap={self.chunk_overlap}"
        )


# Module-level singleton for convenience.
settings = Settings()
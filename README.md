# Precision Oncology Data Architect Assistant

A retrieval-augmented generation (RAG) foundation for converting oncology
FHIR data into searchable clinical context. The project currently focuses on
FHIR bundle parsing, oncology-aware text extraction, document chunking,
embeddings, vector storage, and retrieval.

> **Project status:** early development. The core modules under `src/` are
> implemented, but the API, Streamlit interface, ingestion CLI, evaluation
> workflow, and automated tests are still placeholders.

## Current capabilities

- Parse FHIR R4 bundles into structured oncology-focused text.
- Highlight NSCLC diagnoses and EGFR-related observations.
- Split parsed documents with recursive or sentence-aware chunking.
- Generate local sentence-transformer or OpenAI embeddings.
- Store and query embeddings with persistent ChromaDB storage.
- Re-rank vector search results with lightweight keyword matching.
- Configure multiple LLM providers: OpenAI, Anthropic, Ollama, Azure OpenAI,
  and NVIDIA NIM.
- Load reusable oncology prompts from YAML.

## Repository structure

```text
app/                    API, RAG orchestration, and Streamlit placeholders
data/
  fhir_examples/        Example NSCLC and molecular FHIR bundles
  evaluation_questions/ Evaluation question sets
evaluation/             Evaluation workflow placeholder
ingestion/              Ingestion CLI placeholder
monitoring/             Telemetry placeholder
prompts/                Oncology system prompts
src/                    Core parsing, chunking, embedding, and retrieval code
tests/                  Test suite placeholders
```

## Setup

Python 3.10 or newer is recommended.

```bash
git clone https://github.com/AI-Precision-Medicine-Zoomcamp/precision-oncology-data-architect-assistant.git
cd precision-oncology-data-architect-assistant

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Edit `.env` to select the LLM, embedding, and vector-store configuration.
Never commit real API keys.

The default setup uses:

- `sentence-transformers/all-MiniLM-L6-v2` for local embeddings
- ChromaDB for persistent vector storage
- OpenAI as the configured LLM provider

## Ingest the example FHIR bundles

Until the ingestion CLI is implemented, run the pipeline directly:

```bash
python - <<'PY'
from src.ingestion import DataIngestionPipeline

summary = DataIngestionPipeline().run()
print(summary)
PY
```

The pipeline reads JSON bundles from `data/fhir_examples/` by default and
indexes the generated chunks in ChromaDB.

## Retrieve oncology context

After ingestion:

```bash
python - <<'PY'
from src.retriever import Retriever

results = Retriever().retrieve(
    "How is an EGFR exon 19 deletion represented in this FHIR data?",
    k=5,
)

for result in results:
    print(f"Score: {result.score:.4f}")
    print(result.chunk.text)
    print("-" * 80)
PY
```

## Development

```bash
pytest tests/
```

The test files are currently placeholders, so a successful run does not yet
validate the implemented pipeline.

## Roadmap

- Complete the ingestion command-line entry point.
- Connect retrieval and LLM generation into the RAG pipeline.
- Implement FastAPI and Streamlit interfaces.
- Add unit and integration tests.
- Add retrieval and answer-quality evaluation.
- Add monitoring and telemetry.

## Clinical use disclaimer

This project is a technical prototype for data architecture and educational
use. It is not a medical device and must not be used for clinical diagnosis,
treatment selection, or patient-care decisions without appropriate validation
and professional oversight.

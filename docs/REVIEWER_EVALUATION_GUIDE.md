# Reviewer Evaluation Guide

This guide is intended to help reviewers quickly map the project to common
LLM Zoomcamp capstone scoring areas and reproduce the main checks.

## Submitted Version

- Project branch:
  `https://github.com/AI-Precision-Medicine-Zoomcamp/precision-oncology-data-architect-assistant/tree/justin-implementation`

Use the commit ID entered in the submission form as the authoritative reviewed
version. If this guide is included in the submitted version, it should be
visible from the branch link above.

## Quick Start

Use Python 3.10.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

The app can run in retrieval-only mode without provider keys. For generated
answers, set one of the provider keys in `.env`.

Build or refresh the retrieval index:

```bash
python -m src.ingestion.download_sources
python -m src.ingestion.ingest_documents
python -m ingestion.index_to_vectordb
```

Run the backend API:

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

Run the Streamlit frontend:

```bash
streamlit run app/streamlit_app.py
```

Run the monitoring dashboard:

```bash
PYTHONPATH=. streamlit run monitoring/dashboard.py --server.port 8502
```

## Point-Scoring Areas

| Scoring area | Evidence in this project | Suggested reviewer check |
|---|---|---|
| Problem definition | `README.md` scope section | Confirm the assistant is limited to oncology/genomics data modeling and excludes clinical decision support. |
| Knowledge base / dataset | `data/source_manifest.yaml` | Inspect the public standards sources used for FHIR R4, US Core, mCODE, and Genomics Reporting. |
| Automated ingestion | `src/ingestion/download_sources.py`, `src/ingestion/ingest_documents.py` | Run the ingestion commands and confirm raw documents and JSONL chunks are produced. |
| Chunking | `src/ingestion/ingest_documents.py` | Confirm documents are split into chunk records with source metadata. |
| Retrieval | `src/retrieval/build_index.py`, `src/retrieval/search.py` | Run `/search` or the retrieval evaluation and confirm relevant chunks are returned. |
| LLM integration | `src/rag/pipeline.py`, `.env.example` | Confirm support for Groq, OpenRouter, and OpenAI with retrieval-only fallback. |
| Backend API | `app/api.py` | Start FastAPI and test `GET /health`, `POST /search`, and `POST /answer`. |
| Frontend UI | `app/streamlit_app.py` | Start Streamlit and submit a standards-related question. |
| Evaluation dataset | `evaluation/ground_truth.csv`, `evaluation/questions.csv` | Confirm the project includes reusable question fixtures and expected evidence labels. |
| Retrieval evaluation | `evaluation/retrieval_eval.py` | Run the retrieval evaluation command in the README. |
| Answer evaluation | `evaluation/llm_eval.py` | Run offline smoke evaluation, or LLM mode if keys are available. |
| Monitoring / feedback | `monitoring/telemetry.py`, `monitoring/dashboard.py` | Submit UI feedback and inspect the dashboard charts. |
| Docker reproducibility | `Dockerfile`, `docker-compose.yml` | Run `docker compose config` and `docker compose build`. |
| Documentation | `README.md`, `docs/architecture.md`, `docs/evaluation.md`, `docs/monitoring.md`, `docs/course_requirements.md` | Confirm setup, architecture, evaluation, monitoring, and requirement coverage are documented. |
| Safety / limitations | `README.md`, `src/rag/pipeline.py` system prompt | Confirm the app refuses treatment, trial matching, and variant pathogenicity interpretation scope. |

## API Smoke Tests

Health check:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

Retrieval check:

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"How should oncology genomics data be represented in FHIR?","num_results":3}'
```

Answer check without requiring an LLM key:

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"How should EGFR variants be represented in mCODE?","num_results":3,"use_llm":false}'
```

Answer check with a configured provider key:

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"How should EGFR variants be represented in mCODE?","num_results":3,"use_llm":true}'
```

## Evaluation Commands

Retrieval evaluation:

```bash
mkdir -p artifacts
python evaluation/retrieval_eval.py \
  --questions evaluation/ground_truth.csv \
  --output artifacts/retrieval_metrics.json \
  --k 5
```

Retrieval strategy comparison:

```bash
python evaluation/retrieval_eval.py \
  --questions evaluation/ground_truth.csv \
  --output artifacts/retrieval_strategy_comparison.json \
  --k 5 \
  --compare-strategies
```

Offline answer-context smoke evaluation:

```bash
python evaluation/llm_eval.py --limit 5
```

Generated-answer evaluation, if provider keys are available:

```bash
python evaluation/llm_eval.py --use-llm --limit 5
```

Compare context-only and generated-answer modes:

```bash
python evaluation/llm_eval.py --compare-modes --limit 5
```

## Quality Gates

Reviewers can use these commands as the main reproducibility checks:

```bash
python -m pytest -q
python -m compileall -q app evaluation ingestion monitoring src tests
docker compose config
docker compose build
```

Expected release behavior:

- citations resolve to retrieved chunk IDs;
- unsupported clinical questions abstain or stay out of scope;
- repeated ingestion does not create duplicate indexed chunks;
- no real PHI or provider secrets are committed;
- README commands match the active implementation.

## Notes For Reviewers

- `.env` is intentionally ignored and should not be committed.
- The active runtime uses Minsearch. The older ChromaDB/vector path is kept as
  legacy reference code and is not required for the main Streamlit or FastAPI
  flow.
- The project is an educational prototype for healthcare data modeling, not a
  clinical decision-support tool.

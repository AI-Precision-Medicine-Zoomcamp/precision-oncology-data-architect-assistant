# Maintainer Migration Plan

## Compared trees

**Repository scaffold**

```text
/Users/justin/Downloads/precision-oncology-data-architect-assistant
branch: justin-implementation
base: origin/main at f63d6a4
```

**Local core implementation**

```text
/Users/justin/Documents/precision-oncology-data-architect-assistant
branch: main with uncommitted and untracked implementation files
```

The local tree is a substantial core-library implementation, but it is not a
completed end-to-end application. Its `app/`, `ingestion/` command,
`evaluation/` runner, `monitoring/`, tests, and Docker files are empty.

## 1. Files to copy directly

These files have coherent implementations and no scaffold content to preserve.
They should still receive tests in the same pull request.

| Source file | Destination | Maintainer note |
|---|---|---|
| `src/chunker.py` | `src/chunker.py` | Copy, then test empty input, overlap, long sentences, stable IDs, and both strategies |
| `src/prompts.py` | `src/prompts.py` | Copy; make prompt path configurable in a follow-up |
| `src/llm_client.py` | `src/llm_client.py` | Copy; use mocked contract tests rather than paid live API tests |
| `data/knowledge_graph/placeholder.txt` | Do not copy | Placeholder adds no value |

Exact copy commands:

```bash
SOURCE=/Users/justin/Documents/precision-oncology-data-architect-assistant
TARGET=/Users/justin/Downloads/precision-oncology-data-architect-assistant

cd "$TARGET"
mkdir -p src
cp "$SOURCE/src/chunker.py" src/chunker.py
cp "$SOURCE/src/prompts.py" src/prompts.py
cp "$SOURCE/src/llm_client.py" src/llm_client.py
```

Review the diff before staging:

```bash
git diff -- src/chunker.py src/prompts.py src/llm_client.py
python -m compileall -q src
```

## 2. Files requiring merge

These contain useful implementation but have correctness or integration issues.
Do not copy them and immediately merge the PR.

| File | Keep | Required merge changes |
|---|---|---|
| `src/models.py` | Document, chunk, query, answer, and evaluation models | Replace deprecated naive UTC timestamp; treat hallucination as `1 - rate` or exclude it from a positive average; add explicit citation fields |
| `src/config.py` | Pydantic settings and path helpers | Remove directory creation at import time; align provider names; validate credentials only for the selected provider |
| `src/embeddings.py` | Provider abstraction and local/OpenAI implementations | Fix `sentence-transformners` typo; make embedding model/provider separate settings; test empty and batch inputs |
| `src/vector_store.py` | Chroma adapter | Accept `chroma`; use `upsert` for idempotency; normalize distance to similarity or rename score; avoid mutating chunk metadata; align filter argument |
| `src/retriever.py` | Query embedding and keyword reranking | Pass `filter`, not `filter_criteria`; rerank true similarity scores in descending order; validate `k` |
| `src/ingestion.py` | Parse → chunk → embed → index orchestration | Use configured chunk settings by default; make indexing idempotent; surface embedding/index errors; return indexed count |
| `src/__init__.py` | Public exports | Update only after the merged module contracts are stable |
| `.env.example` | Provider and path inventory | Remove fake key values, default to local-safe configuration, and document only supported backends |
| `prompts/system_prompts.yaml` | Oncology, summary, and extraction prompts | Add numbered evidence citations, explicit abstention, prompt-injection resistance, and clinical-use boundaries |
| `data/evaluation_questions/nsclc_questions.json` | Seventeen useful question ideas | Convert to JSONL and add `answerable`, `relevant_document_ids`, `relevant_chunk_ids`, `required_facts`, `forbidden_claims`, and reference answer |

Known blocking defects:

1. `EmbeddingProvider._detect_provider()` returns
   `sentence-transformners`, which is absent from its provider registry.
2. configuration defaults to `VECTOR_STORE_TYPE=chroma`, while the vector
   store registry only accepts `chromadb`.
3. `Retriever.retrieve()` calls `query(filter_criteria=...)`, while the vector
   store interface accepts `filter`.
4. Chroma distance is stored in a model documented as similarity and then
   sorted as though larger is better.
5. `collection.add()` is not idempotent for stable IDs; repeated ingestion can
   fail instead of updating.
6. `EvaluationResult` averages a hallucination rate into the positive score,
   rewarding a worse value.
7. importing configuration creates the Chroma directory, making imports
   stateful and causing failures in read-only environments.

Recommended workflow for each merge file:

```bash
SOURCE=/Users/justin/Documents/precision-oncology-data-architect-assistant
TARGET=/Users/justin/Downloads/precision-oncology-data-architect-assistant

diff -u "$TARGET/src/embeddings.py" "$SOURCE/src/embeddings.py"
cp "$SOURCE/src/embeddings.py" "$TARGET/src/embeddings.py"
# Apply the required fixes before staging.
git diff -- src/embeddings.py
```

Repeat file-by-file rather than copying the whole `src/` directory.

## 3. Files requiring manual review

| File or area | Why manual review is required |
|---|---|
| `data/fhir_examples/*.json` | Contains patient/practitioner names, full birth dates, and MRN-like identifiers; confirm that every value is synthetic and label it clearly |
| FHIR profile URLs and codes | Confirm current mCODE/FHIR validity and whether non-standard elements such as `stageSummary` are intentional examples |
| `src/fhir_parser.py` | It emits patient and practitioner names into retrievable text; decide whether identity fields should be excluded or redacted |
| `src/llm_client.py` | Confirm supported model names and provider SDK behavior before advertising providers |
| `requirements.txt` from the local tree | It includes many unused and old packages; do not copy it directly |
| Existing README claims | Keep implemented, partial, and planned capabilities separate |
| Clinical language | Ensure the UI and prompts do not imply validated treatment advice |

Suggested privacy review:

```bash
rg -n '"name"|"identifier"|MRN-|birthDate|address|telecom' \
  "$SOURCE/data/fhir_examples"
```

## 4. New files to create

| Path | Purpose |
|---|---|
| `tests/unit/test_models.py` | Validation, scoring, and timestamps |
| `tests/unit/test_fhir_parser.py` | Resource parsing, metadata, and redaction |
| `tests/unit/test_chunker.py` | Boundaries, overlap, IDs, strategies |
| `tests/unit/test_retriever.py` | Filters, score direction, reranking, empty query |
| `tests/integration/test_ingestion.py` | Parse through idempotent vector upsert |
| `tests/integration/test_api.py` | Health and query contracts |
| `data/README.md` | Provenance, synthetic status, schema, licensing, and update policy |
| `data/evaluation/questions.jsonl` | Evidence-ID ground truth |
| `evaluation/rag_eval.py` | Fact, citation, abstention, and forbidden-claim checks |
| `app/schemas.py` | API request/response and citation schemas |
| `app/dependencies.py` | Cached pipeline/provider construction |
| `monitoring/feedback_store.py` | Non-PHI feedback keyed by trace ID |
| `.dockerignore` | Exclude secrets, caches, local indexes, and artifacts |
| `LICENSE` | Explicit project license |

Empty scaffold files to implement rather than copy:

```text
app/api.py
app/rag_pipeline.py
app/streamlit_app.py
ingestion/index_to_vectordb.py
monitoring/telemetry.py
tests/test_api_connections.py
tests/test_ingestion.py
```

Delete `README_TEMPLATE.md` after the final README is accepted.

## 5. README strategy

The updated README in this branch:

- states the migration status truthfully;
- distinguishes core, partial, and missing capabilities;
- includes the target architecture;
- provides setup, Docker, evaluation, and quality-gate commands;
- does not claim the empty API/UI are already runnable.

Update the status table as each PR lands. Do not publish a demo URL or metrics
until they have been reproduced from the merged branch.

## 6. Requirements strategy

The local requirements file should not be copied. It pins old LangChain,
RAGAS, DeepEval, PDF, and data-processing packages that the core code does not
import.

The updated scaffold requirements:

- list direct imports only;
- use versions present in the audited local environment;
- keep evaluation deterministic and dependency-light;
- defer a transitive lock file until the runtime code is integrated.

After merging the core:

```bash
python -m venv .venv-clean
source .venv-clean/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q
pip check
```

If a reproducible transitive lock is required, use a separate generated file:

```bash
python -m pip install pip-tools
pip-compile --generate-hashes --output-file requirements.lock requirements.in
```

## 7. Docker strategy

The updated Dockerfile:

- uses Python 3.10 slim;
- runs as a non-root user;
- excludes local secrets and indexes;
- exposes a FastAPI health check;
- persists data and artifacts through Compose volumes.

The image will not be release-ready until `app.api:app`, `/health`, and the
Streamlit entry point are implemented.

Validation:

```bash
docker compose config
docker compose build
docker compose up
curl --fail http://localhost:8000/health
```

## 8. Evaluation strategy

The updated retrieval evaluator computes:

- Recall@k;
- mean reciprocal rank;
- nDCG@k;
- overall and category-level summaries.

The existing seventeen NSCLC questions are prompts with expected keywords, not
retrieval ground truth. They cannot prove retrieval quality until relevant
document/chunk IDs are labeled.

Migration sequence:

1. Import and sanitize the fixture corpus.
2. Create stable document and chunk IDs.
3. Convert the seventeen questions to JSONL evidence labels.
4. Add the fifty-question benchmark from the capstone report.
5. Save a baseline retrieval run.
6. Add answer facts, citations, abstention, and safety scoring.
7. Run a deterministic subset in CI.

## Exact Git commands

### A. Preserve the maintainer/configuration work

Run in the scaffold checkout:

```bash
cd /Users/justin/Downloads/precision-oncology-data-architect-assistant
git switch justin-implementation
git status --short

git add \
  README.md \
  requirements.txt \
  Dockerfile \
  docker-compose.yml \
  .dockerignore \
  evaluation/retrieval_eval.py \
  evaluation/README.md \
  tests/test_retrieval_eval.py \
  docs/CAPSTONE_UPGRADE_REPORT.md \
  docs/MAINTAINER_MIGRATION_PLAN.md

git diff --cached --check
git commit -m "docs: add maintainer migration and capstone integration plan"
git push origin justin-implementation
```

### B. Create a dedicated core-integration branch

```bash
cd /Users/justin/Downloads/precision-oncology-data-architect-assistant
git fetch origin
git switch -c integrate/core-library origin/main
```

Copy only the direct-copy files:

```bash
SOURCE=/Users/justin/Documents/precision-oncology-data-architect-assistant

mkdir -p src
cp "$SOURCE/src/chunker.py" src/chunker.py
cp "$SOURCE/src/prompts.py" src/prompts.py
cp "$SOURCE/src/llm_client.py" src/llm_client.py

git add src/chunker.py src/prompts.py src/llm_client.py
git diff --cached --check
git commit -m "feat: import chunking prompts and LLM provider core"
```

Then import and fix merge files in small commits:

```bash
cp "$SOURCE/src/models.py" src/models.py
cp "$SOURCE/src/config.py" src/config.py
# Fix timestamp, scoring, and import-time side effects.
git add src/models.py src/config.py
git commit -m "feat: add validated domain models and configuration"

cp "$SOURCE/src/embeddings.py" src/embeddings.py
cp "$SOURCE/src/vector_store.py" src/vector_store.py
cp "$SOURCE/src/retriever.py" src/retriever.py
# Fix provider names, filter contract, score semantics, and upsert behavior.
git add src/embeddings.py src/vector_store.py src/retriever.py
git commit -m "feat: add consistent embedding and retrieval providers"

cp "$SOURCE/src/fhir_parser.py" src/fhir_parser.py
cp "$SOURCE/src/ingestion.py" src/ingestion.py
# Apply redaction policy and idempotent ingestion changes.
git add src/fhir_parser.py src/ingestion.py
git commit -m "feat: add privacy-aware FHIR ingestion pipeline"
```

Do not stage fixtures until the synthetic-data review is complete.

### C. Inspect exactly what will enter a PR

```bash
git fetch origin
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
git log --oneline origin/main..HEAD
python -m pytest -q
```

## Pull request strategy

### PR 1 — Maintainer baseline

**Branch:** `justin-implementation`  
**Contents:** truthful README, requirements cleanup, Docker skeleton,
deterministic retrieval evaluator, capstone and migration documentation.

Do not claim the container is runnable yet. Mark the PR as documentation and
build preparation.

### PR 2 — Core parsing and domain model

**Branch:** `integrate/core-models`  
**Contents:** models, configuration, FHIR parser, chunker, prompt manager,
sanitized fixtures, and unit tests.

Merge only after privacy review and deterministic parser/chunker tests pass.

### PR 3 — Retrieval and ingestion

**Branch:** `integrate/retrieval`  
**Contents:** embeddings, Chroma adapter, retriever, ingestion service and CLI,
stable IDs, idempotent upserts, and retrieval baseline.

Require Recall@5/MRR report and a repeated-ingestion test.

### PR 4 — RAG application

**Branch:** `integrate/rag-app`  
**Contents:** RAG orchestration, citations, abstention, FastAPI, Streamlit,
prompt-injection tests, and answer evaluation.

Require citation correctness and unsupported-answer tests.

### PR 5 — Monitoring and deployment

**Branch:** `integrate/operations`  
**Contents:** trace IDs, structured telemetry, feedback, completed Docker
health checks, CI build, deployment runbook, and demo.

Each PR should target `main`, remain independently reviewable, and avoid a
single giant “copy completed app” change. The local source tree should remain
untouched as evidence until its contents are committed through reviewed PRs.

# Capstone Rubric Scorecard

This file maps the project to the LLM Zoomcamp capstone rubric so reviewers can
find the relevant evidence quickly.

## Core Criteria

| Criterion | Expected score | Evidence |
|---|---:|---|
| Problem description | 2 | `README.md` describes the oncology/genomics data-architecture problem, target users, scope, and non-goals. |
| Retrieval flow | 2 | `README.md`, `docs/architecture.md`, `src/retrieval/search.py`, and `src/rag/pipeline.py` show knowledge-base retrieval followed by optional LLM answer generation. |
| Retrieval evaluation | 2 | `evaluation/retrieval_eval.py` evaluates `baseline` and `expanded` strategies with `recall_at_k`, `mean_reciprocal_rank`, and `ndcg_at_k`; `src/retrieval/search.py` uses `expanded` by default. |
| LLM evaluation | 2 | `evaluation/llm_eval.py` supports generated-answer evaluation, `--compare-modes`, LLM-as-judge scoring, and `--compare-prompts` across multiple prompt variants; `src/rag/pipeline.py` sets `strict_grounded` as the active default. |
| Interface | 2 | `app/streamlit_app.py` provides a Streamlit UI and `app/api.py` provides FastAPI endpoints. |
| Ingestion pipeline | 2 | `src/ingestion/download_sources.py`, `src/ingestion/ingest_documents.py`, and `ingestion/index_to_vectordb.py` automate source download, chunking, and indexing. |
| Monitoring | 2 | `app/streamlit_app.py` collects user feedback through buttons; `monitoring/dashboard.py` exposes six reviewer-visible charts. |
| Containerization | 2 | `docker-compose.yml` starts API, UI, and monitoring dashboard services; `Dockerfile` builds the app image. |
| Reproducibility | 2 | `README.md` and `docs/REVIEWER_EVALUATION_GUIDE.md` provide setup/run/evaluation commands; `requirements.txt` pins dependency versions; `data/source_manifest.yaml` points to public data sources. |

Expected core score: 18 / 18.

## Best Practices

| Item | Expected score | Evidence |
|---|---:|---|
| Hybrid search | 0 | The active runtime uses lexical Minsearch. The legacy Chroma/vector path is retained for reference, but it is not part of the active app. |
| Document re-ranking | 1 | `src/retrieval/search.py` applies source-name boosting and collection diversification after over-retrieval in the `expanded` strategy. |
| User query rewriting | 1 | `src/retrieval/search.py` expands domain-specific query terms such as NSCLC, PD-L1, biomarker, molecular report, and tumor staging. |

Expected best-practice score: 2 / 3.

## Evaluation Commands

Retrieval strategy comparison:

```bash
mkdir -p artifacts
python evaluation/retrieval_eval.py \
  --questions evaluation/ground_truth.csv \
  --output artifacts/retrieval_strategy_comparison.json \
  --k 5 \
  --compare-strategies
```

Generated-answer prompt comparison:

```bash
python evaluation/llm_eval.py \
  --use-llm \
  --compare-prompts \
  --out artifacts/llm_prompt_comparison.json \
  --limit 5
```

Offline answer smoke evaluation:

```bash
python evaluation/llm_eval.py --out artifacts/llm_eval_results.json --limit 5
```

Monitoring dashboard:

```bash
streamlit run monitoring/dashboard.py --server.port 8502
```

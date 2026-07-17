# Evaluation framework

The project separates retrieval evaluation from generated-answer evaluation.

## Retrieval evaluation from CSV

The tracked `evaluation/ground_truth.csv` file contains review questions,
expected answer notes, expected source collections, and categories. Run live
retrieval against the local Minsearch index with:

```bash
mkdir -p artifacts
python evaluation/retrieval_eval.py \
  --questions evaluation/ground_truth.csv \
  --output artifacts/retrieval_metrics.json \
  --k 5
```

This reports Recall@k, mean reciprocal rank, and nDCG@k overall and by
category. Relevance is measured at the source-collection level using
`expected_sources`, for example `mcode|fhir`. Rows whose expected source labels
are not indexed collections, such as `project_scope`, are listed as excluded
records and should be reviewed through answer/safety evaluation instead.

## Optional chunk-level JSONL evaluation

For stricter manual review, each JSONL question can contain exact chunk IDs:

```json
{
  "id": "BIO-001",
  "category": "biomarker",
  "question": "Which EGFR alteration is reported?",
  "relevant_chunk_ids": ["bundle-001-observation-egfr-c000"]
}
```

Each retrieval result must contain:

```json
{
  "id": "BIO-001",
  "retrieved_chunk_ids": [
    "bundle-001-observation-egfr-c000",
    "bundle-001-summary-c000"
  ]
}
```

Run:

```bash
python -m evaluation.retrieval_eval \
  --questions data/evaluation/questions.jsonl \
  --results artifacts/retrieval_results.jsonl \
  --output artifacts/retrieval_metrics.json \
  --k 5
```

## Answer evaluation

The default smoke test uses keyword overlap between expected answer notes and
retrieved context, so it can run without network access or provider keys:

```bash
python evaluation/llm_eval.py --limit 5
```

With a configured provider key, generated-answer evaluation can call the active
LLM provider:

```bash
python evaluation/llm_eval.py --use-llm --limit 5
```

With an OpenAI key, an LLM judge can supplement those checks:

```bash
python evaluation/llm_eval.py --use-llm --judge --limit 5
```

# Evaluation framework

The project separates retrieval evaluation from generated-answer evaluation.

## Retrieval ground truth

Each JSONL question must contain:

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

The evaluator reports Recall@k, mean reciprocal rank, and nDCG@k overall and
by category.

## Answer evaluation to add

The RAG phase should add deterministic checks for:

- required fact coverage;
- forbidden or unsupported claims;
- citation correctness and completeness;
- correct abstention;
- unsupported clinical recommendations.

LLM-as-judge can supplement those checks, but it must be versioned and
calibrated against a human-reviewed sample.

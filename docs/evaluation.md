# Evaluation Plan

This project includes two evaluation layers.

## 1. Retrieval Evaluation

Script:

```bash
mkdir -p artifacts
python evaluation/retrieval_eval.py \
  --questions evaluation/ground_truth.csv \
  --output artifacts/retrieval_metrics.json \
  --k 5
```

Metrics:

- `recall_at_k`: fraction of expected source collections found in top-k results
- `mean_reciprocal_rank`: reciprocal rank of the first expected source collection
- `ndcg_at_k`: ranking quality for expected source collections
- `excluded_records`: rows reserved for answer/safety evaluation because their
  expected labels are not indexed source collections

Input:

- `evaluation/ground_truth.csv`

Output:

- `artifacts/retrieval_metrics.json`

## 2. Answer Evaluation

Script:

```bash
python evaluation/llm_eval.py --limit 5
```

Default mode uses a simple keyword-overlap heuristic against retrieved context,
so it can run without network access or provider keys.
With a configured provider key, generated answers can be evaluated:

```bash
python evaluation/llm_eval.py --use-llm --limit 5
```

With an OpenAI key, an LLM judge can be used:

```bash
python evaluation/llm_eval.py --use-llm --judge --limit 5
```

Output:

- `evaluation/llm_eval_results.json`

## Evaluation Questions

The initial evaluation set focuses on:

- diagnosis modeling
- genomic variant modeling
- molecular report representation
- profile selection
- resource relationships
- scope safety

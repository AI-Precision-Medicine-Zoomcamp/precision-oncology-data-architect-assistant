# Evaluation Plan

This project includes two evaluation layers.

## 1. Retrieval Evaluation

Script:

```bash
python evaluation/retrieval_eval.py --k 5
```

Metrics:

- `hit_rate@k`: whether an expected source collection appears in top-k results
- `mrr@k`: reciprocal rank of the first expected source collection

Input:

- `evaluation/ground_truth.csv`

Output:

- `evaluation/retrieval_results.json`

## 2. Answer Evaluation

Script:

```bash
python evaluation/llm_eval.py --limit 5
```

Default mode uses a simple keyword-overlap heuristic. With an OpenAI key, an LLM judge can be used:

```bash
python evaluation/llm_eval.py --judge --limit 5
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

from evaluation.llm_eval import compare_prompt_variants, evaluate_rows
from src.rag.pipeline import DEFAULT_PROMPT_VARIANT, PROMPT_VARIANTS


def test_evaluate_rows_records_prompt_variant(monkeypatch) -> None:
    rows = [
        {
            "id": "q1",
            "question": "How should EGFR be modeled?",
            "expected_answer": "EGFR should be represented as an Observation.",
        }
    ]

    def fake_run_assistant(question, use_llm, prompt_variant):
        return {
            "answer": "EGFR should be represented as an Observation.",
            "contexts": [{"content": "EGFR should be represented as an Observation."}],
            "sources": [],
            "prompt_variant": prompt_variant,
        }

    monkeypatch.setattr("evaluation.llm_eval.run_assistant", fake_run_assistant)

    report = evaluate_rows(
        rows,
        use_llm=True,
        judge=False,
        judge_model="unused",
        prompt_variant="concise",
    )

    assert report["prompt_variant"] == "concise"
    assert report["results"][0]["score"]["score"] > 0


def test_compare_prompt_variants_selects_highest_score(monkeypatch) -> None:
    rows = [
        {
            "id": "q1",
            "question": "How should EGFR be modeled?",
            "expected_answer": "EGFR Observation specimen report",
        }
    ]

    def fake_evaluate_rows(rows, use_llm, judge, judge_model, prompt_variant):
        scores = {
            "concise": 0.25,
            "implementation_steps": 0.75,
            DEFAULT_PROMPT_VARIANT: 0.5,
        }
        return {
            "average_score": scores[prompt_variant],
            "prompt_variant": prompt_variant,
            "results": [],
        }

    monkeypatch.setattr("evaluation.llm_eval.evaluate_rows", fake_evaluate_rows)

    report = compare_prompt_variants(
        rows,
        use_llm=True,
        judge=False,
        judge_model="unused",
        variants=sorted(PROMPT_VARIANTS),
    )

    assert report["best_prompt_variant"] == "implementation_steps"
    assert report["active_default_prompt_variant"] == DEFAULT_PROMPT_VARIANT

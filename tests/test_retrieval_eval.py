from evaluation.retrieval_eval import (
    EvaluationRecord,
    build_report,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k_uses_all_relevant_chunks() -> None:
    assert recall_at_k(["a", "b"], ["x", "a", "y"], k=3) == 0.5


def test_reciprocal_rank_uses_first_relevant_result() -> None:
    assert reciprocal_rank(["a"], ["x", "y", "a"]) == 1 / 3


def test_ndcg_rewards_earlier_relevant_results() -> None:
    early = ndcg_at_k(["a"], ["a", "x"], k=2)
    late = ndcg_at_k(["a"], ["x", "a"], k=2)
    assert early > late


def test_report_contains_category_slices() -> None:
    records = [
        EvaluationRecord("q1", "biomarker", ("a",), ("a", "x")),
        EvaluationRecord("q2", "staging", ("b",), ("x", "b")),
    ]
    report = build_report(records, k=2)

    assert report["overall"]["count"] == 2
    assert set(report["by_category"]) == {"biomarker", "staging"}

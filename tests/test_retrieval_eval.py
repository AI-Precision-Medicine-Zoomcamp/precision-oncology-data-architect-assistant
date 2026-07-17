from evaluation.retrieval_eval import (
    EvaluationRecord,
    build_report,
    build_source_report,
    ndcg_at_k,
    parse_expected_sources,
    recall_at_k,
    reciprocal_rank,
    SourceEvaluationRecord,
    source_recall_at_k,
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


def test_parse_expected_sources_handles_pipe_separated_labels() -> None:
    assert parse_expected_sources("mcode| FHIR |") == ("mcode", "fhir_r4_core")


def test_source_recall_at_k_matches_expected_collections() -> None:
    assert source_recall_at_k(["mcode", "fhir"], ["genomics", "mcode"], k=2) == 0.5


def test_source_report_includes_records_for_review() -> None:
    records = [
        SourceEvaluationRecord("q1", "profile", ("mcode",), ("fhir", "mcode"), ("c1", "c2")),
    ]
    report = build_source_report(records, k=2)

    assert report["relevance_granularity"] == "source_collection"
    assert report["records"][0]["retrieved_chunk_ids"] == ("c1", "c2")


def test_source_report_excludes_non_indexed_source_labels() -> None:
    records = [
        SourceEvaluationRecord("q1", "safety", ("project_scope",), ("mcode",), ("c1",)),
    ]
    report = build_source_report(records, k=1)

    assert report["overall"]["count"] == 0
    assert report["excluded_records"][0]["question_id"] == "q1"

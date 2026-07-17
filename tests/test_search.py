from src.retrieval import search as search_module


class FakeIndex:
    def __init__(self) -> None:
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return [{"id": "chunk-1"}]


def test_search_passes_empty_filter_dict_when_collection_is_missing(monkeypatch):
    fake_index = FakeIndex()
    monkeypatch.setattr(search_module, "load_index", lambda: fake_index)

    results = search_module.search("EGFR Exon19del", num_results=3)

    assert results == [{"id": "chunk-1"}]
    assert fake_index.calls[0]["filter_dict"] == {}


def test_search_expands_domain_shorthand_before_querying(monkeypatch):
    fake_index = FakeIndex()
    monkeypatch.setattr(search_module, "load_index", lambda: fake_index)

    search_module.search("How should NSCLC be represented?", num_results=3)

    assert "primary cancer condition" in fake_index.calls[0]["query"].lower()


def test_baseline_strategy_does_not_expand_query(monkeypatch):
    fake_index = FakeIndex()
    monkeypatch.setattr(search_module, "load_index", lambda: fake_index)

    search_module.search("How should NSCLC be represented?", num_results=3, strategy="baseline")

    assert fake_index.calls[0]["query"] == "How should NSCLC be represented?"


def test_search_passes_collection_filter_when_collection_is_provided(monkeypatch):
    fake_index = FakeIndex()
    monkeypatch.setattr(search_module, "load_index", lambda: fake_index)

    search_module.search("EGFR Exon19del", num_results=3, collection="mcode")

    assert fake_index.calls[0]["filter_dict"] == {"collection": "mcode"}


def test_search_rejects_unknown_strategy(monkeypatch):
    fake_index = FakeIndex()
    monkeypatch.setattr(search_module, "load_index", lambda: fake_index)

    try:
        search_module.search("EGFR", strategy="unknown")
    except ValueError as exc:
        assert "strategy" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_diversify_by_collection_prefers_distinct_collections_first():
    results = [
        {"id": "a", "collection": "mcode"},
        {"id": "b", "collection": "mcode"},
        {"id": "c", "collection": "fhir_r4_core"},
        {"id": "d", "collection": "genomics_reporting"},
    ]

    diversified = search_module.diversify_by_collection(results, num_results=3)

    assert [r["id"] for r in diversified] == ["a", "c", "d"]

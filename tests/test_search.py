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


def test_search_passes_collection_filter_when_collection_is_provided(monkeypatch):
    fake_index = FakeIndex()
    monkeypatch.setattr(search_module, "load_index", lambda: fake_index)

    search_module.search("EGFR Exon19del", num_results=3, collection="mcode")

    assert fake_index.calls[0]["filter_dict"] == {"collection": "mcode"}

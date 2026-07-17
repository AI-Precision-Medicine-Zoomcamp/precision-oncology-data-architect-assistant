from fastapi.testclient import TestClient

from app import api


def test_health_endpoint_reports_ok():
    client = TestClient(api.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_endpoint_returns_retrieved_context(monkeypatch):
    monkeypatch.setattr(
        api,
        "retrieve_context",
        lambda query, num_results: [{"id": "chunk-1", "content": query}],
    )
    client = TestClient(api.app)

    response = client.post("/search", json={"query": "EGFR", "num_results": 1})

    assert response.status_code == 200
    assert response.json()["results"] == [{"id": "chunk-1", "content": "EGFR"}]


def test_answer_endpoint_uses_service_layer(monkeypatch):
    monkeypatch.setattr(
        api,
        "run_assistant",
        lambda query, num_results, use_llm: {
            "answer": f"answer for {query}",
            "sources": [],
        },
    )
    client = TestClient(api.app)

    response = client.post("/answer", json={"query": "mCODE", "use_llm": False})

    assert response.status_code == 200
    assert response.json()["answer"] == "answer for mCODE"

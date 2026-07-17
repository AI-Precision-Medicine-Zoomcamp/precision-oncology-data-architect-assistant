from src.api import service
from src.api.service import run_assistant, retrieve_context


def test_service_functions_exist():
    assert callable(run_assistant)
    assert callable(retrieve_context)


def test_run_assistant_auto_enables_configured_provider(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "get_llm_provider", lambda: "groq")
    monkeypatch.setattr(service, "has_llm_key", lambda provider: provider == "groq")
    monkeypatch.setattr(
        service,
        "answer_question",
        lambda query, num_results: calls.append((query, num_results)) or {"answer": "llm"},
    )

    result = service.run_assistant("EGFR", num_results=3, use_llm=None)

    assert result["answer"] == "llm"
    assert calls == [("EGFR", 3)]

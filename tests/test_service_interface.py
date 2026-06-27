from src.api.service import run_assistant, retrieve_context


def test_service_functions_exist():
    assert callable(run_assistant)
    assert callable(retrieve_context)

# Zoomcamp Requirement Coverage

| Requirement | Implementation |
|---|---|
| Dataset / Knowledge Base | `data/source_manifest.yaml`, downloaded public docs |
| Automated ingestion | `src/ingestion/download_sources.py`, `src/ingestion/ingest_documents.py` |
| Chunking | `src/ingestion/ingest_documents.py` |
| Retrieval | `src/retrieval/build_index.py`, `src/retrieval/search.py` |
| LLM integration | `src/rag/pipeline.py` |
| User interface | `app/streamlit_app.py` |
| Evaluation dataset | `evaluation/ground_truth.csv`, `evaluation/questions.csv` |
| Retrieval evaluation | `evaluation/retrieval_eval.py` |
| LLM evaluation | `evaluation/llm_eval.py` |
| Monitoring / feedback | `monitoring/telemetry.py`, Streamlit feedback buttons |
| Docker | `Dockerfile`, `docker-compose.yml` |
| Documentation | `README.md`, `docs/` |
| ClawBio-compatible interface | `src/api/service.py` |

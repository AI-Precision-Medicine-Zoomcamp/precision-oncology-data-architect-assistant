from src.ingestion.ingest_documents import chunk_text


def test_chunk_text_basic():
    chunks = chunk_text("A" * 4000, size=1000, overlap=100)
    assert len(chunks) >= 4
    assert all("content" in c for c in chunks)

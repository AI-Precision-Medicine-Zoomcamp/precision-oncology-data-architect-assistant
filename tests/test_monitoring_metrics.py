from pathlib import Path

from monitoring.metrics import load_events, summarize


def test_monitoring_summary_includes_five_dashboard_metrics(tmp_path: Path) -> None:
    log = tmp_path / "queries.jsonl"
    log.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-07-17T10:00:00Z","event_type":"query","query":"q","answer_preview":"short","provider":"groq","sources":[{"collection":"mcode"},{"collection":"fhir_r4_core"}]}',
                '{"timestamp":"2026-07-17T10:01:00Z","event_type":"feedback","query":"q","rating":"helpful"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = summarize(load_events(log))

    assert summary["event_types"]["query"] == 1
    assert summary["feedback"]["helpful"] == 1
    assert summary["source_collections"]["mcode"] == 1
    assert summary["query_volume_by_day"]["2026-07-17"] == 1
    assert summary["provider_usage"]["groq"] == 1
    assert summary["answer_length_buckets"]["0-200"] == 1

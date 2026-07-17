# Monitoring and Feedback

The app includes simple local monitoring for Zoomcamp requirements.

Events are written to:

```text
logs/queries.jsonl
```

Logged fields include:

- timestamp
- query
- answer preview
- retrieved sources
- usage metadata, when available
- feedback events

Streamlit feedback buttons record:

- `helpful`
- `needs_improvement`

This is intentionally lightweight and suitable for local development and course demonstration.

## Dashboard

Run the local dashboard:

```bash
streamlit run monitoring/dashboard.py --server.port 8502
```

The dashboard reads `logs/queries.jsonl` and displays:

- query volume by day
- event type counts
- feedback ratings
- retrieved source collection counts
- provider usage
- answer preview length buckets

Docker Compose exposes the same dashboard at `http://localhost:8502`.

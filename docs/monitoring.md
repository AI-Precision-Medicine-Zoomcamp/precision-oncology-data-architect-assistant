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

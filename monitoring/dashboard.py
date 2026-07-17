"""Streamlit monitoring dashboard for local Zoomcamp telemetry."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from monitoring.metrics import DEFAULT_LOG_PATH, load_events, summarize


def chart_frame(values: dict[str, int], key_name: str, value_name: str) -> pd.DataFrame:
    if not values:
        return pd.DataFrame({key_name: [], value_name: []})
    return pd.DataFrame(
        [{key_name: key, value_name: value} for key, value in values.items()]
    ).set_index(key_name)


st.set_page_config(page_title="Precision Oncology Monitoring", layout="wide")
st.title("Precision Oncology Monitoring")

log_path = Path(st.sidebar.text_input("Telemetry log path", str(DEFAULT_LOG_PATH)))
events = load_events(log_path)
summary = summarize(events)

st.metric("Total events", summary["total_events"])
st.metric("Queries", summary["event_types"].get("query", 0))
st.metric("Feedback events", sum(summary["feedback"].values()))

if not events:
    st.info("No telemetry events found yet. Run the assistant and submit feedback.")
    st.stop()

left, right = st.columns(2)

with left:
    st.subheader("1. Query Volume by Day")
    st.bar_chart(chart_frame(summary["query_volume_by_day"], "day", "queries"))

    st.subheader("2. Event Types")
    st.bar_chart(chart_frame(summary["event_types"], "event_type", "events"))

    st.subheader("3. Feedback Ratings")
    st.bar_chart(chart_frame(summary["feedback"], "rating", "count"))

with right:
    st.subheader("4. Retrieved Source Collections")
    st.bar_chart(chart_frame(summary["source_collections"], "collection", "count"))

    st.subheader("5. Provider Usage")
    st.bar_chart(chart_frame(summary["provider_usage"], "provider", "queries"))

    st.subheader("6. Answer Preview Length")
    st.bar_chart(chart_frame(summary["answer_length_buckets"], "bucket", "answers"))

st.subheader("Recent Events")
st.dataframe(pd.DataFrame(events).tail(25), use_container_width=True)

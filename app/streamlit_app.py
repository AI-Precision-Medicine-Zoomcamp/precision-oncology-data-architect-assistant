from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from dotenv import load_dotenv

from monitoring.telemetry import log_feedback
from src.api.service import run_assistant
from src.retrieval.search import search

load_dotenv(override=True)

st.set_page_config(page_title="Precision Oncology Data Architect Assistant", layout="wide")
st.title("Precision Oncology Data Architect Assistant")
st.caption("FHIR R4 • US Core • mCODE • Genomics Reporting")

st.markdown(
    """
Ask data modeling questions about how oncology and genomics data should be represented using
FHIR, US Core, mCODE, and Genomics Reporting. This app is for data architecture guidance only,
not clinical decision support.
"""
)

sample_questions = [
    "How should NSCLC be represented in mCODE?",
    "How should EGFR Exon19del be modeled using FHIR Genomics Reporting?",
    "Which mCODE profiles are needed for a primary cancer condition?",
    "How should a molecular diagnostic report be structured in FHIR?",
    "Which FHIR resources are used for genomic findings?",
    "How should tumor marker results be represented?",
    "How should a specimen be linked to a genomic observation?",
    "What is the relationship between DiagnosticReport and Observation?",
    "How do US Core profiles constrain FHIR resources?",
    "How do mCODE and Genomics Reporting work together?",
    "How should lung adenocarcinoma be represented using mCODE?",
    "Which resource should represent a genomic variant observation?",
    "How should a biomarker test result be represented in FHIR?",
    "How should cancer staging be modeled in mCODE?",
    "What FHIR resources are commonly included in an oncology diagnostic bundle?",
]

selected_question = st.selectbox(
    "Try an example question",
    [""] + sample_questions,
)

default_question = selected_question or "How should EGFR Exon19del be represented in mCODE?"

query = st.text_area(
    "Ask a data modeling question",
    value=default_question,
    height=100,
)

num_results = st.slider("Number of retrieved chunks", 3, 10, 5)
mode = st.radio("Mode", ["RAG answer", "Search only"], horizontal=True)

llm_provider = os.getenv("LLM_PROVIDER", "groq").lower()

has_llm_key = False
if llm_provider == "groq":
    has_llm_key = bool(os.getenv("GROQ_API_KEY"))
elif llm_provider == "openrouter":
    has_llm_key = bool(os.getenv("OPENROUTER_API_KEY"))
elif llm_provider == "openai":
    has_llm_key = bool(os.getenv("OPENAI_API_KEY"))

st.sidebar.header("Configuration")
st.sidebar.write(f"LLM Provider: `{llm_provider}`")
st.sidebar.write(f"LLM Key Configured: `{has_llm_key}`")

if llm_provider == "groq":
    st.sidebar.write(f"Model: `{os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')}`")
elif llm_provider == "openrouter":
    st.sidebar.write(f"Model: `{os.getenv('OPENROUTER_MODEL', 'not set')}`")
elif llm_provider == "openai":
    st.sidebar.write(f"Model: `{os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}`")

if mode == "RAG answer" and not has_llm_key:
    st.warning(
        f"LLM_PROVIDER is set to `{llm_provider}`, but the required API key is not configured. "
        "The app will show retrieved context only."
    )

if st.button("Run"):
    if not query.strip():
        st.warning("Please enter a question.")
        st.stop()

    if mode == "Search only":
        results = search(query, num_results=num_results)
        st.subheader("Retrieved Context")
        for i, r in enumerate(results, start=1):
            with st.expander(f"{i}. {r.get('source_name')} ({r.get('collection')})"):
                st.write(r.get("content", "")[:2500])
                if r.get("source_url"):
                    st.link_button("Open source", r["source_url"])
    else:
        result = run_assistant(query, num_results=num_results, use_llm=has_llm_key)

        st.subheader("Answer")
        st.write(result.get("answer"))

        st.caption(
            f"Provider: {result.get('provider') or llm_provider} | "
            f"Model: {result.get('model') or 'N/A'}"
        )

        if "contexts" in result:
            st.subheader("Retrieved Context")
            for i, r in enumerate(result["contexts"], start=1):
                with st.expander(f"{i}. {r.get('source_name')} ({r.get('collection')})"):
                    st.write(r.get("content", "")[:2500])
                    if r.get("source_url"):
                        st.link_button("Open source", r["source_url"])

        st.subheader("Sources")
        for s in result.get("sources", []):
            st.markdown(
                f"- **{s.get('name')}** ({s.get('collection')}) — {s.get('url') or 'local'}"
            )

        st.subheader("Feedback")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Helpful"):
                log_feedback(query, "helpful")
                st.success("Feedback saved.")
        with col2:
            if st.button("👎 Needs improvement"):
                log_feedback(query, "needs_improvement")
                st.info("Feedback saved.")

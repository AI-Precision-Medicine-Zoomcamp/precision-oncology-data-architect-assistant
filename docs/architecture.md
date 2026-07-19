# Project Architecture

## Architectural Overview

The Precision Oncology Data Architect Assistant is a retrieval-augmented generation
(RAG) application for questions about FHIR R4, US Core, mCODE, and the Genomics
Reporting Implementation Guide.

The active application uses a lightweight lexical retrieval pipeline:

1. A YAML manifest identifies canonical public standards pages.
2. The ingestion commands download and clean those pages.
3. Clean text is split into overlapping chunks and stored as JSON Lines.
4. A Minsearch index is built and serialized to disk.
5. The FastAPI endpoint, Streamlit UI, or service interface retrieves relevant chunks.
6. The RAG pipeline sends the question and retrieved context to the configured LLM.
7. Query metadata and user feedback are appended to a local JSONL telemetry log.

The repository also contains a legacy/experimental semantic retrieval path for FHIR
JSON bundles. It parses bundles into typed models, creates embeddings, and stores
them in ChromaDB. That path is not called by the current FastAPI, Streamlit, or
service workflow.

## 1. Project Architecture Diagram

```mermaid
flowchart TB
    User[User or external caller]

    subgraph Interfaces
        UI[Streamlit UI<br/>app/streamlit_app.py]
        API[FastAPI API<br/>app/api.py]
        Service[Stable Python service<br/>src/api/service.py]
        SearchCLI[Search CLI]
        Eval[Evaluation scripts]
    end

    subgraph Active["Active RAG runtime"]
        RAG[RAG orchestration<br/>src/rag/pipeline.py]
        Search[Minsearch adapter<br/>src/retrieval/search.py]
        Index[(Serialized Minsearch index<br/>data/indexes/minsearch_index.pkl)]
        Provider{Configured LLM provider}
        Groq[Groq API]
        OpenRouter[OpenRouter API]
        OpenAI[OpenAI API]
        Telemetry[Telemetry logger<br/>monitoring/telemetry.py]
        Logs[(Query and feedback log<br/>logs/queries.jsonl)]
    end

    subgraph Ingestion["Active documentation ingestion"]
        Manifest[data/source_manifest.yaml]
        Downloader[Download and clean HTML<br/>src/ingestion/download_sources.py]
        Raw[(Raw HTML, text, metadata<br/>data/raw/)]
        Chunker[Chunk documents<br/>src/ingestion/ingest_documents.py]
        Chunks[(Processed chunks<br/>data/processed/chunks.jsonl)]
        Builder[Build lexical index<br/>src/retrieval/build_index.py]
    end

    subgraph Legacy["Legacy / experimental semantic path"]
        Bundles[(FHIR JSON bundles<br/>data/fhir_examples/)]
        Parser[FHIR bundle parser]
        LegacyChunker[Typed document chunker]
        Embeddings[Embedding provider]
        Chroma[(ChromaDB vector store)]
        LegacyRetriever[Semantic retriever]
    end

    Standards[HL7 standards websites]

    User --> UI
    User --> API
    User --> Service
    UI --> Service
    API --> Service
    UI --> Search
    Service --> RAG
    Service --> Search
    SearchCLI --> Search
    Eval --> Search
    Eval --> RAG

    RAG --> Search
    Search --> Index
    RAG --> Provider
    Provider --> Groq
    Provider --> OpenRouter
    Provider --> OpenAI
    RAG --> Telemetry
    UI --> Telemetry
    Telemetry --> Logs

    Manifest --> Downloader
    Standards --> Downloader
    Downloader --> Raw
    Raw --> Chunker
    Chunker --> Chunks
    Chunks --> Builder
    Builder --> Index

    Bundles --> Parser
    Parser --> LegacyChunker
    LegacyChunker --> Embeddings
    Embeddings --> Chroma
    LegacyRetriever --> Embeddings
    LegacyRetriever --> Chroma

    classDef active fill:#dff4ff,stroke:#1677a3,color:#111;
    classDef storage fill:#fff3cd,stroke:#9a7500,color:#111;
    classDef legacy fill:#f1e8ff,stroke:#7253a3,color:#111;
    class UI,API,Service,SearchCLI,Eval,RAG,Search,Provider,Groq,OpenRouter,OpenAI,Telemetry,Manifest,Downloader,Chunker,Builder active;
    class Index,Logs,Raw,Chunks,Bundles,Chroma storage;
    class Parser,LegacyChunker,Embeddings,LegacyRetriever legacy;
```

## 2. Module Dependency Diagram

Solid arrows below represent Python imports or direct calls in the current
application. The legacy branch is isolated from the active runtime.

```mermaid
flowchart LR
    Streamlit[app.streamlit_app]
    API[app.api]
    Service[src.api.service]
    RAG[src.rag.pipeline]
    Search[src.retrieval.search]
    Telemetry[monitoring.telemetry]
    Build[src.retrieval.build_index]
    Download[src.ingestion.download_sources]
    Ingest[src.ingestion.ingest_documents]
    RetEval[evaluation.retrieval_eval]
    LLMEval[evaluation.llm_eval]

    LegacyIngest[src.ingestion_legacy]
    Parser[src.fhir_parser]
    DocChunker[src.chunker]
    Models[src.models]
    Embed[src.embeddings]
    Store[src.vector_store]
    Retriever[src.retriever]
    Config[src.config]
    PromptManager[src.prompts]
    LLMClient[src.llm_client]

    Streamlit --> Service
    Streamlit --> Search
    Streamlit --> Telemetry
    API --> Service
    Service --> RAG
    Service --> Search
    RAG --> Search
    RAG --> Telemetry
    RetEval --> Search
    LLMEval --> RAG

    Build --> Minsearch[minsearch]
    Search --> Minsearch
    Download --> Requests[requests]
    Download --> BS4[BeautifulSoup]
    Download --> YAML[PyYAML]

    LegacyIngest --> Parser
    LegacyIngest --> DocChunker
    LegacyIngest --> Embed
    LegacyIngest --> Store
    LegacyIngest --> Models
    LegacyIngest --> Config
    Parser --> Models
    DocChunker --> Models
    Embed --> Config
    Store --> Config
    Store --> Models
    Retriever --> Embed
    Retriever --> Store
    Retriever --> Models
    Retriever --> Config
    PromptManager --> Config
    LLMClient --> Config

    subgraph Current["Current application modules"]
        Streamlit
        API
        Service
        RAG
        Search
        Telemetry
        RetEval
        LLMEval
    end

    subgraph Offline["Offline build modules"]
        Download
        Ingest
        Build
    end

    subgraph Experimental["Legacy / experimental modules"]
        LegacyIngest
        Parser
        DocChunker
        Models
        Embed
        Store
        Retriever
        Config
        PromptManager
        LLMClient
    end
```

## 3. Data Flow Diagram

```mermaid
flowchart LR
    subgraph BuildTime["Offline knowledge-base build"]
        A[Canonical source URLs<br/>source_manifest.yaml]
        B[HTTP download]
        C[Raw HTML]
        D[Clean plain text]
        E[Source metadata and checksums]
        F[Overlapping text chunks]
        G[JSONL chunk records]
        H[Minsearch fit]
        I[(Pickled search index)]

        A --> B
        B --> C
        C --> D
        B --> E
        D --> F
        E --> G
        F --> G
        G --> H
        H --> I
    end

    subgraph QueryTime["Runtime query flow"]
        Q[User question]
        Mode{Selected mode}
        Load[Load pickled index]
        Retrieve[Weighted lexical search<br/>source_name 1.5, content 1.0]
        Context[Top-k context chunks and source metadata]
        Key{LLM key available?}
        Prompt[System prompt + context + question]
        Generate[Provider LLM generation]
        Fallback[Context-only fallback]
        Result[Answer, contexts, sources,<br/>provider, model, usage]
        Display[Streamlit rendering or service response]
        QueryLog[(Query telemetry)]
        Feedback[Helpful / needs improvement]
        FeedbackLog[(Feedback telemetry)]

        Q --> Mode
        Mode -->|Search only| Load
        Mode -->|RAG answer| Load
        I --> Load
        Load --> Retrieve
        Q --> Retrieve
        Retrieve --> Context
        Context -->|Search only| Display
        Context --> Key
        Key -->|Yes| Prompt
        Q --> Prompt
        Prompt --> Generate
        Generate --> Result
        Key -->|No or generation error| Fallback
        Context --> Fallback
        Fallback --> Result
        Result --> Display
        Generate --> QueryLog
        Display --> Feedback
        Feedback --> FeedbackLog
    end
```

### Principal data contracts

| Artifact | Format | Producer | Consumer |
|---|---|---|---|
| `data/source_manifest.yaml` | YAML collections and source URLs | Maintainer | Source downloader |
| `data/raw/<collection>/*` | HTML, clean text, metadata JSON | Source downloader | Document ingestion |
| `data/processed/chunks.jsonl` | One searchable chunk per JSON line | Document ingestion | Index builder |
| `data/indexes/minsearch_index.pkl` | Pickled Minsearch index | Index builder | Runtime search |
| RAG result | Python dictionary | RAG pipeline | Service and Streamlit UI |
| `logs/queries.jsonl` | Append-only JSON events | Telemetry module | Local monitoring/review |

## 4. Folder Structure

Generated artifacts and representative data files are included because they are
part of the checked-in runtime. Cache directories and every individual downloaded
standards page are omitted for readability.

```text
.
├── app/
│   ├── __init__.py
│   ├── api.py                         # FastAPI endpoints
│   └── streamlit_app.py               # Interactive UI and feedback controls
├── data/
│   ├── evaluation_questions/
│   │   └── nsclc_questions.json
│   ├── fhir_examples/                 # Example FHIR bundles for legacy parsing
│   ├── indexes/
│   │   └── minsearch_index.pkl        # Active serialized retrieval index
│   ├── processed/
│   │   └── chunks.jsonl               # Active searchable chunk corpus
│   ├── raw/
│   │   ├── fhir_r4_core/
│   │   ├── genomics_reporting/
│   │   ├── mcode/
│   │   ├── us_core/
│   │   └── download_report.json
│   ├── sample/
│   └── source_manifest.yaml
├── docs/
│   ├── architecture.md                # Detailed architecture documentation
│   ├── clawbio_integration.md
│   ├── course_requirements.md
│   ├── data_sources.md
│   ├── evaluation.md
│   ├── monitoring.md
│   ├── REVIEWER_EVALUATION_GUIDE.md
│   └── rubric_scorecard.md
├── evaluation/
│   ├── ground_truth.csv
│   ├── llm_eval.py                    # Heuristic or LLM-as-judge evaluation
│   ├── questions.csv
│   └── retrieval_eval.py              # Recall@k, MRR, and nDCG evaluation
├── ingestion/
│   └── index_to_vectordb.py            # Compatibility entrypoint for index build
├── logs/
│   └── queries.jsonl                  # Local query and feedback events
├── monitoring/
│   └── telemetry.py
├── notebooks/                         # Reserved for analysis notebooks
├── prompts/
│   └── system_prompts.yaml            # Experimental reusable prompt templates
├── scripts/                           # Reserved for utility scripts
├── src/
│   ├── api/
│   │   └── service.py                 # Stable application-facing interface
│   ├── evaluation/                    # Thin wrappers around evaluation scripts
│   ├── ingestion/
│   │   ├── download_sources.py        # Manifest-driven downloader and cleaner
│   │   └── ingest_documents.py        # Active text chunking pipeline
│   ├── rag/
│   │   ├── pipeline.py                # Active RAG and provider routing
│   │   └── pipeline_openai_backup.py  # Earlier OpenAI-only implementation
│   ├── retrieval/
│   │   ├── build_index.py             # Active Minsearch index builder
│   │   └── search.py                  # Active runtime retrieval
│   ├── chunker.py                     # Legacy typed document chunking
│   ├── config.py                      # Legacy provider/vector settings
│   ├── embeddings.py                  # Legacy embedding abstraction
│   ├── fhir_parser.py                 # Legacy FHIR bundle parser
│   ├── ingestion_legacy.py            # Legacy semantic ingestion orchestration
│   ├── llm_client.py                  # Experimental multi-provider abstraction
│   ├── models.py                      # Pydantic domain models
│   ├── prompts.py                     # YAML prompt loader
│   ├── retriever.py                   # Legacy semantic retriever
│   └── vector_store.py                # Legacy ChromaDB abstraction
├── tests/
│   ├── test_api_connections.py
│   ├── test_chunker.py
│   ├── test_evaluation_files.py
│   ├── test_ingestion.py
│   ├── test_manifest.py
│   └── test_service_interface.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
└── requirements.txt
```

## 5. User Query Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant Service as src.api.service
    participant RAG as src.rag.pipeline
    participant Search as src.retrieval.search
    participant Index as Minsearch index
    participant LLM as Configured LLM API
    participant Log as telemetry.py

    User->>UI: Enter question, top-k, and mode
    User->>UI: Click Run

    alt Search only
        UI->>Search: search(question, top-k)
        Search->>Index: Load pickled index
        Search->>Index: Weighted lexical search
        Index-->>Search: Ranked chunks
        Search-->>UI: Context records
        UI-->>User: Display retrieved context and links
    else RAG answer
        UI->>Service: run_assistant(question, top-k, use_llm)
        alt LLM enabled
            Service->>RAG: answer_question(question, top-k)
            RAG->>Search: search(question, top-k)
            Search->>Index: Load pickled index
            Search->>Index: Weighted lexical search
            Index-->>Search: Ranked chunks
            Search-->>RAG: Context records
            RAG->>RAG: Build grounded prompt
            RAG->>LLM: Generate answer
            alt Generation succeeds
                LLM-->>RAG: Answer and usage
                RAG->>Log: Append query event
                RAG-->>Service: Answer, sources, contexts, metadata
            else Provider error
                LLM--xRAG: Error
                RAG->>Search: Retrieve context-only fallback
                Search-->>RAG: Context records
                RAG-->>Service: Error notice and contexts
            end
        else LLM disabled or key missing
            Service->>RAG: answer_without_llm(question, top-k)
            RAG->>Search: search(question, top-k)
            Search->>Index: Load and query index
            Index-->>Search: Ranked chunks
            Search-->>RAG: Context records
            RAG-->>Service: Context-only response
        end
        Service-->>UI: Result dictionary
        UI-->>User: Display answer, context, and sources
        opt User submits feedback
            User->>UI: Helpful or needs improvement
            UI->>Log: Append feedback event
        end
    end
```

## 6. README Architecture Section

The following is the concise architecture section used in the project README:

> The application uses an offline ingestion pipeline and a lightweight runtime
> RAG pipeline. Canonical FHIR R4, US Core, mCODE, and Genomics Reporting pages
> are downloaded from a manifest, converted to clean text, split into overlapping
> JSONL chunks, and indexed with Minsearch. At runtime, the FastAPI endpoint,
> Streamlit UI, and reusable Python service retrieve top-ranked chunks and
> either return them directly or pass them to the configured Groq, OpenRouter,
> or OpenAI model.
> Queries and user feedback are recorded in a local append-only JSONL log.
>
> A separate legacy/experimental path supports parsing FHIR JSON bundles,
> embedding typed chunks, and storing them in ChromaDB; it is not used by the
> current FastAPI or Streamlit runtime.

## Implementation Notes

- The active retriever is lexical Minsearch, not the ChromaDB vector store.
- The active RAG provider router supports `groq`, `openrouter`, and `openai`.
- The Streamlit UI explicitly detects keys for all three active providers.
- `run_assistant(..., use_llm=None)` auto-enables generation when the selected
  provider has its required key configured.
- Runtime search reloads the pickled index for each search call.
- Successful LLM generations are logged; context-only fallbacks are not logged
  as query events by the RAG pipeline.
- The YAML prompt manager and generic `LLMClient` abstraction belong to the
  experimental architecture and are not imported by the active RAG pipeline.
- `ingestion/index_to_vectordb.py` is kept as a compatibility entrypoint for
  the documented index-build command.

# Architecture Diagrams

All diagrams use Mermaid. Render in GitHub, VS Code, or any Mermaid viewer.

---

## 1. General layered architecture

```mermaid
flowchart TB
    subgraph Input["Perception and Input"]
        UI[Web / API / Chat]
        MM[Multimodal: text, image, audio, files]
        Doc[Document parsers]
    end

    subgraph Core["Agent Core"]
        LLM[LLM: Claude / GPT / Gemini / Groq]
        Planner[Planner: LangGraph]
        Tools[Tools via MCP or Python]
    end

    subgraph Memory["Memory and Knowledge"]
        STM[Short-term: session / checkpoint]
        LTM[Long-term: vector + optional graph]
        KB[Knowledge base / RAG]
    end

    subgraph Control["Orchestration and Safety"]
        Orch[Orchestrator: LangGraph]
        Guard[Guardrails + policy]
        Obs[Observability: Langfuse]
    end

    subgraph Learn["Feedback and Learning"]
        Eval[Eval + human feedback]
        RAGUp[RAG / prompt updates]
    end

    Input --> Core
    Core --> Memory
    Core --> Tools
    Core --> Control
    Control --> Learn
    Learn --> Memory
```

---

## 2. Research assistant stack (single agent, model routing)

```mermaid
flowchart LR
    TG[Telegram] --> API[FastAPI + Bot]
    API --> Graph[LangGraph Agent]

    Graph --> R1[Router: Groq Llama - free]
    Graph --> R2[Research: Gemini Flash - free]
    Graph --> R3[Synthesis: Gemini Pro - free]
    Graph --> R4[Embeddings: Gemini - free]

    Graph --> Tools[Tools]
    Tools --> Arxiv[arXiv API]
    Tools --> PDF[PDF download + PyMuPDF]
    Tools --> KB[RAG: pgvector]
    Tools --> Store[Save to KB]

    KB --> DB[(PostgreSQL Supabase / Docker)]
    Graph --> Mem[Session memory SQLite]
    DB --> BK[Local JSONL backup]
    PDF --> Vol[PDF Docker volume]
```

---

## 3. Typical user scenario (sequence)

```mermaid
sequenceDiagram
    participant U as User Telegram
    participant B as Bot + LangGraph
    participant A as arXiv API
    participant L as Gemini
    participant DB as Supabase pgvector
    participant BK as Local backup
    participant FS as PDF volume

    U->>B: find papers last month on MEV in web3
    B->>B: parse intent + date range + topic
    B->>A: search query + submittedDate filter
    A-->>B: papers list
    B->>DB: dedupe by arxiv_id
    loop new papers only
        B->>A: download PDF
        B->>FS: save PDF file
        B->>B: extract text + chunk
        B->>L: embed each chunk
        B->>DB: insert paper + chunks + vectors
    end
    opt paper enrichment phase
        B->>L: summarize indexed paper
        B->>DB: save summaries and tags
    end
    B->>BK: async export delta
    B-->>U: Saved N papers with summaries

    U->>B: summary on MEV
    B->>DB: semantic search + filters
    B->>L: synthesize with citations
    B-->>U: executive summary + arxiv_ids
```

---

## 4. PDF ingest pipeline

```mermaid
flowchart TD
    Q[User query] --> P[Parse topic + dates]
    P --> S[arXiv search]
    S --> D{Paper lifecycle state}
    D -->|new| DL[Download PDF]
    D -->|indexed| Skip[Skip without mutation]
    D -->|pending_text_ok_failed| Manual[Owner runs reindex]
    Manual --> DL
    DL --> FS[Local PDF storage]
    DL --> EX[Extract text PyMuPDF]
    EX --> TextOk[text_ok]
    TextOk --> CH[Chunk text]
    CH --> EM[Embed each chunk]
    EM --> DB2[(chunks + vectors)]
    DB2 --> Indexed[indexed]
    DL --> Failed[failed with safe error]
    EX --> Failed
    CH --> Failed
    EM --> Failed
    DB2 --> BK
```

---

## 5. Paper lifecycle

```mermaid
stateDiagram-v2
    [*] --> pending: metadata saved
    pending --> text_ok: text extracted
    text_ok --> indexed: chunks embedded
    pending --> failed: download or extraction failure
    text_ok --> failed: chunking or embedding failure
    failed --> pending: explicit reindex
    text_ok --> pending: explicit reindex
    pending --> pending: explicit reindex
```

`indexed` is terminal for normal search. Replacing an indexed representation needs a
future staged-index design.

---

## 6. LangGraph state machine (single agent, future phase)

```mermaid
stateDiagram-v2
    [*] --> Router
    Router --> SearchIngest: intent=find_papers
    Router --> RetrieveList: intent=list_all
    Router --> RetrieveSummary: intent=topic_summary
    Router --> Clarify: intent=unclear

    SearchIngest --> ParseQuery
    ParseQuery --> TranslateQuery
    TranslateQuery --> ArxivSearch
    ArxivSearch --> IngestPapers
    IngestPapers --> Respond

    RetrieveList --> KBFilter
    RetrieveSummary --> KBSearch
    KBSearch --> Synthesize
    KBFilter --> Respond
    Synthesize --> Respond
    Clarify --> Respond
    Respond --> [*]
```

---

## 7. Memory layers

```mermaid
flowchart TB
    subgraph Session["Short-term (per chat thread)"]
        CP[LangGraph SQLite checkpointer]
        CTX[Current research context]
    end

    subgraph KB["Long-term knowledge base"]
        PAPERS[papers metadata + summaries]
        CHUNKS[chunks + embeddings]
        PDFS[PDF files on volume]
    end

    subgraph Backup["Duplication"]
        JSONL[JSONL delta export]
        MANIFEST[daily manifest]
    end

    Session --> KB
    KB --> Backup
```

---

## 8. Infrastructure deployment

```mermaid
flowchart LR
    subgraph Local["Docker Compose 24/7"]
        APP[app: bot + agent]
        PG[(postgres pgvector)]
        VOL[data/papers]
        BKP[data/backups]
    end

    subgraph Cloud["Free cloud APIs"]
        GEM[Gemini API]
        GRQ[Groq API]
        SUP[Supabase optional remote PG]
    end

    subgraph Batch["Colab / Kaggle optional"]
        NB[reindex notebook]
    end

    APP --> PG
    APP --> VOL
    APP --> BKP
    APP --> GEM
    APP --> GRQ
    PG -.-> SUP
    NB -.-> PG
```

---

## 9. Summary generation strategy

```mermaid
flowchart LR
    Q[Topic query] --> E[Embed query]
    E --> VS[Vector search top chunks]
    VS --> G[Group by paper_id]
    G --> C[Top 3-5 chunks per paper]
    C --> S[Add paper summaries]
    S --> SYN[Gemini synthesis]
    SYN --> OUT[Report with arxiv_id citations]
```

Recommended for MVP: summaries + top chunks per paper (not full text in one prompt).

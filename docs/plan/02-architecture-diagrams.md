# Architecture Diagrams

Mermaid. Render in GitHub, VS Code, or any Mermaid viewer.

---

## 1. Knowledge Runtime (target)

```mermaid
flowchart TB
    subgraph Channel["Channel"]
        TG[Telegram whitelist]
    end

    subgraph Plan["Planner / router — spec 005"]
        P[Decompose question]
        R[Pick retrieval tool]
    end

    subgraph Retrieve["Retrieval"]
        H[Hybrid dense + FTS + RRF — as-built]
        RR[Rerank — spec 002]
        G[Graph — spec 007 late]
    end

    subgraph Guard["Corrective — spec 004"]
        C[Retrieval quality gate]
        S[Groundedness / Self-RAG]
    end

    subgraph Eval["Eval — spec 006"]
        M[Precision recall faithfulness relevancy]
        T[Traces]
    end

    KB[(Postgres papers + chunks + PDF volume)]

    TG --> P
    P --> R
    R --> H
    H --> RR
    R -.-> G
    RR --> C
    C --> S
    S --> TG
    H --> KB
    RR --> KB
    C --> H
    S --> Eval
```

Solid path today: Telegram -> heuristic route -> hybrid -> generate. Dashed: later specs.

---

## 2. As-built stack

```mermaid
flowchart LR
    TG[Telegram] --> BOT[aiogram bot]
    BOT --> ARX[arxiv search]
    BOT --> ING[ingest PDF extract chunk embed]
    BOT --> ASK["/ask router"]

    ASK --> HY[hybrid_search]
    ASK --> ANS[generate_answer / synthesize_answer]

    HY --> PG[(PostgreSQL pgvector)]
    ING --> PG
    ING --> VOL[data/papers PDF]
    ANS --> GEM[Gemini]
    HY --> GEM
```

No FastAPI, no LangGraph, no Groq router in the running path.

---

## 3. Ask path (today vs target)

```mermaid
sequenceDiagram
    participant U as User
    participant B as Bot
    participant RT as Router heuristic
    participant H as Hybrid RRF
    participant L as Gemini

    U->>B: /ask question
    B->>RT: point or synthesis
    alt point
        RT->>H: hybrid_search
        H->>L: generate_answer with citations
    else synthesis
        RT->>H: per-subquestion retrieve
        H->>L: synthesize_answer with citations
    end
    L-->>U: answer + sources

    Note over H,L: Later: rerank then CRAG then Self-RAG
```

---

## 4. PDF ingest pipeline

```mermaid
flowchart TD
    Q[User query] --> P[Parse topic + dates]
    P --> S[arXiv search]
    S --> D{Paper lifecycle}
    D -->|new| DL[Download PDF]
    D -->|indexed| Skip[Skip no mutation]
    D -->|pending text_ok failed| Manual[Owner /reindex]
    Manual --> DL
    DL --> FS[Local PDF storage]
    DL --> EX[Extract PyMuPDF]
    EX --> TextOk[text_ok]
    TextOk --> CH[Section window chunk]
    CH --> EM[Embed]
    EM --> DB2[(chunks + vectors)]
    DB2 --> Indexed[indexed]
    DL --> Failed[failed keep PDF]
    EX --> Failed
    CH --> Failed
    EM --> Failed
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
future staged-index design (own spec). Semantic rechunk (`003`) is that class of change.

---

## 6. Memory layers

```mermaid
flowchart TB
    subgraph Session["Short-term"]
        CTX[Current Telegram turn]
    end

    subgraph KB["Long-term"]
        PAPERS[papers metadata + summaries]
        CHUNKS[chunks + halfvec + tsvector]
        PDFS[PDF files on volume]
    end

    Session --> KB
```

JSONL backup and LangGraph checkpointer are not wired. Do not draw them as current.

---

## 7. Infrastructure

```mermaid
flowchart LR
    subgraph Local["Docker Compose"]
        APP[app: bot]
        PG[(postgres pgvector)]
        VOL[data/papers]
    end

    subgraph Cloud["APIs"]
        GEM[Gemini]
        ARX[arXiv]
    end

    APP --> PG
    APP --> VOL
    APP --> GEM
    APP --> ARX
```

---

## 8. Spec Kit vs this folder

```mermaid
flowchart LR
    VIS[docs/plan + RAG_UPGRADE_PLAN] -->|intent only| SP[specs/NNN]
    SP --> SPEC[spec.md]
    SPEC --> PLAN[plan.md]
    PLAN --> TASKS[tasks.md]
    TASKS --> CODE[app/]
```

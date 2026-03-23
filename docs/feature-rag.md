# Feature Doc: RAG (Retrieval-Augmented Generation) Pipeline

> Target reader: senior engineer integrating this feature into a new project.

---

## 1. Feature Summary

The RAG system enriches LLM-generated health & fitness plans with grounded, authoritative content. When a user asks the Goal Planner for a personalised plan, the system:

1. Embeds the user's goal as a vector.
2. Retrieves the most similar chunks from a curated article corpus (Pinecone).
3. Injects those chunks as "expert context" into the LLM prompt.
4. Cites sources in the final plan response.

If no sufficiently relevant content is found, it degrades gracefully — the LLM falls back to general knowledge and no citations are invented.

---

## 2. Key Entrypoints

| Type | Path | Purpose |
|------|------|---------|
| HTTP POST | `POST /api/v1/rag/ingest` | Trigger full ingestion pipeline (load → chunk → embed → upsert) |
| HTTP GET | `GET /api/v1/rag/search?q=...&top_k=N` | Debug retrieval quality |
| Internal call | `rag_service.retrieve(query)` | Used by Goal Planner during plan generation |
| Script | `backend/scripts/demo_rag.py` | 3-act demo (retrieval, planning, fallback) |
| Script | `backend/scripts/demo_rag_extended.py` | 6-act extended demo with interactive Q&A |
| Script | `download_articles.py` | Downloads corpus articles from web/PDF sources |

---

## 3. Architecture Overview

```
[download_articles.py]
        │  writes .txt files
        ▼
[Article Corpus — docs/*.txt]
        │
        ▼
POST /api/v1/rag/ingest
        │
        ▼
rag_service.ingest_articles()
   ├─ load_articles()       ← parse metadata headers + body
   ├─ chunk_articles()      ← RecursiveCharacterTextSplitter (2000/200)
   ├─ embed_texts()         ← OpenRouter → text-embedding-3-small (1536-dim)
   └─ Pinecone upsert       ← index: flux-articles, cosine, batches of 100

──────────────────────── (at query time) ─────────────────────────

User message → GoalPlanner._generate_plan()
        │
        ├─ rag_service.retrieve(query)
        │      ├─ embed_texts([query])
        │      └─ pinecone.query(top_k=5, include_metadata=True)
        │
        ├─ rag_service.format_rag_context(chunks, threshold=0.2)
        │      └─ filters by score, formats as numbered blocks
        │
        └─ LLM prompt with "EXPERT CONTEXT" section injected
               └─ Response contains plan + cited sources
```

---

## 4. Core Flow

### 4.1 Ingestion

**`rag_service.load_articles(articles_dir: Path)`** — `rag_service.py:71`

Reads every `.txt` / `.md` file. Expects one of two header formats:

```
# New format (2 lines)
Title: <title> | Source: <url>
Category: <category> | Authority: <authority>
---
<body>

# Legacy format (1 line)
Title: <title>
<body>
```

Returns a list of dicts: `{filename, title, source, category, authority, body}`.

---

**`rag_service.chunk_articles(articles)`** — `rag_service.py:190`

Uses LangChain `RecursiveCharacterTextSplitter`:

```python
chunk_size=2000, chunk_overlap=200
separators=["\n\n", "\n", ". ", " ", ""]
```

Each chunk carries all parent metadata plus `chunk_index`. Approximately 355 chunks for the 30-article corpus.

---

**`rag_service.embed_texts(texts: list[str])`** — `rag_service.py:239`

Calls the OpenAI client routed through OpenRouter:

```python
model = "openai/text-embedding-3-small"   # 1536 dimensions
batch_size = 64
base_url = settings.openrouter_base_url   # https://openrouter.ai/api/v1
api_key  = settings.open_router_api_key
```

Returns `list[list[float]]` of length 1536.

---

**`rag_service.ingest_articles(articles_dir, clear_existing=True)`** — `rag_service.py:272`

Orchestrates the full pipeline:
1. Calls `load_articles` → `chunk_articles` → `embed_texts`.
2. Upserts to Pinecone in batches of 100. Vector ID format: `{filename}_{chunk_index}`.
3. Optionally deletes all existing vectors before upserting (`clear_existing=True`).
4. Returns `{"status": "ok", "articles": N, "chunks": M}`.

---

### 4.2 Retrieval & Context Injection

**`rag_service.retrieve(query: str, top_k: int = 5)`** — `rag_service.py:338`

1. Embeds the query string (single call to `embed_texts`).
2. Calls `index.query(vector=..., top_k=top_k, include_metadata=True)`.
3. Returns list of dicts: `{text, title, source, category, authority, score}`.

---

**`rag_service.format_rag_context(chunks, relevance_threshold=0.2)`** — `rag_service.py:392`

Filters chunks below threshold, then formats as:

```
[1] Title: <title>
Source: <url>
Content: <text>

[2] ...
```

Returns a markdown string ready to be concatenated into an LLM prompt.

---

**`GoalPlanner._generate_plan()`** — `goal_planner.py:413`

The integration point:

```python
# 1. Build query from user context
query = f"{goal} {target} {preferences}"

# 2. Retrieve asynchronously (thread pool so it doesn't block the event loop)
chunks = await asyncio.get_event_loop().run_in_executor(
    None, rag_service.retrieve, query
)

# 3. Decide if content is relevant enough (AC3: score >= 0.4 for "relevant")
relevant = [c for c in chunks if c["score"] >= 0.4]

# 4. Format or use fallback
if relevant:
    expert_section = rag_service.format_rag_context(relevant)
    rag_rules = RAG_RULES       # "Ground recommendations in expert content, cite"
else:
    expert_section = FALLBACK_NO_EXPERT_CONTENT
    rag_rules = NO_RAG_RULES    # "Use general knowledge"

# 5. Inject into LLM prompt template
prompt = PLAN_PROMPT.format(expert_context_section=expert_section, rag_rules=rag_rules, ...)
```

LLM response includes `sources` as a JSON array of `{title, url}` objects.

---

### 4.3 Graceful Fallback

Two threshold constants control fallback behaviour (`goal_planner.py:104–119`):

| Constant | Value | Used for |
|----------|-------|---------|
| `rag_relevance_threshold` (config) | `0.2` | Filter before formatting (`format_rag_context`) |
| Hard-coded check in `_generate_plan` | `0.4` | Decides whether to use RAG rules vs. fallback rules |

When no chunks survive the 0.4 gate, the LLM receives `FALLBACK_NO_EXPERT_CONTENT` instead of sourced text, and `sources` is returned as `[]`. No citations are invented.

---

## 5. Data & Contracts

### Article file format (on disk)

```
Title: <string> | Source: <https://...>
Category: <string> | Authority: <government|peer_reviewed|hospital|university|professional>
---
<free text body>
```

### Pinecone vector metadata

```json
{
  "text":        "...",
  "title":       "...",
  "source":      "https://...",
  "category":    "...",
  "authority":   "...",
  "chunk_index": 0
}
```

Index: `flux-articles`, dimension: `1536`, metric: `cosine`.

### API response shape (from chat router, `chat.py:39–43`)

```json
{
  "sources": [
    { "title": "...", "url": "https://..." }
  ]
}
```

### Config settings (`config.py`)

| Key | Default | Description |
|-----|---------|-------------|
| `embedding_model` | `openai/text-embedding-3-small` | Model name passed to OpenRouter |
| `openrouter_base_url` | `https://openrouter.ai/api/v1` | Proxy base URL |
| `open_router_api_key` | — | Secret key |
| `pinecone_api_key` | — | Secret key |
| `pinecone_index_name` | `flux-articles` | Pinecone index name |
| `rag_chunk_size` | `2000` | Characters per chunk |
| `rag_chunk_overlap` | `200` | Overlap characters |
| `rag_top_k` | `5` | Default results returned |
| `rag_relevance_threshold` | `0.2` | Minimum score for format_rag_context |

---

## 6. Edge Cases & Error Handling

| Scenario | Handling |
|----------|---------|
| Pinecone unreachable at retrieval time | `retrieve()` is wrapped in try/except; `_generate_plan` catches exceptions and falls back to no-RAG mode |
| Off-domain query (e.g. "quantum computing") | Similarity scores stay below 0.4 threshold → fallback message injected |
| Duplicate sources across chunks | `_generate_plan` deduplicates by `title` before passing to chat response |
| Large embedding batch | `embed_texts` splits into batches of 64 to avoid payload limits |
| Ingest with stale vectors | `clear_existing=True` (default) deletes all vectors before re-upserting |
| Legacy article header format | `load_articles` handles both 1-line and 2-line header variants |

---

## 7. Extension Points

### Add a new article
1. Add the URL + metadata to `download_articles.py` registry.
2. Run `python download_articles.py` — it saves a `.txt` file to the corpus directory.
3. Call `POST /api/v1/rag/ingest` (or run the ingestion script) to re-embed and upsert.

### Change the embedding model
Update `settings.embedding_model` in `config.py` and re-run ingestion. Ensure the Pinecone index dimension matches the new model's output (1536 for `text-embedding-3-small`; 3072 for `text-embedding-3-large`).

### Swap vector stores
Replace `_get_pinecone_index()` and the `upsert` / `query` calls in `rag_service.py`. The rest of the pipeline is vector-store-agnostic.

### Tune retrieval quality
- Increase `rag_top_k` in config to retrieve more candidates.
- Raise `rag_relevance_threshold` to tighten the fallback gate.
- Try `text-embedding-3-large` for better semantic accuracy at higher cost.

### Add metadata filtering
Pinecone supports server-side metadata filters. Pass `filter={"category": "nutrition"}` to `index.query()` to restrict retrieval to a specific category.

---

## 8. Integration Guide: Porting to a New Project

### Step 1 — Dependencies

```
pinecone==5.4.2
langchain-text-splitters==0.2.4
openai==1.59.3          # used as OpenRouter client
beautifulsoup4>=4.12.0  # article downloading
pdfplumber>=0.10.0      # PDF articles
```

### Step 2 — Environment variables

```bash
PINECONE_API_KEY=...
OPEN_ROUTER_API_KEY=...
# Optionally:
PINECONE_INDEX_NAME=my-index
```

### Step 3 — Artifacts to copy

| File | What it provides |
|------|-----------------|
| `backend/app/services/rag_service.py` | All core RAG logic |
| `backend/app/routers/rag.py` | Ingest + search HTTP endpoints |
| `backend/app/config.py` (RAG fields only) | Typed settings |
| `download_articles.py` | Corpus downloader |
| `docs/rag-article-corpus.md` | Reference article registry |
| Article `.txt` files | The actual corpus |

### Step 4 — Create the Pinecone index

Log into Pinecone console and create a serverless index:
- Name: match `PINECONE_INDEX_NAME`
- Dimensions: `1536`
- Metric: `cosine`
- Cloud / region: any

### Step 5 — Prepare your article corpus

Write `.txt` files in the expected format:

```
Title: <title> | Source: <url>
Category: <category> | Authority: <authority>
---
<body text here>
```

Place them in a directory (e.g. `data/articles/`).

### Step 6 — Run ingestion

```bash
curl -X POST "http://localhost:8000/api/v1/rag/ingest?articles_dir=/abs/path/to/articles&clear_existing=true"
```

Or call `rag_service.ingest_articles(Path("data/articles"))` directly in a script.

### Step 7 — Integrate retrieval into your agent/LLM call

```python
from app.services.rag_service import rag_service

# At generation time:
chunks = rag_service.retrieve(user_query, top_k=5)
context = rag_service.format_rag_context(chunks, relevance_threshold=0.4)

if context:
    prompt = f"Use the following expert context:\n{context}\n\nUser question: {user_query}"
else:
    prompt = f"Answer from general knowledge.\n\nUser question: {user_query}"
```

### Step 8 — Verify with the search endpoint

```bash
curl "http://localhost:8000/api/v1/rag/search?q=your+test+query&top_k=5"
```

Check scores — you want scores > 0.4 for domain queries and scores < 0.3 for off-domain queries.

---

## 9. File Map

```
backend/
  app/
    services/
      rag_service.py         ← Core: load, chunk, embed, ingest, retrieve, format
    routers/
      rag.py                 ← HTTP endpoints: /ingest, /search
    agents/
      goal_planner.py        ← Consumer: calls retrieve(), injects context into LLM prompt
    config.py                ← RAG settings (chunk size, top_k, thresholds, API keys)
  scripts/
    demo_rag.py              ← 3-act demo script
    demo_rag_extended.py     ← 6-act extended demo with interactive mode
  requirements.txt           ← pinecone, langchain-text-splitters, openai, etc.

docs/
  feature-rag.md             ← This document
  rag-article-corpus.md      ← Registry of 30 curated articles with URLs + metadata
  agents/rag.md              ← High-level RAG service overview

download_articles.py         ← Downloads web/PDF articles and writes .txt corpus files
```

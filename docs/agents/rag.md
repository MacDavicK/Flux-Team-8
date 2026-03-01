# RAG (Retrieval-Augmented Generation)

> Last verified: 2026-03-01

## What it does

Article ingestion pipeline (load → chunk → embed → upsert to Pinecone) and semantic search. Used by the **Goal Planner** to ground plans in expert content. It is a **service**, not a conversational agent. The orchestrator does not call RAG directly.

## How to run

Same process as the main app. No separate server. Ingestion is on-demand via HTTP or a script.

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## Connection

- **In-process (primary):** Goal Planner calls `rag_service.retrieve(query)` and `rag_service.format_rag_context(chunks)` from [backend/app/agents/goal_planner.py](../../backend/app/agents/goal_planner.py). No HTTP needed for normal goal-planning flow.
- **HTTP (admin/debug):** For ingesting articles and for debugging search from outside the app.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/rag/ingest` | Run ingestion: load articles from disk, chunk, embed (OpenRouter), upsert to Pinecone. Query params: `articles_dir` (optional, default `backend/articles/`), `clear_existing` (default true). Returns article and chunk counts. |
| GET | `/api/v1/rag/search` | Search the vector store. Query params: `q`, optional `top_k`. Returns matching chunks (debug). |

Defined in [backend/app/routers/rag.py](../../backend/app/routers/rag.py). Implementation in [backend/app/services/rag_service.py](../../backend/app/services/rag_service.py).

## Orchestrator

The orchestrator does **not** call RAG. Goal Planner uses RAG internally when building plans. For the pipeline to use expert context:

1. Configure Pinecone: `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` in `backend/.env`.
2. Run ingestion at least once: `POST /api/v1/rag/ingest` (or use the same logic in a script).
3. Goal Planner will call `rag_service.retrieve(...)` when the user’s goal query matches; if no index or key is missing, it falls back to plans without RAG context.

## Dependencies

- **Embeddings:** OpenRouter (`OPEN_ROUTER_API_KEY`) — see [backend/app/config.py](../../backend/app/config.py) (`embedding_model`).
- **Vector store:** Pinecone (`PINECONE_API_KEY`, `PINECONE_INDEX_NAME`). Index must exist; dimensions must match the embedding model (e.g. text-embedding-3-small).
- **Articles:** Default directory `backend/articles/` (configurable via `articles_dir` on ingest). Format expected by the loader is defined in [backend/app/services/rag_service.py](../../backend/app/services/rag_service.py).

"""
Flux Backend — RAG Router (SCRUM-46)

Admin and debug endpoints for the RAG article ingestion pipeline.

Endpoints:
  POST /api/v1/rag/ingest  — Ingest articles into the Pinecone vector store
  GET  /api/v1/rag/search  — Search the vector store (debug/testing)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

# Default articles directory (relative to the backend/ root)
_DEFAULT_ARTICLES_DIR = Path(__file__).resolve().parents[2] / "articles"


# ── POST /api/v1/rag/ingest ─────────────────────────────────
# TODO: Add admin auth guard
# TODO: Restrict articles_dir to allowed paths (path traversal risk)

@router.post("/ingest")
async def ingest_articles(
    articles_dir: Optional[str] = Query(
        default=None,
        description="Path to the articles directory (defaults to backend/articles/)",
    ),
    clear_existing: bool = Query(
        default=True,
        description="Delete all existing vectors before ingesting (default: True)",
    ),
):
    """Run the full ingestion pipeline: load → chunk → embed → upsert.

    Returns the number of articles loaded and chunks upserted.
    """
    target_dir = Path(articles_dir) if articles_dir else _DEFAULT_ARTICLES_DIR

    if not target_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Articles directory not found: {target_dir}",
        )

    try:
        stats = rag_service.ingest_articles(target_dir, clear_existing=clear_existing)
    except Exception as e:
        logger.error("Ingestion failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return {"status": "ok", **stats}


# ── GET /api/v1/rag/search ──────────────────────────────────

@router.get("/search")
async def search_articles(
    q: str = Query(..., description="Search query"),
    top_k: Optional[int] = Query(
        default=None,
        description="Number of results to return (defaults to RAG_TOP_K)",
    ),
):
    """Search the Pinecone vector store for relevant article chunks.

    This is a debug/testing endpoint for verifying retrieval quality.
    """
    try:
        chunks = rag_service.retrieve(query=q, top_k=top_k)
    except Exception as e:
        logger.error("RAG search failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    return {"query": q, "results": chunks}

"""
RAG API endpoints.

POST /api/v1/rag/ingest  — Trigger full ingestion pipeline (dev/ops only).
GET  /api/v1/rag/search  — Debug retrieval quality (authenticated).
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.middleware.auth import get_current_user
from app.services.rag_service import rag_service

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ingest")
async def ingest_articles(
    articles_dir: str = Query(
        ..., description="Absolute path to the articles directory"
    ),
    clear_existing: bool = Query(
        True, description="Delete all existing vectors before upserting"
    ),
) -> dict:
    """
    Run the full RAG ingestion pipeline: load → chunk → embed → upsert to Pinecone.

    Restricted to development mode — returns 403 in production.
    Intended for first-time setup (via setup.sh) and corpus updates.

    To re-ingest after adding or changing articles:
        curl -X POST "http://localhost:8000/api/v1/rag/ingest?articles_dir=/abs/path/to/backend/articles&clear_existing=true"
    """
    if settings.app_env != "development":
        raise HTTPException(
            status_code=403,
            detail="RAG ingest is only available in development mode.",
        )

    path = Path(articles_dir)
    if not path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"articles_dir does not exist or is not a directory: {articles_dir}",
        )

    try:
        result = rag_service.ingest_articles(path, clear_existing=clear_existing)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    return result


@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results to return"),
    current_user=Depends(get_current_user),
) -> list[dict]:
    """
    Debug endpoint to verify retrieval quality against the Pinecone index.

    Scores > 0.4 indicate relevant results for domain queries.
    Scores < 0.3 for off-domain queries (e.g. non-health goals) are expected.

    Example:
        curl "http://localhost:8000/api/v1/rag/search?q=how+to+lose+weight&top_k=5"
    """
    chunks = rag_service.retrieve(q, top_k=top_k)
    return chunks

"""
Flux Backend — RAG Service (SCRUM-46)

Article ingestion pipeline and vector retrieval for the Goal Planner agent.

Responsibilities:
  - Load articles from disk, parse metadata (title, source, category, authority)
  - Chunk article bodies with RecursiveCharacterTextSplitter
  - Embed chunks via OpenRouter and upsert to Pinecone
  - Retrieve top-K chunks for a user query (semantic search)
  - Format retrieved context for LLM consumption (SCRUM-47 integration)

All configuration is read from ``app.config.settings``.
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pinecone import Pinecone

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Clients (lazy singletons)
# ---------------------------------------------------------------------------

_openai_client: Optional[OpenAI] = None
_pinecone_index = None


def _get_openai_client() -> OpenAI:
    """Return an OpenAI client routed through OpenRouter."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=settings.open_router_api_key,
            base_url=settings.openrouter_base_url,
        )
    return _openai_client


def _get_pinecone_index():
    """Return a handle to the Pinecone index (cached)."""
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _pinecone_index = pc.Index(settings.pinecone_index_name)
    return _pinecone_index


# ---------------------------------------------------------------------------
# 1. Load articles
# ---------------------------------------------------------------------------

def load_articles(articles_dir: Path) -> list[dict]:
    """Read all ``.txt`` / ``.md`` files from *articles_dir*.

    Supports two metadata header formats:

    **New format (30 curated articles):**
    ::

        Title: <title> | Source: <url>
        Category: <cat> | Authority: <auth>
        ---
        <body text>

    **Legacy format:**
    ::

        TITLE: <title> | SOURCE: <url>
        <body text>

    Returns a list of dicts with keys:
    ``title``, ``source``, ``category``, ``authority``, ``body``, ``filename``.
    """
    articles: list[dict] = []
    patterns = [str(articles_dir / ext) for ext in ("*.txt", "*.md")]

    for pattern in patterns:
        for filepath in sorted(glob.glob(pattern)):
            path = Path(filepath)
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

            if not lines:
                logger.warning("Skipping empty file: %s", filepath)
                continue

            meta = _parse_metadata(lines, filepath)

            if not meta["body"]:
                logger.warning("Skipping file with empty body: %s", filepath)
                continue

            articles.append(
                {
                    "title": meta["title"],
                    "source": meta["source"],
                    "category": meta["category"],
                    "authority": meta["authority"],
                    "body": meta["body"],
                    "filename": path.name,
                }
            )

    logger.info("Loaded %d article(s) from %s", len(articles), articles_dir)
    return articles


def _parse_metadata(lines: list[str], filepath: str) -> dict:
    """Extract title, source, category, authority, and body from file lines.

    Auto-detects the new 2-line header vs. the legacy single-line header.
    Falls back to filename-derived title and ``'unknown'`` defaults.
    """
    title = Path(filepath).stem.replace("_", " ").title()
    source = "unknown"
    category = "unknown"
    authority = "unknown"
    body_start = 0

    line1 = lines[0].strip() if len(lines) > 0 else ""
    line2 = lines[1].strip() if len(lines) > 1 else ""
    line3 = lines[2].strip() if len(lines) > 2 else ""

    # --- New format ---
    if line1.startswith("Title:") and line3 == "---":
        if "|" in line1:
            parts = line1.split("|", maxsplit=1)
            raw_title = parts[0].strip()
            raw_source = parts[1].strip() if len(parts) > 1 else ""
            if raw_title.startswith("Title:"):
                title = raw_title[len("Title:"):].strip()
            if raw_source.startswith("Source:"):
                source = raw_source[len("Source:"):].strip()

        if "|" in line2:
            parts = line2.split("|", maxsplit=1)
            raw_cat = parts[0].strip()
            raw_auth = parts[1].strip() if len(parts) > 1 else ""
            if raw_cat.startswith("Category:"):
                category = raw_cat[len("Category:"):].strip()
            if raw_auth.startswith("Authority:"):
                authority = raw_auth[len("Authority:"):].strip()

        body_start = 3

    # --- Legacy format ---
    elif "|" in line1 and line1.upper().startswith("TITLE:"):
        parts = line1.split("|", maxsplit=1)
        raw_title = parts[0].strip()
        raw_source = parts[1].strip() if len(parts) > 1 else ""
        if raw_title.upper().startswith("TITLE:"):
            title = raw_title[len("TITLE:"):].strip()
        if raw_source.upper().startswith("SOURCE:"):
            source = raw_source[len("SOURCE:"):].strip()
        body_start = 1

    body = "".join(lines[body_start:]).strip()

    return {
        "title": title,
        "source": source,
        "category": category,
        "authority": authority,
        "body": body,
    }


# ---------------------------------------------------------------------------
# 2. Chunk
# ---------------------------------------------------------------------------

def chunk_articles(articles: list[dict]) -> list[dict]:
    """Split each article body into overlapping chunks with metadata.

    Returns a flat list of dicts with keys:
    ``text``, ``filename``, ``metadata`` (dict with text, title, source,
    chunk_index, category, authority).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks: list[dict] = []

    for article in articles:
        splits = splitter.split_text(article["body"])
        logger.info(
            "  %s: %d chunks", article["filename"], len(splits),
        )

        for i, chunk_text in enumerate(splits):
            all_chunks.append(
                {
                    "text": chunk_text,
                    "filename": Path(article["filename"]).stem,
                    "metadata": {
                        "text": chunk_text,
                        "title": article["title"],
                        "source": article["source"],
                        "chunk_index": i,
                        "category": article["category"],
                        "authority": article["authority"],
                    },
                }
            )

    logger.info("Total chunks: %d", len(all_chunks))
    return all_chunks


# ---------------------------------------------------------------------------
# 3. Embed
# ---------------------------------------------------------------------------

_EMBED_BATCH_SIZE = 64


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed *texts* via OpenRouter.

    Returns a list of embedding vectors (one per input text).
    Uses batches of 64 to stay within typical API limits.
    """
    client = _get_openai_client()
    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[start : start + _EMBED_BATCH_SIZE]
        # TODO: Add retry logic for embedding API calls (handle 429/500 from OpenRouter)
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in response.data])
        logger.info(
            "Embedded batch %d (%d texts)",
            start // _EMBED_BATCH_SIZE + 1,
            len(batch),
        )

    return all_embeddings


# ---------------------------------------------------------------------------
# 4. Ingest (orchestrator)
# ---------------------------------------------------------------------------

_UPSERT_BATCH_SIZE = 100


def ingest_articles(articles_dir: Path, clear_existing: bool = True) -> dict:
    """Full ingestion pipeline: load → chunk → embed → upsert to Pinecone.

    When *clear_existing* is True (default), all vectors in the index are
    deleted before upserting.  Set to False for incremental ingestion.

    Returns ``{"articles": int, "chunks": int}``.
    """
    # Optionally clear the index before ingesting
    if clear_existing:
        index = _get_pinecone_index()
        index.delete(delete_all=True)
        logger.info("Cleared existing vectors from '%s'", settings.pinecone_index_name)

    # Load
    articles = load_articles(articles_dir)
    if not articles:
        logger.warning("No articles found in %s — nothing to ingest.", articles_dir)
        return {"articles": 0, "chunks": 0}

    # Chunk
    chunks = chunk_articles(articles)

    # Embed
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    # Build Pinecone vectors
    vectors = []
    for i, chunk in enumerate(chunks):
        vec_id = f"{chunk['filename']}_{chunk['metadata']['chunk_index']}"
        vectors.append(
            {
                "id": vec_id,
                "values": embeddings[i],
                "metadata": chunk["metadata"],
            }
        )

    # Upsert in batches
    index = _get_pinecone_index()
    total_upserted = 0
    for start in range(0, len(vectors), _UPSERT_BATCH_SIZE):
        batch = vectors[start : start + _UPSERT_BATCH_SIZE]
        index.upsert(vectors=batch)
        total_upserted += len(batch)
        logger.info(
            "Upserted batch %d (%d vectors)",
            start // _UPSERT_BATCH_SIZE + 1,
            len(batch),
        )

    logger.info(
        "Ingestion complete: %d articles, %d vectors upserted to '%s'",
        len(articles),
        total_upserted,
        settings.pinecone_index_name,
    )

    return {"articles": len(articles), "chunks": total_upserted}


# ---------------------------------------------------------------------------
# 5. Retrieve
# ---------------------------------------------------------------------------

def retrieve(query: str, top_k: Optional[int] = None) -> list[dict]:
    """Embed *query* and return the most similar chunks from Pinecone.

    Each result dict contains:
    ``text``, ``title``, ``source``, ``category``, ``authority``, ``score``.
    """
    if top_k is None:
        top_k = settings.rag_top_k

    # Embed query
    client = _get_openai_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=query,
    )
    query_embedding = response.data[0].embedding

    # Query Pinecone
    index = _get_pinecone_index()
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
    )

    # Unpack matches
    chunks: list[dict] = []
    for match in results.matches:
        meta = match.metadata
        chunks.append(
            {
                "text": meta["text"],
                "title": meta["title"],
                "source": meta["source"],
                "category": meta.get("category", "unknown"),
                "authority": meta.get("authority", "unknown"),
                "score": match.score,
            }
        )

    logger.info(
        "Retrieved %d chunks for query: '%s' (top score: %.4f)",
        len(chunks),
        query[:60],
        chunks[0]["score"] if chunks else 0.0,
    )

    return chunks


# ---------------------------------------------------------------------------
# 6. Format context (utility for SCRUM-47 Goal Planner integration)
# ---------------------------------------------------------------------------

def format_rag_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block with citations.

    Only includes chunks above the relevance threshold.
    Returns an empty string if no chunks pass the threshold.

    Example output::

        [1] Source: "Aim for a Healthy Weight" — https://www.nhlbi.nih.gov/...
        Content: A safe rate of weight loss is 1 to 2 pounds per week...

        [2] Source: "Steps for Losing Weight" — https://www.cdc.gov/...
        Content: Evidence shows that people who lose weight gradually...
    """
    threshold = settings.rag_relevance_threshold
    relevant = [c for c in chunks if c["score"] > threshold]

    if not relevant:
        return ""

    blocks: list[str] = []
    for i, chunk in enumerate(relevant, 1):
        blocks.append(
            f'[{i}] Source: "{chunk["title"]}" — {chunk["source"]}\n'
            f'Content: {chunk["text"]}'
        )

    return "\n\n".join(blocks)

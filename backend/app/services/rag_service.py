import logging
from pathlib import Path

from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# RAG Service
# ─────────────────────────────────────────────────────────────────


class _RagService:
    def __init__(self) -> None:
        self._index = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    # ── Pinecone ──────────────────────────────────────────────────

    def _get_index(self):
        """Lazy-initialise and cache the Pinecone index handle."""
        if self._index is None:
            pc = Pinecone(api_key=settings.pinecone_api_key)
            self._index = pc.Index(settings.pinecone_index_name)
        return self._index

    # ── Article loading ───────────────────────────────────────────

    def load_articles(self, articles_dir: Path) -> list[dict]:
        """
        Read every .txt / .md file in articles_dir.

        Supports two header formats:

            New (2-line):
                Title: <title> | Source: <url>
                Category: <category> | Authority: <authority>
                ---
                <body>

            Legacy (1-line):
                Title: <title>
                <body>
        """
        articles = []
        for path in sorted(articles_dir.iterdir()):
            if path.suffix not in {".txt", ".md"}:
                continue
            try:
                raw = path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.warning("Could not read %s: %s", path.name, exc)
                continue

            lines = raw.splitlines()
            title = source = category = authority = ""
            body_start = 0

            # New format: 2-line header + "---" separator
            if (
                len(lines) >= 3
                and lines[0].startswith("Title:")
                and lines[1].startswith("Category:")
                and lines[2].strip() == "---"
            ):
                line0_parts = {
                    p.split(":", 1)[0].strip(): p.split(":", 1)[1].strip()
                    for p in lines[0].split("|")
                    if ":" in p
                }
                line1_parts = {
                    p.split(":", 1)[0].strip(): p.split(":", 1)[1].strip()
                    for p in lines[1].split("|")
                    if ":" in p
                }
                title = line0_parts.get("Title", "")
                source = line0_parts.get("Source", "")
                category = line1_parts.get("Category", "")
                authority = line1_parts.get("Authority", "")
                body_start = 3

            # Legacy format: 1-line header
            elif lines[0].startswith("Title:"):
                title = lines[0].split(":", 1)[1].strip()
                body_start = 1

            body = "\n".join(lines[body_start:]).strip()
            if not body:
                logger.warning("Skipping %s — empty body", path.name)
                continue

            articles.append(
                {
                    "filename": path.name,
                    "title": title,
                    "source": source,
                    "category": category,
                    "authority": authority,
                    "body": body,
                }
            )

        logger.info("Loaded %d articles from %s", len(articles), articles_dir)
        return articles

    # ── Chunking ──────────────────────────────────────────────────

    def chunk_articles(self, articles: list[dict]) -> list[dict]:
        """Split article bodies into overlapping chunks; carry parent metadata."""
        chunks = []
        for article in articles:
            texts = self._splitter.split_text(article["body"])
            for idx, text in enumerate(texts):
                chunks.append(
                    {
                        "filename": article["filename"],
                        "title": article["title"],
                        "source": article["source"],
                        "category": article["category"],
                        "authority": article["authority"],
                        "chunk_index": idx,
                        "text": text,
                    }
                )
        logger.info("Produced %d chunks from %d articles", len(chunks), len(articles))
        return chunks

    # ── Embedding ─────────────────────────────────────────────────

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of strings via OpenRouter (openai/text-embedding-3-small).
        Batches in groups of 64 to stay within payload limits.
        Returns a list of 1536-dim float vectors.
        """
        client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        vectors: list[list[float]] = []
        batch_size = 64

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
                dimensions=settings.embedding_dimensions,
            )
            vectors.extend([item.embedding for item in response.data])

        return vectors

    # ── Ingestion ─────────────────────────────────────────────────

    def ingest_articles(self, articles_dir: Path, clear_existing: bool = True) -> dict:
        """
        Full pipeline: load → chunk → embed → upsert to Pinecone.
        Vector IDs: {filename}_{chunk_index}

        Returns {"status": "ok", "articles": N, "chunks": M}
        """
        index = self._get_index()

        articles = self.load_articles(articles_dir)
        if not articles:
            return {"status": "ok", "articles": 0, "chunks": 0}

        chunks = self.chunk_articles(articles)

        texts = [c["text"] for c in chunks]
        vectors = self.embed_texts(texts)

        if clear_existing:
            logger.info("Clearing existing vectors from Pinecone index")
            try:
                index.delete(delete_all=True)
            except Exception as exc:
                # Pinecone returns 404 "Namespace not found" on a fresh empty index — safe to ignore.
                logger.info("Delete all skipped (index likely empty): %s", exc)

        # Upsert in batches of 100
        upsert_batch_size = 100
        for i in range(0, len(chunks), upsert_batch_size):
            batch_chunks = chunks[i : i + upsert_batch_size]
            batch_vectors = vectors[i : i + upsert_batch_size]
            records = [
                {
                    "id": f"{c['filename']}_{c['chunk_index']}",
                    "values": v,
                    "metadata": {
                        "text": c["text"],
                        "title": c["title"],
                        "source": c["source"],
                        "category": c["category"],
                        "authority": c["authority"],
                        "chunk_index": c["chunk_index"],
                    },
                }
                for c, v in zip(batch_chunks, batch_vectors)
            ]
            index.upsert(vectors=records)
            logger.info(
                "Upserted batch %d–%d of %d chunks",
                i + 1,
                min(i + upsert_batch_size, len(chunks)),
                len(chunks),
            )

        logger.info(
            "Ingestion complete: %d articles, %d chunks", len(articles), len(chunks)
        )
        return {"status": "ok", "articles": len(articles), "chunks": len(chunks)}

    # ── Retrieval ─────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Embed query and fetch the most similar chunks from Pinecone.
        Returns list of {text, title, source, category, authority, score}.
        Returns [] on any exception (graceful fallback).
        """
        if not settings.pinecone_api_key:
            return []

        try:
            k = top_k if top_k is not None else settings.rag_top_k
            index = self._get_index()
            query_vector = self.embed_texts([query])[0]
            result = index.query(
                vector=query_vector,
                top_k=k,
                include_metadata=True,
            )
            return [
                {
                    "text": match.metadata.get("text", ""),
                    "title": match.metadata.get("title", ""),
                    "source": match.metadata.get("source", ""),
                    "category": match.metadata.get("category", ""),
                    "authority": match.metadata.get("authority", ""),
                    "score": match.score,
                }
                for match in result.matches
            ]
        except Exception as exc:
            logger.warning("RAG retrieval failed (graceful fallback): %s", exc)
            return []

    # ── Context formatting ────────────────────────────────────────

    def format_rag_context(self, chunks: list[dict]) -> str:
        """
        Filter chunks below rag_relevance_threshold, deduplicate by title,
        and format as numbered blocks ready for LLM prompt injection.
        Returns empty string if no chunks survive the filter.

        Deduplication ensures citation numbers [1]..[N] exactly match the
        N-entry sources list returned by rag_retriever_node.
        """
        relevant = [
            c for c in chunks if c.get("score", 0) >= settings.rag_relevance_threshold
        ]
        if not relevant:
            return ""

        # Keep first (highest-scored) chunk per unique source title so that
        # citation indices in the prompt align with the deduplicated sources list.
        seen: set[str] = set()
        deduped: list[dict] = []
        for chunk in relevant:
            title = chunk.get("title", "")
            if title not in seen:
                seen.add(title)
                deduped.append(chunk)

        blocks = []
        for i, chunk in enumerate(deduped, start=1):
            blocks.append(
                f"[{i}] Title: {chunk['title']}\n"
                f"Source: {chunk['source']}\n"
                f"Content: {chunk['text']}"
            )
        return "\n\n".join(blocks)


# ─────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────

rag_service = _RagService()

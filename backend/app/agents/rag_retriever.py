import logging

from app.agents.state import AgentState
from app.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

# Tags from the 14-tag classifier taxonomy that map to the health/fitness corpus
_RAG_TRIGGER_TAGS = set(settings.rag_trigger_tags)


async def rag_retriever_node(state: AgentState) -> dict:
    """
    Retrieves relevant expert context from Pinecone for health/fitness goals.

    Runs as a parallel node in the Send() fan-out from goal_planner (Phase 2).
    Only fires when the classifier has tagged the goal with a health-adjacent tag.

    Returns:
        rag_output: {
            "context":   formatted markdown string for LLM prompt injection,
            "sources":   deduplicated list of {title, url} for citation,
            "retrieved": bool — True if relevant content was found
        }
    """
    goal_draft: dict = state.get("goal_draft") or {}

    # Build a semantic query from available goal fields
    query_parts = list(
        filter(
            None,
            [
                goal_draft.get("title", ""),
                goal_draft.get("description", ""),
                goal_draft.get("target", ""),
                goal_draft.get("preferences", ""),
            ],
        )
    )

    # If structured fields aren't populated yet (Phase 2 runs before goal_planner LLM call),
    # build from clarification Q&A pairs which are available at this stage.
    if not query_parts:
        for qa in goal_draft.get("clarification_answers") or []:
            answer = qa.get("answer", "").strip()
            question = qa.get("question", "").strip()
            if answer and answer.lower() not in {"none", "n/a", ""}:
                query_parts.append(f"{question}: {answer}")

    # Also prepend the first user message (original goal statement) for context.
    history = state.get("conversation_history") or []
    first_user_msg = next(
        (m.get("content", "") for m in history if m.get("role") == "user"), ""
    )
    if first_user_msg:
        query_parts.insert(0, first_user_msg)

    query = " ".join(query_parts).strip()

    if not query:
        logger.warning("rag_retriever_node: no query could be built — returning empty")
        return {"rag_output": {"context": "", "sources": [], "retrieved": False}}

    # Retrieve — rag_service.retrieve() handles all exceptions and returns [] on failure
    chunks = rag_service.retrieve(query)

    # Format context (applies relevance threshold filter internally)
    context = rag_service.format_rag_context(chunks)

    # Deduplicated sources from chunks that passed the threshold
    seen: set[str] = set()
    sources: list[dict] = []
    for chunk in chunks:
        if chunk.get("score", 0) >= settings.rag_relevance_threshold:
            title = chunk.get("title", "")
            if title and title not in seen:
                seen.add(title)
                sources.append({"title": title, "url": chunk.get("source", "")})

    retrieved = bool(context)
    if retrieved:
        logger.info(
            "rag_retriever_node: retrieved %d relevant chunks, %d sources",
            len(
                [
                    c
                    for c in chunks
                    if c.get("score", 0) >= settings.rag_relevance_threshold
                ]
            ),
            len(sources),
        )
    else:
        logger.info("rag_retriever_node: no relevant chunks above threshold")

    return {
        "rag_output": {"context": context, "sources": sources, "retrieved": retrieved}
    }

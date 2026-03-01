"""
Chat API endpoints — §17.1

POST /api/v1/chat/message        — Send a message; runs the LangGraph agent and persists results.
GET  /api/v1/chat/history        — Fetch paginated conversation history for a conversation.
GET  /api/v1/chat/conversations  — List all conversations for the current user.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.agents.graph import compiled_graph
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import limiter
from app.models.api_schemas import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageSchema,
)
from app.services.context_manager import window_conversation_history
from app.services.supabase import db

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    body: ChatMessageRequest,
    current_user=Depends(get_current_user),
) -> ChatMessageResponse:
    """
    17.1.1–17.1.4 — Accept a user message, run the LangGraph agent, persist
    results to DB, and return the assistant reply with metadata.
    """
    user_id: str = str(current_user["sub"])

    # ── 17.1.2  Resolve or create conversation ──────────────────────────────
    if body.conversation_id is None:
        thread_id = str(uuid.uuid4())
        conv = await db.fetchrow(
            """
            INSERT INTO conversations (user_id, langgraph_thread_id, context_type)
            VALUES ($1, $2, 'general')
            RETURNING id, langgraph_thread_id
            """,
            uuid.UUID(user_id),
            thread_id,
        )
        conv_id: uuid.UUID = conv["id"]
        langgraph_thread_id: str = conv["langgraph_thread_id"]
    else:
        conv = await db.fetchrow(
            "SELECT id, user_id, langgraph_thread_id FROM conversations WHERE id = $1",
            uuid.UUID(body.conversation_id),
        )
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if str(conv["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        conv_id = conv["id"]
        langgraph_thread_id = conv["langgraph_thread_id"]

    # ── Load conversation history from DB ────────────────────────────────────
    rows = await db.fetch(
        """
        SELECT id, role, content, agent_node, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        """,
        conv_id,
    )

    # Exclude 'summary' role messages from graph input; keep them in DB only.
    history: list[dict] = [
        {"role": row["role"], "content": row["content"]}
        for row in rows
        if row["role"] != "summary"
    ]

    # ── Apply context window, add new user turn ──────────────────────────────
    history = await window_conversation_history(history, user_id, str(conv_id))
    history.append({"role": "user", "content": body.message})

    # ── Fetch user profile ───────────────────────────────────────────────────
    user_row = await db.fetchrow(
        "SELECT profile, timezone FROM users WHERE id = $1",
        uuid.UUID(user_id),
    )
    user_profile: dict = {}
    if user_row and user_row["profile"]:
        raw = user_row["profile"]
        user_profile = dict(raw) if not isinstance(raw, dict) else raw

    # ── Build initial AgentState ─────────────────────────────────────────────
    # user_profile is only injected when the DB has a populated profile (i.e. the
    # user is onboarded). For new users mid-onboarding, omitting the key lets the
    # LangGraph checkpointer's accumulated onboarding state (tracking keys like
    # _wake_collected, etc.) survive across turns without being overwritten.
    state: dict = {
        "user_id": user_id,
        "conversation_history": history,
        "intent": None,
        "goal_draft": None,
        "proposed_tasks": None,
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "approval_status": None,
        "error": None,
        "token_usage": {},
        "correlation_id": str(uuid.uuid4()),
        **({"user_profile": user_profile} if user_profile else {}),
    }

    # ── Run LangGraph ────────────────────────────────────────────────────────
    result: dict = await compiled_graph.ainvoke(
        state,
        config={"configurable": {"thread_id": langgraph_thread_id}},
    )

    # ── Extract assistant reply ──────────────────────────────────────────────
    reply: str = ""
    for msg in reversed(result.get("conversation_history", [])):
        if msg.get("role") == "assistant":
            reply = msg.get("content", "")
            break

    # ── Persist messages to DB ───────────────────────────────────────────────
    await db.execute(
        """
        INSERT INTO messages (conversation_id, role, content)
        VALUES ($1, 'user', $2)
        """,
        conv_id,
        body.message,
    )
    await db.execute(
        """
        INSERT INTO messages (conversation_id, role, content, agent_node)
        VALUES ($1, 'assistant', $2, $3)
        """,
        conv_id,
        reply,
        result.get("intent"),
    )

    # ── Update conversation timestamp ────────────────────────────────────────
    await db.execute(
        "UPDATE conversations SET last_message_at = NOW() WHERE id = $1",
        conv_id,
    )

    return ChatMessageResponse(
        conversation_id=str(conv_id),
        message=reply,
        agent_node=result.get("intent"),
        proposed_plan=result.get("goal_draft"),
        requires_user_action=result.get("approval_status") == "pending",
    )


@router.get("/history", response_model=ChatHistoryResponse)
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    conversation_id: str | None = Query(None, description="UUID of the conversation; omit to get the most recent one"),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> ChatHistoryResponse:
    """17.1.3 — Return paginated message history for a conversation, oldest first.

    If conversation_id is omitted the user's most recently active conversation
    is used. Returns an empty message list (with conversation_id=null) when the
    user has no conversations yet.
    """
    user_id: str = str(current_user["sub"])

    if conversation_id is None:
        # Resolve most-recent conversation for this user.
        conv = await db.fetchrow(
            """
            SELECT id, user_id FROM conversations
            WHERE user_id = $1
            ORDER BY last_message_at DESC NULLS LAST, created_at DESC
            LIMIT 1
            """,
            uuid.UUID(user_id),
        )
        if conv is None:
            # No conversations yet — return empty history so the chat page
            # can display the appropriate greeting without erroring.
            return ChatHistoryResponse(conversation_id=None, messages=[])
    else:
        conv = await db.fetchrow(
            "SELECT id, user_id FROM conversations WHERE id = $1",
            uuid.UUID(conversation_id),
        )
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if str(conv["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    rows = await db.fetch(
        """
        SELECT id, role, content, agent_node, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        LIMIT $2
        """,
        conv["id"],
        limit,
    )

    messages = [
        MessageSchema(
            id=str(row["id"]),
            role=row["role"],
            content=row["content"],
            agent_node=row["agent_node"],
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return ChatHistoryResponse(
        conversation_id=str(conv["id"]),
        messages=messages,
    )


@router.get("/conversations", response_model=ConversationListResponse)
@limiter.limit("30/minute")
async def list_conversations(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    current_user=Depends(get_current_user),
) -> ConversationListResponse:
    """Return the user's conversations, newest first, with a preview of the first user message."""
    user_id: str = str(current_user["sub"])

    rows = await db.fetch(
        """
        SELECT
            c.id,
            c.last_message_at,
            c.created_at,
            (
                SELECT content FROM messages
                WHERE conversation_id = c.id AND role = 'user'
                ORDER BY created_at ASC
                LIMIT 1
            ) AS preview
        FROM conversations c
        WHERE c.user_id = $1
        ORDER BY c.last_message_at DESC NULLS LAST, c.created_at DESC
        LIMIT $2
        """,
        uuid.UUID(user_id),
        limit,
    )

    conversations = [
        ConversationSummary(
            id=str(row["id"]),
            last_message_at=row["last_message_at"],
            created_at=row["created_at"],
            preview=row["preview"][:80] if row["preview"] else None,
        )
        for row in rows
    ]

    return ConversationListResponse(conversations=conversations)

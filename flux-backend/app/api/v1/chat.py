"""
Chat API endpoints — §17.1

POST /api/v1/chat/message  — Send a message; runs the LangGraph agent and persists results.
GET  /api/v1/chat/history  — Fetch paginated conversation history for a conversation.
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
    user_id: str = str(current_user.id)

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
    state: dict = {
        "user_id": user_id,
        "conversation_history": history,
        "intent": None,
        "user_profile": user_profile,
        "goal_draft": None,
        "proposed_tasks": None,
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "approval_status": None,
        "error": None,
        "token_usage": {},
        "correlation_id": str(uuid.uuid4()),
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
async def get_history(
    conversation_id: str = Query(..., description="UUID of the conversation"),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
) -> ChatHistoryResponse:
    """17.1.3 — Return paginated message history for a conversation, oldest first."""
    user_id: str = str(current_user.id)

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
        conversation_id=conversation_id,
        messages=messages,
    )

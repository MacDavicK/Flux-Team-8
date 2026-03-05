"""
Chat API endpoints — §17.1

POST /api/v1/chat/message        — Send a message; runs the LangGraph agent and persists results.
GET  /api/v1/chat/history        — Fetch paginated conversation history for a conversation.
GET  /api/v1/chat/conversations  — List all conversations for the current user.
"""
from __future__ import annotations

import itertools
import json
import uuid
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request

import app.agents.graph as _graph_module
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import limiter
from app.models.api_schemas import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationListResponse,
    ConversationSummary,
    MessageSchema,
    OnboardingStartRequest,
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
    _raw_profile = user_row["profile"] if user_row and user_row["profile"] else None
    if _raw_profile is None:
        user_profile: dict[str, Any] = {}
    elif isinstance(_raw_profile, str):
        user_profile = cast(dict[str, Any], json.loads(_raw_profile))
    else:
        user_profile = cast(dict[str, Any], dict(_raw_profile))

    # Ensure timezone from dedicated column takes precedence over profile JSON
    if user_row and user_row["timezone"]:
        user_profile["timezone"] = user_row["timezone"]

    # ── Build initial AgentState ─────────────────────────────────────────────
    # user_profile is loaded from DB on every turn. The onboarding node writes
    # partial answers back to users.profile after each step, so the DB is always
    # the authoritative source of onboarding progress.
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
        "onboarding_options": None,
        **({"user_profile": user_profile} if user_profile else {}),
    }

    # ── Run LangGraph ────────────────────────────────────────────────────────
    result: dict = await _graph_module.compiled_graph.ainvoke(
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
    goal_draft = result.get("goal_draft")
    approval_pending = result.get("approval_status") == "pending"
    # Only persist the plan in metadata when the user still needs to act on it.
    # After save_tasks runs, approval_status is None — don't echo the plan back.
    metadata = {"proposed_plan": goal_draft} if goal_draft and approval_pending else None
    await db.execute(
        """
        INSERT INTO messages (conversation_id, role, content, agent_node, metadata)
        VALUES ($1, 'assistant', $2, $3, $4)
        """,
        conv_id,
        reply,
        result.get("intent"),
        json.dumps(metadata) if metadata else None,
    )

    # ── Update conversation timestamp + title ────────────────────────────────
    # Set a title once the agent produces a goal plan. Use the user's original
    # goal message (first user message in this conversation) as the title —
    # it's the most natural, human-readable label. Cap at 80 chars.
    # COALESCE ensures an existing title is never overwritten.
    conv_title: str | None = None
    if result.get("intent") == "GOAL" and result.get("goal_draft"):
        # Walk history to find the user message that triggered this goal turn
        for msg in (result.get("conversation_history") or []):
            if msg.get("role") == "user":
                raw = (msg.get("content") or "").strip()
                if raw:
                    conv_title = raw[:80]
                    break

    if conv_title:
        await db.execute(
            """
            UPDATE conversations
            SET last_message_at = NOW(), title = COALESCE(title, $2)
            WHERE id = $1
            """,
            conv_id,
            conv_title,
        )
    else:
        await db.execute(
            "UPDATE conversations SET last_message_at = NOW() WHERE id = $1",
            conv_id,
        )

    return ChatMessageResponse(
        conversation_id=str(conv_id),
        message=reply,
        agent_node=result.get("intent"),
        proposed_plan=goal_draft if approval_pending else None,
        requires_user_action=approval_pending,
        onboarding_options=result.get("onboarding_options"),
    )


@router.post("/onboarding/start", response_model=ChatMessageResponse)
@limiter.limit("10/minute")
async def start_onboarding(
    request: Request,
    body: OnboardingStartRequest = None,
    current_user=Depends(get_current_user),
) -> ChatMessageResponse:
    """
    Trigger the first onboarding message without requiring user input.

    Called by the frontend when a non-onboarded user opens /chat and
    has no prior messages. Runs the LangGraph graph with an empty history
    so onboarding_node fires _ask_question("name") and returns the greeting.

    Idempotent: if a conversation with messages already exists, returns that
    conversation_id with an empty message (frontend resumes normally).
    Returns 409 if the user is already onboarded.
    """
    user_id: str = str(current_user["sub"])

    # Guard: already onboarded; also fetch profile for state injection
    user_row = await db.fetchrow(
        "SELECT onboarded, profile FROM users WHERE id = $1", uuid.UUID(user_id)
    )
    if user_row and user_row["onboarded"]:
        raise HTTPException(status_code=409, detail="User already onboarded")

    user_profile: dict = {}
    if user_row and user_row["profile"]:
        raw = user_row["profile"]
        if isinstance(raw, str):
            user_profile = json.loads(raw)
        elif isinstance(raw, dict):
            user_profile = raw
        else:
            user_profile = dict(raw)

    # Idempotency: if a conversation with at least one message exists, resume it
    existing = await db.fetchrow(
        """
        SELECT c.id, c.langgraph_thread_id
        FROM conversations c
        JOIN messages m ON m.conversation_id = c.id
        WHERE c.user_id = $1
        ORDER BY c.last_message_at DESC NULLS LAST, c.created_at DESC
        LIMIT 1
        """,
        uuid.UUID(user_id),
    )
    if existing:
        return ChatMessageResponse(
            conversation_id=str(existing["id"]),
            message="",
            agent_node="ONBOARDING",
        )

    # Create a new conversation
    thread_id = str(uuid.uuid4())
    conv = await db.fetchrow(
        """
        INSERT INTO conversations (user_id, langgraph_thread_id, context_type)
        VALUES ($1, $2, 'onboarding')
        RETURNING id, langgraph_thread_id
        """,
        uuid.UUID(user_id),
        thread_id,
    )
    conv_id: uuid.UUID = conv["id"]
    langgraph_thread_id: str = conv["langgraph_thread_id"]

    # Merge timezone from request body into the profile so onboarding_node
    # stores it without asking the user. Falls back to "UTC" if not provided.
    tz = (body.timezone if body and body.timezone else None) or "UTC"
    user_profile["timezone"] = tz

    # Run graph with empty history — onboarding_node detects no messages and
    # calls _get_question directly (no LLM call needed).
    # Inject any existing profile so the node skips steps already answered
    # (e.g. name pre-populated from OAuth sign-up).
    state: dict = {
        "user_id": user_id,
        "conversation_history": [],
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
        "onboarding_options": None,
        "user_profile": user_profile,
    }
    result: dict = await _graph_module.compiled_graph.ainvoke(
        state,
        config={"configurable": {"thread_id": langgraph_thread_id}},
    )

    # Extract the greeting from conversation_history
    greeting = next(
        (
            m["content"]
            for m in reversed(result.get("conversation_history") or [])
            if m["role"] == "assistant"
        ),
        None,
    )

    # Persist the greeting message and update conversation timestamp
    if greeting:
        await db.execute(
            """
            INSERT INTO messages (conversation_id, role, content, agent_node)
            VALUES ($1, 'assistant', $2, 'ONBOARDING')
            """,
            conv_id,
            greeting,
        )
        await db.execute(
            "UPDATE conversations SET last_message_at = NOW() WHERE id = $1",
            conv_id,
        )

    return ChatMessageResponse(
        conversation_id=str(conv_id),
        message=greeting or "Hi there! I'm Flux, your AI life coach. What should I call you?",
        agent_node="ONBOARDING",
        onboarding_options=result.get("onboarding_options"),
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
        SELECT id, role, content, agent_node, created_at, metadata
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
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
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
    cursor: str | None = Query(None, description="ISO8601 last_message_at of the last item for keyset pagination"),
    current_user=Depends(get_current_user),
) -> ConversationListResponse:
    """Return 10 conversations per page, newest first, with keyset pagination.

    Pass the returned next_cursor as the cursor query param to load the next page.
    has_more=false means you've reached the end.
    """
    _PAGE_SIZE = 10
    user_id: str = str(current_user["sub"])

    if cursor:
        rows = await db.fetch(
            """
            SELECT
                c.id,
                c.last_message_at,
                c.created_at,
                c.title,
                (
                    SELECT content FROM messages
                    WHERE conversation_id = c.id AND role = 'user'
                    ORDER BY created_at ASC
                    LIMIT 1
                ) AS preview
            FROM conversations c
            WHERE c.user_id = $1
              AND (c.context_type IS NULL OR c.context_type != 'onboarding')
              AND (c.last_message_at < $2::timestamptz
                   OR (c.last_message_at IS NULL AND $2 IS NOT NULL))
            ORDER BY c.last_message_at DESC NULLS LAST, c.created_at DESC
            LIMIT $3
            """,
            uuid.UUID(user_id),
            cursor,
            _PAGE_SIZE + 1,
        )
    else:
        rows = await db.fetch(
            """
            SELECT
                c.id,
                c.last_message_at,
                c.created_at,
                c.title,
                (
                    SELECT content FROM messages
                    WHERE conversation_id = c.id AND role = 'user'
                    ORDER BY created_at ASC
                    LIMIT 1
                ) AS preview
            FROM conversations c
            WHERE c.user_id = $1
              AND (c.context_type IS NULL OR c.context_type != 'onboarding')
            ORDER BY c.last_message_at DESC NULLS LAST, c.created_at DESC
            LIMIT $2
            """,
            uuid.UUID(user_id),
            _PAGE_SIZE + 1,
        )

    rows_list: list[Any] = list(rows)
    has_more = len(rows_list) > _PAGE_SIZE
    page: list[Any] = list(itertools.islice(rows_list, _PAGE_SIZE))

    next_cursor: str | None = None
    if has_more and page:
        last = page[-1]
        next_cursor = last["last_message_at"].isoformat() if last["last_message_at"] else None

    conversations = [
        ConversationSummary(
            id=str(row["id"]),
            last_message_at=row["last_message_at"],
            created_at=row["created_at"],
            title=row["title"],
            preview=row["preview"][:80] if row["preview"] else None,
        )
        for row in page
    ]

    return ConversationListResponse(
        conversations=conversations,
        has_more=has_more,
        next_cursor=next_cursor,
    )

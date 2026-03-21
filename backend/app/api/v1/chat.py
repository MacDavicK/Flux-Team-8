"""
Chat API endpoints — §17.1

POST /api/v1/chat/message        — Send a message; runs the LangGraph agent and persists results.
GET  /api/v1/chat/history        — Fetch paginated conversation history for a conversation.
GET  /api/v1/chat/conversations  — List all conversations for the current user.
"""

from __future__ import annotations

import itertools
import json
import re
import uuid
from typing import Any, Optional, cast


from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

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
    OnboardingOptionSchema,
    OnboardingStartRequest,
    RagSource,
)
from app.services.context_manager import window_conversation_history
from app.services.supabase import db
from app.api.v1.tasks import (
    _fetch_task_or_404,
    _compute_simple_reschedule_slots,
    _build_slot_options,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def strip_markdown(text: str) -> str:
    """Remove common markdown syntax for TTS."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text.strip()


def build_spoken_summary(response: "ChatMessageResponse") -> str:
    if response.proposed_plan:
        n = len(response.proposed_plan.get("milestones", []))
        return f"I've built a {n}-week plan for you. Take a look and tap Activate when you're ready."
    if response.questions:
        n = len(response.questions)
        return f"I have {n} quick question{'s' if n > 1 else ''} to help me plan your goal better."
    if response.options and response.agent_node == "ask_start_date":
        return "When would you like to start? Pick a date below."
    if response.options:
        return "Here are some options for you. Tap one to continue."
    return strip_markdown(response.message)[:300]


@router.post("/message")
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    body: ChatMessageRequest,
    current_user=Depends(get_current_user),
) -> StreamingResponse:
    """SSE stream. Events: progress | complete | error (text/event-stream)."""
    return StreamingResponse(
        _send_message_events(body, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _send_message_events(body: ChatMessageRequest, current_user: dict):
    """Async generator yielding SSE events for the chat message endpoint."""
    user_id: str = str(current_user["sub"])

    # ── Short-circuit: RESCHEDULE_TASK with pre-set intent ───────────────────
    if body.intent == "RESCHEDULE_TASK" and body.task_id:
        task = await _fetch_task_or_404(body.task_id, user_id)

        user_row = await db.fetchrow(
            "SELECT timezone, profile FROM users WHERE id = $1",
            uuid.UUID(user_id),
        )
        user_tz = "UTC"
        if user_row:
            user_tz = user_row["timezone"] or "UTC"

        # Resolve or create conversation (scoped to task reschedule)
        conv_id: Optional[uuid.UUID] = None
        if body.conversation_id:
            conv = await db.fetchrow(
                "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
                uuid.UUID(body.conversation_id),
                uuid.UUID(user_id),
            )
            if conv:
                conv_id = conv["id"]

        if conv_id is None:
            thread_id = str(uuid.uuid4())
            conv = await db.fetchrow(
                """
                INSERT INTO conversations (user_id, langgraph_thread_id, context_type)
                VALUES ($1, $2, 'general')
                RETURNING id
                """,
                uuid.UUID(user_id),
                thread_id,
            )
            conv_id = conv["id"]

        task_title = task["title"]
        is_recurring = bool(task.get("recurrence_rule"))

        # ── Step 1: Ask scope (only for recurring tasks, first turn) ─────────
        if is_recurring and not body.reschedule_scope:
            scope_options = [
                OnboardingOptionSchema(label="Just this one", value="scope:one"),
                OnboardingOptionSchema(
                    label="This one + all future", value="scope:series"
                ),
            ]
            reply = (
                f"Would you like to reschedule just this occurrence of **{task_title}**, "
                f"or this one and all future occurrences?"
            )
            await db.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES ($1, 'user', $2)",
                conv_id,
                body.message,
            )
            await db.execute(
                "INSERT INTO messages (conversation_id, role, content, agent_node) VALUES ($1, 'assistant', $2, 'RESCHEDULE_SCOPE')",
                conv_id,
                reply,
            )
            await db.execute(
                "UPDATE conversations SET last_message_at = NOW() WHERE id = $1",
                conv_id,
            )
            resp = ChatMessageResponse(
                conversation_id=str(conv_id),
                message=reply,
                agent_node="RESCHEDULE_SCOPE",
                proposed_plan=None,
                requires_user_action=True,
                options=scope_options,
            )
            resp.spoken_summary = build_spoken_summary(resp)
            yield f"data: {json.dumps({'type': 'complete', 'data': resp.model_dump(mode='json')})}\n\n"
            return

        # ── Step 2: Return time slot options ─────────────────────────────────
        scope = body.reschedule_scope or "one"
        series_mode = scope == "series"
        simple_slots = await _compute_simple_reschedule_slots(task, user_id, user_tz)
        slot_options = _build_slot_options(
            simple_slots, user_tz, body.task_id, series_mode=series_mode
        )
        real_slots = [o for o in slot_options if o.value is not None]
        slot_count = len(real_slots)
        scope_prefix = (
            "You've chosen to update **all future occurrences**. "
            if series_mode
            else ""
        )
        reply = (
            f"{scope_prefix}Here {'is' if slot_count == 1 else 'are'} the next available "
            f"{'slot' if slot_count == 1 else 'slots'} for **{task_title}**. "
            f"Pick one or choose a custom date & time."
        )

        await db.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES ($1, 'user', $2)",
            conv_id,
            body.message,
        )
        await db.execute(
            "INSERT INTO messages (conversation_id, role, content, agent_node) VALUES ($1, 'assistant', $2, 'RESCHEDULE_TASK')",
            conv_id,
            reply,
        )
        await db.execute(
            "UPDATE conversations SET last_message_at = NOW() WHERE id = $1",
            conv_id,
        )

        resp = ChatMessageResponse(
            conversation_id=str(conv_id),
            message=reply,
            agent_node="RESCHEDULE_TASK",
            proposed_plan=None,
            requires_user_action=True,
            options=slot_options,
        )
        resp.spoken_summary = build_spoken_summary(resp)
        yield f"data: {json.dumps({'type': 'complete', 'data': resp.model_dump(mode='json')})}\n\n"
        return

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
            yield f"data: {json.dumps({'type': 'error', 'message': 'Conversation not found'})}\n\n"
            return
        if str(conv["user_id"]) != user_id:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Access denied'})}\n\n"
            return
        conv_id = conv["id"]
        langgraph_thread_id = conv["langgraph_thread_id"]

    # ── Load conversation history from DB ────────────────────────────────────
    rows = await db.fetch(
        """
        SELECT id, role, content, agent_node, created_at, metadata
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
        """,
        conv_id,
    )

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

    if user_row and user_row["timezone"]:
        user_profile["timezone"] = user_row["timezone"]

    # ── Restore pending approval state ───────────────────────────────────────
    pending_goal_draft: dict | None = None
    pending_proposed_tasks: list | None = None
    pending_approval_status: str | None = None
    pending_classifier_output: dict | None = None
    for row in reversed(rows):
        if row["role"] == "assistant" and row["metadata"]:
            meta = (
                json.loads(row["metadata"])
                if isinstance(row["metadata"], str)
                else dict(row["metadata"])
            )
            plan = meta.get("proposed_plan")
            if plan:
                plan_approval = plan.get("plan", {}).get("approval_status")
                if plan_approval == "pending":
                    pending_goal_draft = plan
                    pending_proposed_tasks = plan.get("plan", {}).get("proposed_tasks")
                    pending_approval_status = "pending"
                    pending_classifier_output = meta.get("classifier_output")
                elif meta.get("approval_status") == "awaiting_start_date":
                    pending_goal_draft = plan
                    pending_proposed_tasks = plan.get("plan", {}).get("proposed_tasks")
                    pending_approval_status = "awaiting_start_date"
                    pending_classifier_output = meta.get("classifier_output")
            break

    # ── Build initial AgentState ─────────────────────────────────────────────
    initial_goal_draft = pending_goal_draft
    if body.intent == "GOAL_CLARIFY" and body.answers:
        initial_goal_draft = dict(pending_goal_draft or {})
        initial_goal_draft["clarification_answers"] = [
            a.model_dump() for a in body.answers
        ]

    state: dict = {
        "user_id": user_id,
        "conversation_history": history,
        "intent": body.intent or None,
        "goal_draft": initial_goal_draft,
        "proposed_tasks": pending_proposed_tasks,
        "classifier_output": pending_classifier_output,
        "scheduler_output": None,
        "pattern_output": None,
        "approval_status": pending_approval_status,
        "error": None,
        "token_usage": {},
        "correlation_id": str(uuid.uuid4()),
        "conversation_id": str(conv_id),
        "options": None,
        **({"user_profile": user_profile} if user_profile else {}),
    }

    # ── Run LangGraph via astream_events ─────────────────────────────────────
    result: dict | None = None
    try:
        async for event in _graph_module.compiled_graph.astream_events(
            state,
            version="v2",
            config={"configurable": {"thread_id": langgraph_thread_id}},
        ):
            if event["event"] == "on_chain_start":
                node = event.get("metadata", {}).get("langgraph_node")
                # Only emit when the event name matches the node name to avoid
                # duplicate events from parent subgraph on_chain_start firings.
                if node and event.get("name") == node:
                    yield f"data: {json.dumps({'type': 'progress', 'node': node})}\n\n"
            elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                result = event["data"].get("output")
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        return

    if result is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Graph produced no output'})}\n\n"
        return

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
    result_approval = result.get("approval_status")
    approval_pending = result_approval == "pending"
    awaiting_start_date = result_approval == "awaiting_start_date"
    agent_node_value = (
        "ask_start_date" if awaiting_start_date else result.get("intent") or None
    )
    # Extract RAG provenance upfront — used in both metadata and resp below
    _rag_output = result.get("rag_output") or {}
    _rag_used = bool(_rag_output.get("retrieved"))
    _rag_sources = (
        [
            RagSource(title=s.get("title", ""), url=s.get("url") or None)
            for s in _rag_output.get("sources", [])
        ]
        if _rag_used
        else []
    )
    if goal_draft and (approval_pending or awaiting_start_date):
        metadata: dict | None = {
            "proposed_plan": goal_draft,
            "classifier_output": result.get("classifier_output"),
            "approval_status": result_approval,
            "rag_used": _rag_used,
            "rag_sources": [s.model_dump() for s in _rag_sources],
        }
    elif agent_node_value == "ONBOARDING" and result.get("options"):
        metadata = {"options": result.get("options")}
    else:
        metadata = None
    await db.execute(
        """
        INSERT INTO messages (conversation_id, role, content, agent_node, metadata)
        VALUES ($1, 'assistant', $2, $3, $4)
        """,
        conv_id,
        reply,
        agent_node_value,
        json.dumps(metadata) if metadata else None,
    )

    # ── Update conversation timestamp + title ────────────────────────────────
    conv_title: str | None = None
    if result.get("intent") == "GOAL" and result.get("goal_draft"):
        for msg in result.get("conversation_history") or []:
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

    raw_options = result.get("options")
    is_clarifier = agent_node_value == "GOAL_CLARIFY"
    resp = ChatMessageResponse(
        conversation_id=str(conv_id),
        message=reply,
        agent_node=agent_node_value,
        proposed_plan=goal_draft if approval_pending else None,
        requires_user_action=approval_pending,
        options=None if is_clarifier else raw_options,
        questions=raw_options if is_clarifier else None,
        rag_used=_rag_used,
        rag_sources=_rag_sources,
    )
    resp.spoken_summary = build_spoken_summary(resp)
    yield f"data: {json.dumps({'type': 'complete', 'data': resp.model_dump(mode='json')})}\n\n"


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
        "options": None,
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
        greeting_options = result.get("options")
        greeting_metadata = (
            json.dumps({"options": greeting_options}) if greeting_options else None
        )
        await db.execute(
            """
            INSERT INTO messages (conversation_id, role, content, agent_node, metadata)
            VALUES ($1, 'assistant', $2, 'ONBOARDING', $3)
            """,
            conv_id,
            greeting,
            greeting_metadata,
        )
        await db.execute(
            "UPDATE conversations SET last_message_at = NOW() WHERE id = $1",
            conv_id,
        )

    return ChatMessageResponse(
        conversation_id=str(conv_id),
        message=greeting
        or "Hi there! I'm Flux, your AI life coach. What should I call you?",
        agent_node="ONBOARDING",
        options=result.get("options"),
    )


@router.get("/history", response_model=ChatHistoryResponse)
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    conversation_id: str | None = Query(
        None, description="UUID of the conversation; omit to get the most recent one"
    ),
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
    cursor: str | None = Query(
        None,
        description="ISO8601 last_message_at of the last item for keyset pagination",
    ),
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
        next_cursor = (
            last["last_message_at"].isoformat() if last["last_message_at"] else None
        )

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

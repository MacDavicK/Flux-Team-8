"""
13. Context Manager (app/services/context_manager.py) — §15

Implements conversation history windowing to stay within token/message limits.
When limits are exceeded, the older half is summarised via a cheap LLM call
and replaced with a single summary message.
"""
from __future__ import annotations

from app.config import settings
from app.services.llm import llm_call
from app.services.supabase import db

_SUMMARY_MODEL = "openrouter/openai/gpt-4o-mini"


def _estimate_tokens(history: list[dict]) -> int:
    """Rough token estimate: 1 token ≈ 4 chars."""
    return sum(len(msg.get("content", "")) for msg in history) // 4


async def window_conversation_history(
    history: list[dict],
    user_id: str,
    conversation_id: str | None = None,
) -> list[dict]:
    """
    13.1 — Check length and token count against config limits.

    If either limit is exceeded:
    13.2 — Split at midpoint, summarise older half via gpt-4o-mini (max 500 tokens).
    13.3 — Return [summary_message] + recent.
    13.4 — Write summary message to messages table with role='summary'.
    """
    msg_limit: int = settings.max_conversation_messages
    tok_limit: int = settings.max_conversation_tokens

    over_messages = len(history) > msg_limit
    over_tokens = _estimate_tokens(history) > tok_limit

    if not (over_messages or over_tokens):
        return history

    # 13.2 — Split at midpoint
    midpoint = len(history) // 2
    older = history[:midpoint]
    recent = history[midpoint:]

    older_text = "\n".join(
        f"{m['role'].upper()}: {m.get('content', '')}" for m in older
    )

    summary_content = await llm_call(
        model=_SUMMARY_MODEL,
        system=(
            "You are a helpful assistant. Summarise the following conversation "
            "segment in 3–5 sentences, preserving all important facts, goals, "
            "and decisions. Be concise."
        ),
        messages=[{"role": "user", "content": older_text}],
        max_tokens=500,
        user_id=user_id,
    )

    summary_message = {"role": "summary", "content": summary_content}

    # 13.4 — Persist summary to messages table if conversation_id provided
    if conversation_id:
        try:
            await db.execute(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES ($1, $2, $3)
                """,
                conversation_id,
                "summary",
                summary_content,
            )
        except Exception:
            pass  # Non-fatal: windowing still works without DB write

    # 13.3 — Return [summary_message] + recent
    return [summary_message] + recent

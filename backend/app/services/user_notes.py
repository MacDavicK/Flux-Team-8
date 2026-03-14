"""
User preference notes service.

Stores and retrieves free-text notes about user habits/constraints that agents
extract from conversational context (e.g. "I go to the gym on Tuesday evenings").

These notes are persisted in the patterns table using pattern_type='user_preference'
and are injected into goal_planner and pattern_observer context so future plans
avoid conflicts and acknowledge existing habits.
"""

from __future__ import annotations

import json

from app.services.supabase import db


async def get_user_notes(user_id: str) -> list[dict]:
    """Return all stored user preference notes for a user, newest first."""
    rows = await db.fetch(
        """
        SELECT id, pattern_key, description, data, confidence, created_at
        FROM patterns
        WHERE user_id = $1 AND pattern_type = 'user_preference'
        ORDER BY created_at DESC
        """,
        user_id,
    )
    return [
        {
            "key": row["pattern_key"],
            "note": row["description"],
            "details": row["data"] or {},
            "confidence": row["confidence"],
        }
        for row in rows
    ]


async def upsert_user_note(
    user_id: str,
    key: str,
    description: str,
    details: dict | None = None,
    confidence: float = 0.9,
) -> None:
    """
    Insert or update a user preference note.

    key        — stable identifier, e.g. "gym_tuesday_evening"
    description — human-readable note, e.g. "Goes to gym on Tuesday evenings around 19:00"
    details    — optional structured data (activity, days, time, duration_minutes)
    confidence — certainty (0–1); default 0.9 for explicit user statements
    """
    existing = await db.fetchrow(
        """
        SELECT id FROM patterns
        WHERE user_id = $1 AND pattern_type = 'user_preference' AND pattern_key = $2
        """,
        user_id,
        key,
    )
    if existing:
        await db.execute(
            """
            UPDATE patterns
            SET description = $1, data = $2::jsonb, confidence = $3, updated_at = now()
            WHERE id = $4
            """,
            description,
            json.dumps(details or {}),
            confidence,
            existing["id"],
        )
    else:
        await db.execute(
            """
            INSERT INTO patterns (user_id, pattern_type, pattern_key, description, data, confidence)
            VALUES ($1, 'user_preference', $2, $3, $4::jsonb, $5)
            """,
            user_id,
            key,
            description,
            json.dumps(details or {}),
            confidence,
        )

"""
Unit tests for save_tasks._row_to_tuple and _parse_dt.

Covers datetime string → datetime object conversion for both
scheduled_at ($6) and canonical_scheduled_at ($14).
"""

from __future__ import annotations

import sys
from datetime import timezone
from unittest.mock import MagicMock

import pendulum

# Stub DB-dependent modules before any app imports.
sys.modules.setdefault("app.services.supabase", MagicMock(db=MagicMock()))
sys.modules.setdefault("app.agents.state", MagicMock())
sys.modules.setdefault("app.agents.pattern_observer", MagicMock())
sys.modules.setdefault("app.services.rrule_expander", MagicMock())

from app.agents.save_tasks import _parse_dt, _row_to_tuple  # noqa: E402

UTC = timezone.utc

# ─────────────────────────────────────────────────────────────────
# _parse_dt
# ─────────────────────────────────────────────────────────────────


def test_parse_dt_iso_string():
    result = _parse_dt("2026-03-23T01:30:00+00:00")
    assert isinstance(result, pendulum.DateTime)
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 23
    assert result.hour == 1
    assert result.minute == 30


def test_parse_dt_passes_through_datetime():
    dt = pendulum.datetime(2026, 3, 23, 9, 0, 0)
    assert _parse_dt(dt) is dt


def test_parse_dt_none_returns_none():
    assert _parse_dt(None) is None


def test_parse_dt_invalid_string_returns_none():
    assert _parse_dt("not-a-date") is None


# ─────────────────────────────────────────────────────────────────
# _row_to_tuple — field positions
# ─────────────────────────────────────────────────────────────────

# Positional mapping (0-indexed):
# 0  user_id
# 1  goal_id
# 2  title
# 3  description
# 4  status
# 5  scheduled_at          ← $6
# 6  duration_minutes
# 7  trigger_type
# 8  location_trigger
# 9  recurrence_rule
# 10 shared_with_goal_ids
# 11 escalation_policy
# 12 conversation_id
# 13 canonical_scheduled_at ← $14


def _make_row(**overrides) -> dict:
    base = {
        "user_id": "user-1",
        "goal_id": None,
        "title": "Test task",
        "description": "",
        "status": "pending",
        "scheduled_at": None,
        "duration_minutes": 30,
        "trigger_type": "time",
        "location_trigger": None,
        "recurrence_rule": None,
        "shared_with_goal_ids": [],
        "escalation_policy": "standard",
        "conversation_id": None,
        "canonical_scheduled_at": None,
    }
    return {**base, **overrides}


def test_scheduled_at_string_is_converted():
    row = _make_row(scheduled_at="2026-03-23T01:30:00+00:00")
    t = _row_to_tuple(row)
    assert isinstance(t[5], pendulum.DateTime), (
        f"scheduled_at should be a datetime, got {type(t[5])}"
    )


def test_canonical_scheduled_at_string_is_converted():
    row = _make_row(canonical_scheduled_at="2026-03-23T01:30:00+00:00")
    t = _row_to_tuple(row)
    assert isinstance(t[13], pendulum.DateTime), (
        f"canonical_scheduled_at should be a datetime, got {type(t[13])}"
    )


def test_both_datetime_fields_converted_from_strings():
    row = _make_row(
        scheduled_at="2026-03-23T09:00:00+00:00",
        canonical_scheduled_at="2026-03-23T01:30:00+00:00",
    )
    t = _row_to_tuple(row)
    assert isinstance(t[5], pendulum.DateTime)
    assert isinstance(t[13], pendulum.DateTime)


def test_datetime_objects_pass_through_unchanged():
    dt_sched = pendulum.datetime(2026, 3, 23, 9, 0, 0)
    dt_canon = pendulum.datetime(2026, 3, 23, 1, 30, 0)
    row = _make_row(scheduled_at=dt_sched, canonical_scheduled_at=dt_canon)
    t = _row_to_tuple(row)
    assert t[5] is dt_sched
    assert t[13] is dt_canon


def test_none_datetime_fields_stay_none():
    row = _make_row(scheduled_at=None, canonical_scheduled_at=None)
    t = _row_to_tuple(row)
    assert t[5] is None
    assert t[13] is None


def test_tuple_length_matches_insert_columns():
    """Tuple must have exactly 14 elements to match the INSERT $1–$14."""
    t = _row_to_tuple(_make_row())
    assert len(t) == 14


def test_defaults_applied_for_missing_fields():
    t = _row_to_tuple({})
    assert t[2] == ""  # title
    assert t[4] == "pending"  # status
    assert t[6] == 30  # duration_minutes
    assert t[7] == "time"  # trigger_type
    assert t[10] == []  # shared_with_goal_ids
    assert t[11] == "standard"  # escalation_policy

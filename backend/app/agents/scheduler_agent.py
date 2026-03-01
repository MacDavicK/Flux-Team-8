"""
Flux Backend — Scheduler Agent

Finds available time slots for drifted tasks and generates reschedule
suggestions with rationale (template-based or LLM-powered).

Slot-Finding Logic:
  1. Load the drifted task (get duration, user_id)
  2. Load user profile (sleep_window, work_hours)
  3. Load existing tasks for today + tomorrow
  4. Build occupied-slot list with buffers
  5. Find free slots that fit the task duration
  6. Return 1–2 best candidates with rationale
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, time, timezone
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import RescheduleSuggestion
from app.services import scheduler_service

logger = logging.getLogger(__name__)

# Default schedule boundaries (used when user has no profile/preferences)
_DEFAULT_SLEEP_START = time(23, 0)   # 11 PM
_DEFAULT_SLEEP_END = time(7, 0)      # 7 AM
_DEFAULT_WORK_START = time(9, 0)     # 9 AM
_DEFAULT_WORK_END = time(18, 0)      # 6 PM
_DEFAULT_WORK_DAYS = {"Mon", "Tue", "Wed", "Thu", "Fri"}

# LLM rationale prompt (used when scheduler_use_llm_rationale=True)
_RATIONALE_SYSTEM_PROMPT = """\
You are Flux, an empathetic scheduling assistant. Given a task that drifted \
(missed its original time) and a proposed new time slot, write a brief, \
warm, 1-sentence rationale for why this slot works.

Be concise. Use a friendly tone. Reference specific reasons like:
- "It's your next free slot today"
- "Morning sessions have your best completion rate"
- "This avoids your usual work hours"

Respond with ONLY the rationale sentence — no JSON, no quotes, no extras.
"""


class SchedulerAgent:
    """Finds free slots for drifted tasks and generates suggestions."""

    def __init__(self):
        self._llm_client: Optional[AsyncOpenAI] = None

    def _get_llm_client(self) -> AsyncOpenAI:
        """Lazy-init the OpenRouter client (same pattern as GoalPlannerAgent)."""
        if self._llm_client is None:
            self._llm_client = AsyncOpenAI(
                api_key=settings.open_router_api_key,
                base_url=settings.openrouter_base_url,
            )
        return self._llm_client

    # ── Public API ──────────────────────────────────────────

    def suggest_slots(self, event_id: str) -> dict:
        """
        Main entry point: find reschedule options for a drifted task.

        Returns dict matching SchedulerSuggestResponse shape.
        """
        # 1. Load the drifted task
        task = scheduler_service.get_task_by_id(event_id)
        if not task:
            raise ValueError(f"Task {event_id} not found")

        if task["state"] != "drifted":
            raise ValueError(
                f"Task {event_id} is '{task['state']}', not 'drifted'. "
                "Only drifted tasks can be rescheduled via suggestions."
            )

        # 2. Calculate task duration from start_time/end_time
        task_start = datetime.fromisoformat(task["start_time"])
        task_end = datetime.fromisoformat(task["end_time"])
        duration = task_end - task_start
        if duration.total_seconds() <= 0:
            duration = timedelta(hours=1)  # safe fallback

        # 3. Load user profile for schedule preferences
        user_profile = scheduler_service.get_user_profile(task["user_id"])
        prefs = (user_profile or {}).get("preferences", {}) or {}

        sleep_window = prefs.get("sleep_window", {})
        work_hours = prefs.get("work_hours", {})

        sleep_start = self._parse_time(sleep_window.get("start"), _DEFAULT_SLEEP_START)
        sleep_end = self._parse_time(sleep_window.get("end"), _DEFAULT_SLEEP_END)
        work_start = self._parse_time(work_hours.get("start"), _DEFAULT_WORK_START)
        work_end = self._parse_time(work_hours.get("end"), _DEFAULT_WORK_END)
        work_days = set(work_hours.get("days", _DEFAULT_WORK_DAYS))

        # 4. Define search windows
        now = datetime.now(timezone.utc)
        today_end = now.replace(
            hour=settings.scheduler_cutoff_hour, minute=0, second=0, microsecond=0
        )
        tomorrow_start = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        tomorrow_end = tomorrow_start + timedelta(days=1)

        # 5. Load existing tasks for conflict detection
        existing_today = scheduler_service.get_tasks_in_range(
            user_id=task["user_id"],
            range_start=now,
            range_end=today_end,
            exclude_task_id=event_id,
        )
        existing_tomorrow = scheduler_service.get_tasks_in_range(
            user_id=task["user_id"],
            range_start=tomorrow_start,
            range_end=tomorrow_end,
            exclude_task_id=event_id,
        )

        # 6. Find free slots
        suggestions: list[RescheduleSuggestion] = []

        # -- Today slots (only if before cutoff hour) --
        if now < today_end:
            today_slots = self._find_free_slots(
                search_start=now + timedelta(minutes=5),
                search_end=today_end,
                duration=duration,
                existing_tasks=existing_today,
                sleep_start=sleep_start,
                sleep_end=sleep_end,
                work_start=work_start,
                work_end=work_end,
                work_days=work_days,
                is_today=True,
            )
            if today_slots:
                slot = today_slots[0]
                suggestions.append(RescheduleSuggestion(
                    new_start=slot["start"],
                    new_end=slot["end"],
                    label=self._format_label(slot["start"], is_today=True),
                    rationale=self._template_rationale(slot, is_today=True),
                ))

        # -- Tomorrow slots (search within tomorrow only, not day-after-tomorrow) --
        tomorrow_search_start = tomorrow_start.replace(
            hour=sleep_end.hour, minute=sleep_end.minute
        )
        tomorrow_search_end = tomorrow_start.replace(
            hour=settings.scheduler_cutoff_hour, minute=0, second=0, microsecond=0
        )
        tomorrow_slots = self._find_free_slots(
            search_start=tomorrow_search_start,
            search_end=tomorrow_search_end,
            duration=duration,
            existing_tasks=existing_tomorrow,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            work_start=work_start,
            work_end=work_end,
            work_days=work_days,
            is_today=False,
            prefer_original_time=task_start.time(),
        )
        if tomorrow_slots:
            slot = tomorrow_slots[0]
            suggestions.append(RescheduleSuggestion(
                new_start=slot["start"],
                new_end=slot["end"],
                label=self._format_label(slot["start"], is_today=False),
                rationale=self._template_rationale(slot, is_today=False),
            ))

        # 7. Build response
        task_title = task.get("title", "Task")
        ai_message = (
            f"{task_title} drifted. I can do:"
            if suggestions
            else f"{task_title} drifted, but I couldn't find open slots today or tomorrow. You can skip for now."
        )

        return {
            "event_id": event_id,
            "task_title": task_title,
            "suggestions": suggestions,
            "skip_option": True,
            "ai_message": ai_message,
        }

    async def suggest_slots_with_llm_rationale(self, event_id: str) -> dict:
        """
        Same as suggest_slots() but replaces template rationale with
        LLM-generated natural language. Activated via config flag.
        Falls back to template rationale if LLM call fails.
        """
        result = self.suggest_slots(event_id)

        if not result["suggestions"]:
            return result

        task_title = result["task_title"]
        for suggestion in result["suggestions"]:
            try:
                llm_rationale = await self._generate_rationale_llm(
                    task_title=task_title,
                    slot_start=suggestion.new_start,
                    slot_end=suggestion.new_end,
                    is_today=(
                        suggestion.new_start.date()
                        == datetime.now(timezone.utc).date()
                    ),
                )
                suggestion.rationale = llm_rationale
            except Exception as e:
                logger.warning(f"LLM rationale failed, keeping template: {e}")

        return result

    # ── Slot-Finding Logic ──────────────────────────────────

    def _find_free_slots(
        self,
        search_start: datetime,
        search_end: datetime,
        duration: timedelta,
        existing_tasks: list[dict],
        sleep_start: time,
        sleep_end: time,
        work_start: time,
        work_end: time,
        work_days: set[str],
        is_today: bool,
        prefer_original_time: Optional[time] = None,
    ) -> list[dict]:
        """
        Scan a time range for free slots that fit the task duration.
        Returns list of {start, end, score, reason} sorted by preference.
        """
        buffer = timedelta(minutes=settings.scheduler_buffer_minutes)

        # Build occupied intervals (with buffer on each side)
        occupied = []
        for t in existing_tasks:
            if not t.get("start_time") or not t.get("end_time"):
                continue
            t_start = datetime.fromisoformat(t["start_time"])
            t_end = datetime.fromisoformat(t["end_time"])
            occupied.append((t_start - buffer, t_end + buffer))

        occupied.sort(key=lambda x: x[0])

        # Scan in 30-minute increments
        candidates = []
        cursor = search_start
        increment = timedelta(minutes=30)

        while cursor + duration <= search_end:
            slot_start = cursor
            slot_end = cursor + duration

            # Skip sleep hours
            if self._is_during_sleep(slot_start, slot_end, sleep_start, sleep_end):
                cursor += increment
                continue

            # Skip conflicting slots
            if self._overlaps_any(slot_start, slot_end, occupied):
                cursor += increment
                continue

            # Score the slot
            day_name = slot_start.strftime("%a")
            is_work_time = (
                day_name in work_days
                and work_start <= slot_start.time() < work_end
            )

            score = 0
            reason = "next free slot"

            if not is_work_time:
                score += 10
                reason = "outside work hours"

            if (
                prefer_original_time
                and abs(
                    self._time_to_minutes(slot_start.time())
                    - self._time_to_minutes(prefer_original_time)
                ) <= 30
            ):
                score += 20
                reason = "same time as originally planned"

            candidates.append({
                "start": slot_start,
                "end": slot_end,
                "score": score,
                "reason": reason,
            })

            cursor += increment

        candidates.sort(key=lambda c: (-c["score"], c["start"]))
        return candidates[:2]

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _parse_time(value: Optional[str], default: time) -> time:
        if not value:
            return default
        try:
            parts = value.split(":")
            return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return default

    @staticmethod
    def _is_during_sleep(
        start: datetime, end: datetime,
        sleep_start: time, sleep_end: time,
    ) -> bool:
        s = start.time()
        if sleep_start > sleep_end:
            return s >= sleep_start or s < sleep_end
        else:
            return sleep_start <= s < sleep_end

    @staticmethod
    def _overlaps_any(
        start: datetime, end: datetime,
        occupied: list[tuple[datetime, datetime]],
    ) -> bool:
        for occ_start, occ_end in occupied:
            if start < occ_end and end > occ_start:
                return True
        return False

    @staticmethod
    def _time_to_minutes(t: time) -> int:
        return t.hour * 60 + t.minute

    @staticmethod
    def _format_label(dt: datetime, is_today: bool) -> str:
        time_str = dt.strftime("%-I:%M %p")
        if is_today:
            return f"{time_str} Today"
        return f"{time_str} {dt.strftime('%A')}"

    @staticmethod
    def _template_rationale(slot: dict, is_today: bool) -> str:
        reason = slot.get("reason", "free slot")
        time_str = slot["start"].strftime("%-I:%M %p")
        if is_today:
            return f"Suggested {time_str} — it's your {reason} today."
        day = slot["start"].strftime("%A")
        return f"Suggested {time_str} {day} — {reason}."

    async def _generate_rationale_llm(
        self,
        task_title: str,
        slot_start: datetime,
        slot_end: datetime,
        is_today: bool,
    ) -> str:
        """Generate natural-language rationale via GPT-4o-mini (OpenRouter)."""
        client = self._get_llm_client()
        time_str = slot_start.strftime("%-I:%M %p")
        day_context = "today" if is_today else slot_start.strftime("%A")

        user_msg = (
            f"Task: {task_title}\n"
            f"Proposed time: {time_str} {day_context}\n"
            f"Duration: {int((slot_end - slot_start).total_seconds() / 60)} minutes\n"
            f"Generate a brief, warm rationale for this reschedule suggestion."
        )

        response = await client.chat.completions.create(
            model=settings.scheduler_model,
            messages=[
                {"role": "system", "content": _RATIONALE_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()

"""
Flux Backend — Onboarding Agent

State-machine agent for the onboarding chat. Collects name, sleep/wake times,
work schedule, chronotype, and commitments; returns a profile dict and
is_complete when done. Aligned to FE-4 contract (POST /api/v1/chat/message).
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# ── State enum (exact strings for frontend placeholders) ───

class OnboardingState(str, Enum):
    ASK_NAME = "ASK_NAME"
    ASK_WAKE_TIME = "ASK_WAKE_TIME"
    ASK_SLEEP_TIME = "ASK_SLEEP_TIME"
    ASK_WORK_SCHEDULE = "ASK_WORK_SCHEDULE"
    ASK_CHRONOTYPE = "ASK_CHRONOTYPE"
    ASK_COMMITMENTS = "ASK_COMMITMENTS"
    COMPLETE = "COMPLETE"


_STATES_ORDER = [
    OnboardingState.ASK_NAME,
    OnboardingState.ASK_WAKE_TIME,
    OnboardingState.ASK_SLEEP_TIME,
    OnboardingState.ASK_WORK_SCHEDULE,
    OnboardingState.ASK_CHRONOTYPE,
    OnboardingState.ASK_COMMITMENTS,
]
TOTAL_STEPS = 7  # 6 questions + COMPLETE


# ── Prompts per state ────────────────────────────────────────

_PROMPTS = {
    OnboardingState.ASK_NAME: "Hey! I'm Flux, your AI life assistant 🚀 What should I call you?",
    OnboardingState.ASK_WAKE_TIME: "Nice to meet you, {name}! What time do you usually wake up?",
    OnboardingState.ASK_SLEEP_TIME: "Got it. And when do you usually go to bed?",
    OnboardingState.ASK_WORK_SCHEDULE: "Do you work during the day? If so, roughly what hours? (If not, just say 'no')",
    OnboardingState.ASK_CHRONOTYPE: "Almost done — are you more of a morning person or a night owl?",
    OnboardingState.ASK_COMMITMENTS: "Last one! Do you have any regular weekly commitments? Like 'Gym on Tuesday evenings' or 'Piano on Saturdays'. List as many as you'd like, or say 'none'.",
    OnboardingState.COMPLETE: "You're all set! 🎉 I now know your schedule. Ready to set your first goal? Just tell me what you'd like to work on.",
}


def _get_prompt(state: OnboardingState, collected: dict[str, Any]) -> str:
    base = _PROMPTS.get(state, "")
    if state == OnboardingState.ASK_WAKE_TIME and collected.get("name"):
        return base.format(name=collected["name"])
    return base


# ── Time parsing (regex → HH:MM) ─────────────────────────────

_TIME_PATTERNS = [
    (re.compile(r"(?i)(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)?"), lambda m: _norm_ampm(int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower())),
    (re.compile(r"(?i)(\d{1,2})\s*(am|pm)\b"), lambda m: _norm_ampm(int(m.group(1)), 0, m.group(2).lower())),
    (re.compile(r"(?i)(\d{1,2})\s+in\s+the\s+morning"), lambda m: _norm_ampm(int(m.group(1)), 0, "am")),
    (re.compile(r"(?i)(\d{1,2})\s+in\s+the\s+(evening|night)"), lambda m: _norm_ampm(int(m.group(1)), 0, "pm")),
    (re.compile(r"(?i)(\d{1,2})\s*:\s*(\d{2})"), lambda m: f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"),
    (re.compile(r"(?i)^(\d{1,2})\s*$"), lambda m: f"{int(m.group(1)):02d}:00"),
]


def _norm_ampm(h: int, min: int, ampm: str) -> str:
    if ampm == "pm" and h != 12:
        h += 12
    elif ampm == "am" and h == 12:
        h = 0
    return f"{h:02d}:{min:02d}"


def _parse_time_to_hhmm(user_input: str) -> str | None:
    s = (user_input or "").strip()
    if not s:
        return None
    for pat, fn in _TIME_PATTERNS:
        m = pat.search(s)
        if m:
            try:
                out = fn(m)
                if isinstance(out, str) and re.match(r"^\d{2}:\d{2}$", out):
                    return out
            except Exception:
                continue
    return None


# ── Work schedule parsing ────────────────────────────────────

_NO_WORK = re.compile(r"^(no|nope|i don't work|none|n/a|no work)$", re.I)


def _parse_work_schedule(user_input: str) -> dict[str, Any] | None:
    s = (user_input or "").strip()
    if not s or _NO_WORK.match(s):
        return None
    # Regex: 9-5, 9am to 6pm, 9:00-18:00
    m = re.search(r"(\d{1,2})(?:\s*:\s*(\d{2}))?\s*(am|pm)?\s*(?:-|to)\s*(\d{1,2})(?:\s*:\s*(\d{2}))?\s*(am|pm)?", s, re.I)
    if m:
        h1, min1, ap1 = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
        h2, min2, ap2 = int(m.group(4)), int(m.group(5) or 0), (m.group(6) or "").lower()
        start = _norm_ampm(h1, min1, ap1 or "am")
        end = _norm_ampm(h2, min2, ap2 or "pm")
        return {"start": start, "end": end, "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]}
    return None


# ── Chronotype keywords ──────────────────────────────────────

def _parse_chronotype(user_input: str) -> str:
    s = (user_input or "").lower().strip()
    if not s:
        return "neutral"
    if any(k in s for k in ("morning", "early", "dawn", "early bird", "lark")):
        return "morning"
    if any(k in s for k in ("night", "evening", "owl", "late", "night owl")):
        return "evening"
    if any(k in s for k in ("both", "neither", "depends", "neutral", "in between")):
        return "neutral"
    return "neutral"


# ── Commitments: "none" → [] ─────────────────────────────────

_COMMITMENTS_NONE = re.compile(r"^(none|no|nothing|nope|no commitments)$", re.I)


def _parse_commitments_none(user_input: str) -> bool:
    return bool((user_input or "").strip() and _COMMITMENTS_NONE.match((user_input or "").strip()))


# ── OnboardingAgent ──────────────────────────────────────────

class OnboardingAgent:
    def __init__(self) -> None:
        self._state = OnboardingState.ASK_NAME
        self._collected: dict[str, Any] = {}
        self._client: AsyncOpenAI | None = None
        self._model = getattr(settings, "onboarding_model", None) or settings.goal_planner_model

    @property
    def current_state(self) -> OnboardingState:
        return self._state

    @property
    def current_step_index(self) -> int:
        try:
            return _STATES_ORDER.index(self._state)
        except ValueError:
            return len(_STATES_ORDER)

    async def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.open_router_api_key,
                base_url=settings.openrouter_base_url,
            )
        return self._client

    async def _ask_llm(self, instruction: str, max_tokens: int = 300) -> str:
        client = await self._get_client()
        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": instruction}],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("Onboarding LLM call failed: %s", e)
            return ""

    async def _parse_time_llm(self, user_input: str) -> str | None:
        out = await self._ask_llm(
            f"Parse this time input into 24-hour HH:MM format. Input: '{user_input}'. "
            "Respond with ONLY the time in HH:MM format, nothing else.",
            max_tokens=20,
        )
        if out and re.match(r"^\d{1,2}:\d{2}$", out):
            h, m = out.split(":")
            return f"{int(h):02d}:{int(m):02d}"
        return None

    async def _parse_work_llm(self, user_input: str) -> dict[str, Any] | None:
        out = await self._ask_llm(
            f"Parse this work schedule. Input: '{user_input}'. "
            'Respond with JSON only: {"start":"HH:MM","end":"HH:MM","days":["Mon",...]}. '
            "If the person doesn't work, respond with: null",
            max_tokens=150,
        )
        if not out or "null" in out.lower():
            return None
        try:
            # Extract JSON from response
            start = out.find("{")
            if start >= 0:
                obj = json.loads(out[start : out.rfind("}") + 1])
                return {
                    "start": obj.get("start", "09:00"),
                    "end": obj.get("end", "17:00"),
                    "days": obj.get("days", ["Mon", "Tue", "Wed", "Thu", "Fri"]),
                }
        except Exception:
            pass
        return None

    async def _parse_commitments_llm(self, user_input: str) -> list[dict[str, Any]]:
        out = await self._ask_llm(
            "Parse these weekly commitments into structured JSON. "
            f"Input: '{user_input}'\n"
            "Respond with ONLY a JSON array: "
            '[{"title":"string","days":["Monday"],"time":"HH:MM","duration_minutes":60}]. '
            "Use best estimates for duration if not specified. Return [] if no commitments.",
            max_tokens=400,
        )
        if not out:
            return []
        try:
            start = out.find("[")
            if start >= 0:
                arr = json.loads(out[start : out.rfind("]") + 1])
                result = []
                for item in arr if isinstance(arr, list) else []:
                    if isinstance(item, dict) and item.get("title"):
                        result.append({
                            "title": str(item["title"]),
                            "days": [str(d) for d in item.get("days", [])],
                            "time": str(item.get("time", "09:00")),
                            "duration_minutes": int(item.get("duration_minutes", 60)),
                        })
                return result
        except Exception:
            pass
        return []

    def _build_profile(self) -> dict[str, Any]:
        name = self._collected.get("name", "")
        wake = self._collected.get("wake_time", "07:00")
        sleep = self._collected.get("sleep_time", "23:00")
        work = self._collected.get("work_schedule")
        chronotype = self._collected.get("chronotype", "neutral")
        commitments = self._collected.get("existing_commitments") or []
        return {
            "name": name,
            "sleep_window": {"start": sleep, "end": wake},
            "work_hours": work,
            "chronotype": chronotype,
            "existing_commitments": commitments,
        }

    async def process_message(self, message: str) -> dict[str, Any]:
        """
        Process one user message. Returns dict with:
          message, state (str), progress (float), is_complete (bool), profile (dict | None).
        """
        # Resume: empty string → re-send current prompt
        if (message or "").strip() == "":
            prompt = _get_prompt(self._state, self._collected)
            idx = self.current_step_index
            return {
                "message": prompt,
                "state": self._state.value,
                "progress": idx / TOTAL_STEPS,
                "is_complete": False,
                "profile": None,
            }

        if self._state == OnboardingState.ASK_NAME:
            name = (message or "").strip()
            if name:
                name = name[0].upper() + name[1:].lower()
            self._collected["name"] = name or "there"
            self._state = OnboardingState.ASK_WAKE_TIME
            prompt = _get_prompt(self._state, self._collected)
            return {
                "message": prompt,
                "state": self._state.value,
                "progress": 1 / TOTAL_STEPS,
                "is_complete": False,
                "profile": None,
            }

        if self._state == OnboardingState.ASK_WAKE_TIME:
            parsed = _parse_time_to_hhmm(message)
            if parsed is None:
                parsed = await self._parse_time_llm(message)
            self._collected["wake_time"] = parsed or "07:00"
            self._state = OnboardingState.ASK_SLEEP_TIME
            prompt = _get_prompt(self._state, self._collected)
            return {
                "message": prompt,
                "state": self._state.value,
                "progress": 2 / TOTAL_STEPS,
                "is_complete": False,
                "profile": None,
            }

        if self._state == OnboardingState.ASK_SLEEP_TIME:
            parsed = _parse_time_to_hhmm(message)
            if parsed is None:
                parsed = await self._parse_time_llm(message)
            self._collected["sleep_time"] = parsed or "23:00"
            self._state = OnboardingState.ASK_WORK_SCHEDULE
            prompt = _get_prompt(self._state, self._collected)
            return {
                "message": prompt,
                "state": self._state.value,
                "progress": 3 / TOTAL_STEPS,
                "is_complete": False,
                "profile": None,
            }

        if self._state == OnboardingState.ASK_WORK_SCHEDULE:
            work = _parse_work_schedule(message)
            if work is None:
                work = await self._parse_work_llm(message)
            self._collected["work_schedule"] = work
            self._state = OnboardingState.ASK_CHRONOTYPE
            prompt = _get_prompt(self._state, self._collected)
            return {
                "message": prompt,
                "state": self._state.value,
                "progress": 4 / TOTAL_STEPS,
                "is_complete": False,
                "profile": None,
            }

        if self._state == OnboardingState.ASK_CHRONOTYPE:
            self._collected["chronotype"] = _parse_chronotype(message)
            self._state = OnboardingState.ASK_COMMITMENTS
            prompt = _get_prompt(self._state, self._collected)
            return {
                "message": prompt,
                "state": self._state.value,
                "progress": 5 / TOTAL_STEPS,
                "is_complete": False,
                "profile": None,
            }

        if self._state == OnboardingState.ASK_COMMITMENTS:
            if _parse_commitments_none(message):
                self._collected["existing_commitments"] = []
            else:
                self._collected["existing_commitments"] = await self._parse_commitments_llm(message)
            self._state = OnboardingState.COMPLETE
            prompt = _get_prompt(self._state, self._collected)
            profile = self._build_profile()
            return {
                "message": prompt,
                "state": self._state.value,
                "progress": 1.0,
                "is_complete": True,
                "profile": profile,
            }

        # Already COMPLETE — shouldn't normally reach here
        prompt = _get_prompt(OnboardingState.COMPLETE, self._collected)
        return {
            "message": prompt,
            "state": OnboardingState.COMPLETE.value,
            "progress": 1.0,
            "is_complete": True,
            "profile": self._build_profile(),
        }

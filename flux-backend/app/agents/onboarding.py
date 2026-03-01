"""
9.6 — Onboarding node for Flux (§12).

Conducts a conversational onboarding flow (10 data-collection questions + first-goal
transition) entirely via the chat interface.  The orchestrator routes here whenever
users.onboarded = false.

Step tracking uses special underscore-prefixed keys inside user_profile (persisted by
the LangGraph checkpointer), so partial onboarding can be resumed across reconnects.
"""

import json
from typing import Any, Optional

from pydantic import BaseModel

from app.agents.state import AgentState
from app.services.llm import validated_llm_call
from app.services.supabase import db

# ─────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────

_MODEL = "openrouter/openai/gpt-4o"

# ─────────────────────────────────────────────────────────────────
# Step definitions
#
# Each entry is (step_name, tracking_key).
# tracking_key is the key written to user_profile to mark the step done.
# 9.6.2 — Presence of tracking_key in profile means that step is answered.
# ─────────────────────────────────────────────────────────────────

_STEPS: list[tuple[str, str]] = [
    ("name",                 "name"),
    ("wake_time",            "_wake_collected"),
    ("sleep_time",           "_sleep_collected"),
    ("work_hours",           "work_hours"),
    ("chronotype",           "chronotype"),
    ("timezone",             "_timezone_confirmed"),
    ("locations",            "locations"),
    ("existing_commitments", "_commitments_answered"),
    ("phone_number",         "_phone_collected"),
    ("whatsapp_opt_in",      "_whatsapp_answered"),
]

# ─────────────────────────────────────────────────────────────────
# LLM output model
# ─────────────────────────────────────────────────────────────────


class _OnboardingExtract(BaseModel):
    """Structured extraction + assistant reply for one onboarding turn."""

    extracted_value: Any  # null when user's message doesn't answer the current step
    reply: str  # warm natural-language message to show the user
    phone_number_e164: Optional[str] = None  # set when step == phone_number
    whatsapp_opted_in: Optional[bool] = None  # set when step == whatsapp_opt_in


# ─────────────────────────────────────────────────────────────────
# Per-step extraction instructions (injected into the system prompt)
# ─────────────────────────────────────────────────────────────────

_STEP_INSTRUCTIONS: dict[str, str] = {
    "name": (
        'Ask: "What should I call you?" '
        "Extract the user's name as a plain string."
    ),
    "wake_time": (
        'Ask: "What time do you usually wake up?" '
        'Extract as HH:MM (24-hour). e.g. "7am" → "07:00", "7:30 AM" → "07:30".'
    ),
    "sleep_time": (
        'Ask: "What time do you usually go to bed?" '
        'Extract as HH:MM (24-hour). e.g. "11pm" → "23:00".'
    ),
    "work_hours": (
        'Ask: "Do you work during the day? If so, roughly what hours and which days?" '
        "Extract as {\"start\": \"HH:MM\", \"end\": \"HH:MM\", \"days\": [\"Mon\",\"Tue\",...]}. "
        "If user doesn't work, use {\"start\": null, \"end\": null, \"days\": []}."
    ),
    "chronotype": (
        'Ask: "Are you more of a morning person or a night owl?" '
        'Extract as exactly one of: "morning", "evening", "neutral".'
    ),
    "timezone": (
        'Tell the user their detected timezone and ask them to confirm. '
        'e.g. "I see you\'re in {timezone} — is that right?" '
        "If confirmed, extracted_value = the timezone string. "
        "If the user corrects it, extracted_value = the corrected IANA timezone string."
    ),
    "locations": (
        'Ask: "What should I call your home location? (e.g., \'Home\', \'Apartment\')" '
        'Extract as {"home": "<label>"}.'
    ),
    "existing_commitments": (
        'Ask: "Any regular commitments I should know about? (e.g., gym on Tuesday evenings) '
        "Or just say 'none' if you don't have any.\" "
        "Extract as a list of {\"title\": str, \"days\": [str], \"time\": \"HH:MM\", \"duration_minutes\": int}. "
        "If none, extract []."
    ),
    "phone_number": (
        'Ask: "What\'s your phone number? I\'ll use it to send you reminders if you don\'t '
        "respond in the app. (Include country code, e.g., +1 555-123-4567)\" "
        "Extract the E.164 number into phone_number_e164. Set extracted_value = true once a valid number is given."
    ),
    "whatsapp_opt_in": (
        'Ask: "Can I also reach you on WhatsApp at this number? (yes / no)" '
        "Extract boolean into whatsapp_opted_in. Set extracted_value = true once the user has answered."
    ),
}

# ─────────────────────────────────────────────────────────────────
# System prompt template
# ─────────────────────────────────────────────────────────────────

_SYSTEM_TEMPLATE = """\
You are Flux, a warm and encouraging AI life coach. You are conducting a first-time
onboarding conversation with a new user.

CURRENT ONBOARDING STEP: {step}
PROFILE COLLECTED SO FAR: {profile_json}
USER'S DETECTED TIMEZONE: {timezone}

STEP INSTRUCTIONS:
{step_instructions}

GENERAL RULES:
- Extract the user's answer to the CURRENT STEP from their latest message.
- If their message does not clearly answer the current step (e.g. it's a greeting or
  off-topic), set extracted_value = null and gently ask the step's question.
- Keep replies brief, warm, and encouraging. Use the user's name if already known.
- ONLY respond with valid JSON — no markdown fences, no extra prose.

RETURN THIS JSON SCHEMA EXACTLY:
{{
  "extracted_value": <extracted data or null>,
  "reply": "<your message to the user>",
  "phone_number_e164": "<E.164 phone string or null>",
  "whatsapp_opted_in": <true / false / null>
}}"""


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────


def _current_step(profile: dict) -> Optional[str]:
    """Return the name of the first unanswered step, or None when all done."""
    for step, key in _STEPS:
        if key not in profile:
            return step
    return None


def _apply_extraction(
    profile: dict, step: str, value: Any, result: _OnboardingExtract
) -> dict:
    """Merge the LLM-extracted value into the profile dict and set the tracking key."""
    p = dict(profile)
    if value is None:
        return p  # Nothing extracted; profile unchanged; step repeats next turn.

    if step == "name":
        p["name"] = str(value)
    elif step == "wake_time":
        p["wake_time"] = str(value)
        p["_wake_collected"] = True
    elif step == "sleep_time":
        p["sleep_time"] = str(value)
        p["_sleep_collected"] = True
    elif step == "work_hours":
        p["work_hours"] = value
    elif step == "chronotype":
        p["chronotype"] = str(value)
    elif step == "timezone":
        p["timezone"] = str(value)
        p["_timezone_confirmed"] = True
    elif step == "locations":
        p["locations"] = value if isinstance(value, dict) else {"home": str(value)}
    elif step == "existing_commitments":
        p["existing_commitments"] = value if isinstance(value, list) else []
        p["_commitments_answered"] = True
    elif step == "phone_number":
        if result.phone_number_e164:
            p["phone_number"] = result.phone_number_e164
        p["_phone_collected"] = True
    elif step == "whatsapp_opt_in":
        p["whatsapp_opt_in"] = bool(result.whatsapp_opted_in)
        p["_whatsapp_answered"] = True

    return p


def _build_final_profile(p: dict) -> dict:
    """
    9.6.5 — Produce the clean profile JSON to be written to users.profile.
    Internal underscore-prefixed tracking keys are stripped out.
    """
    return {
        "name": p.get("name", ""),
        "sleep_window": {
            "start": p.get("sleep_time", "23:00"),
            "end": p.get("wake_time", "07:00"),
        },
        "work_hours": p.get("work_hours") or {
            "start": "09:00",
            "end": "18:00",
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        },
        "chronotype": p.get("chronotype", "neutral"),
        "existing_commitments": p.get("existing_commitments") or [],
        "locations": p.get("locations") or {"home": "Home"},
    }


async def _seed_commitment_task(user_id: str, commitment: dict) -> None:
    """
    9.6.6 — Insert a recurring task row for a pre-existing commitment.
    Uses FREQ=WEEKLY RRULE; scheduled_at is left null (no specific date expansion).
    """
    _day_map = {
        "Monday": "MO", "Tuesday": "TU", "Wednesday": "WE",
        "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU",
        "Mon": "MO", "Tue": "TU", "Wed": "WE", "Thu": "TH",
        "Fri": "FR", "Sat": "SA", "Sun": "SU",
    }
    days = commitment.get("days") or []
    byday = ",".join(_day_map[d] for d in days if d in _day_map)
    rrule = f"FREQ=WEEKLY;BYDAY={byday}" if byday else "FREQ=WEEKLY"

    await db.execute(
        """
        INSERT INTO tasks (
            user_id, title, description,
            status, trigger_type, recurrence_rule, duration_minutes
        ) VALUES ($1, $2, $3, 'pending', 'time', $4, $5)
        """,
        user_id,
        commitment.get("title", "Commitment"),
        f"Pre-seeded from onboarding: {commitment.get('title', '')}",
        rrule,
        commitment.get("duration_minutes", 60),
    )


async def _complete_onboarding(
    user_id: str, profile: dict, history: list[dict]
) -> dict:
    """
    Called when all onboarding steps have been answered.

    9.6.5 — Writes final profile JSON to users.profile; sets onboarded=true and timezone.
    9.6.6 — Pre-seeds existing_commitments as task rows.
    9.6.7 — Returns intent=None so the orchestrator handles the next user message
             (the user's first goal) through the normal routing path.
    """
    final_profile = _build_final_profile(profile)
    timezone = profile.get("timezone", "UTC")
    name = final_profile.get("name", "")

    # 9.6.5 — Persist profile, mark onboarded, set timezone
    await db.execute(
        """
        UPDATE users
        SET profile    = $1::jsonb,
            onboarded  = true,
            timezone   = $2,
            updated_at = now()
        WHERE id = $3
        """,
        json.dumps(final_profile),
        timezone,
        user_id,
    )

    # 9.6.6 — Pre-seed existing commitments as recurring task rows
    for commitment in final_profile.get("existing_commitments") or []:
        try:
            await _seed_commitment_task(user_id, commitment)
        except Exception:
            pass  # Non-fatal; user can add commitments manually later

    # Transition prompt: Q11 from §12 — "what's your first goal?"
    first_goal_prompt = (
        f"Great{', ' + name if name else ''}! You're all set. "
        "Now, what's the first thing you'd like to work on?"
    )

    # 9.6.7 — Clear intent so orchestrator handles the next message normally
    return {
        "conversation_history": history + [
            {"role": "assistant", "content": first_goal_prompt}
        ],
        "user_profile": final_profile,
        "intent": None,
    }


# ─────────────────────────────────────────────────────────────────
# 9.6.1 — Main onboarding node
# ─────────────────────────────────────────────────────────────────


async def onboarding_node(state: AgentState) -> dict:
    """
    Conversational onboarding node (§12).

    Called by LangGraph on every turn while users.onboarded = false.
    Persists partial answers in user_profile via LangGraph checkpointing so
    the session can be resumed if the user disconnects mid-onboarding.
    """
    user_id: str = state["user_id"]
    profile: dict = dict(state.get("user_profile") or {})
    history: list[dict] = list(state.get("conversation_history") or [])

    # 9.6.2 — Determine first unanswered step
    step = _current_step(profile)

    # All steps already complete (e.g. resumed after DB write but before onboarded flag
    # propagated); re-trigger completion write and show transition prompt.
    if step is None:
        return await _complete_onboarding(user_id, profile, history)

    # If there's no user message to extract from, just ask the first question.
    # This handles both the very first turn and resumed sessions where the last
    # persisted message was from the assistant.
    last_role = history[-1]["role"] if history else "assistant"
    if not history or last_role == "assistant":
        question = await _ask_question(step, profile)
        return {
            "conversation_history": history + [
                {"role": "assistant", "content": question}
            ],
            "user_profile": profile,
            "intent": "ONBOARDING",
        }

    # Build per-step system prompt
    timezone = profile.get("timezone", "UTC")
    step_instructions = _STEP_INSTRUCTIONS[step].replace("{timezone}", timezone)
    system = _SYSTEM_TEMPLATE.format(
        step=step,
        profile_json=json.dumps(
            {k: v for k, v in profile.items() if not k.startswith("_")}
        ),
        timezone=timezone,
        step_instructions=step_instructions,
    )

    # LLM call: extract answer + generate reply
    try:
        result: _OnboardingExtract = await validated_llm_call(
            model=_MODEL,
            system_prompt=system,
            messages=history,
            output_model=_OnboardingExtract,
            max_tokens=512,
            user_id=user_id,
        )
    except ValueError:
        fallback = "Sorry, I had a hiccup there. Could you try again?"
        return {
            "conversation_history": history + [
                {"role": "assistant", "content": fallback}
            ],
            "user_profile": profile,
            "intent": "ONBOARDING",
        }

    # Apply extracted answer to profile (step advances only when value is non-null)
    profile = _apply_extraction(profile, step, result.extracted_value, result)

    # 9.6.3 — Phone number collected: fire OTP send (non-blocking; failure is non-fatal)
    if step == "phone_number" and result.phone_number_e164:
        try:
            from app.services.twilio_service import send_otp  # noqa: PLC0415
            await send_otp(result.phone_number_e164)
        except Exception:
            pass  # User can verify phone via POST /account/phone/verify/send later

    # 9.6.4 — WhatsApp opt-in: persist timestamp immediately
    if step == "whatsapp_opt_in" and result.whatsapp_opted_in:
        await db.execute(
            "UPDATE users SET whatsapp_opt_in_at = now() WHERE id = $1",
            user_id,
        )

    updated_history = history + [{"role": "assistant", "content": result.reply}]

    # Check if all steps are now complete after this extraction
    if _current_step(profile) is None:
        return await _complete_onboarding(user_id, profile, updated_history)

    return {
        "conversation_history": updated_history,
        "user_profile": profile,
        "intent": "ONBOARDING",
    }


async def _ask_question(step: str, profile: dict) -> str:
    """
    Return a static fallback question string for the given step.
    Used on the very first turn (no user message yet) and on session resume.
    """
    name = profile.get("name", "")
    timezone = profile.get("timezone", "your timezone")

    _questions: dict[str, str] = {
        "name": (
            "Hi there! I'm Flux, your AI life coach. I'll help you build habits that "
            "actually stick. Let's get you set up — what should I call you?"
        ),
        "wake_time": f"Nice to meet you{', ' + name if name else ''}! What time do you usually wake up?",
        "sleep_time": "And what time do you usually go to bed?",
        "work_hours": (
            "Do you work during the day? If so, roughly what hours and which days? "
            "(e.g., Mon–Fri 9 to 6)"
        ),
        "chronotype": "Are you more of a morning person or a night owl?",
        "timezone": f"I see you're in {timezone} — is that right?",
        "locations": "What should I call your home location? (e.g., 'Home', 'Apartment')",
        "existing_commitments": (
            "Any regular commitments I should know about? "
            "(e.g., gym on Tuesday evenings) Or say 'none' if not."
        ),
        "phone_number": (
            "What's your phone number? I'll use it to send you reminders if you don't "
            "respond in the app. (Include country code, e.g., +1 555-123-4567)"
        ),
        "whatsapp_opt_in": "Can I also reach you on WhatsApp at this number? (yes / no)",
    }
    return _questions.get(step, "Let's continue with your setup.")

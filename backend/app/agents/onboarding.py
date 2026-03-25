"""
9.6 — Onboarding node for Flux (§12).

Conducts a conversational onboarding flow via the chat interface.
The orchestrator routes here whenever users.onboarded = false.

All answers arrive either as quick-select option values or as validated
free-text from the frontend (Zod-validated before sending). No LLM is used
here — every step is handled by direct string passthrough or the fast-path
quick-select matcher.

Step tracking uses special underscore-prefixed keys inside user_profile
(persisted by the LangGraph checkpointer), so partial onboarding can be
resumed across reconnects.
"""

from typing import Any, Optional

from pydantic import BaseModel

from app.agents.state import AgentState
from app.services.supabase import db

# ─────────────────────────────────────────────────────────────────
# Work-minutes parser — converts natural-language work schedule to
# a per-day-of-week minute map used by the congestion check.
# ─────────────────────────────────────────────────────────────────

_WORK_MINUTES_FALLBACK: dict[str, int] = {
    "mon": 480,
    "tue": 480,
    "wed": 480,
    "thu": 480,
    "fri": 480,
    "sat": 0,
    "sun": 0,
}


class _WorkMinutesByDay(BaseModel):
    mon: int
    tue: int
    wed: int
    thu: int
    fri: int
    sat: int
    sun: int


async def _parse_work_minutes_by_day(work_hours: str) -> dict[str, int]:
    """
    Convert a natural-language work schedule string into a per-day minute map.

    Examples:
      "9 AM to 5 PM, Monday to Friday"  → {"mon": 480, ..., "sat": 0, "sun": 0}
      "I don't work set hours"           → all zeros
      "Flexible hours, mostly weekdays"  → moderate estimate Mon–Fri

    Uses a single structured LLM call (gpt-4o-mini). Never raises — falls back
    to 480 min Mon–Fri on any error. Called once at end of onboarding and lazily
    by ask_start_date_node for pre-feature users missing work_minutes_by_day.
    """
    from app.services.llm import validated_llm_call  # noqa: PLC0415 — lazy import

    _SYSTEM = (
        "You convert a natural-language work schedule description into exact minutes "
        "worked per day of the week. Return a JSON object with keys: "
        "mon, tue, wed, thu, fri, sat, sun — each an integer number of minutes. "
        "For 'I don't work set hours' or similar, return all zeros. "
        "For flexible/remote schedules estimate conservatively (e.g. 360 min weekdays). "
        "Return only the JSON object, no explanation."
    )
    try:
        result = await validated_llm_call(
            model="openrouter/openai/gpt-4o-mini",
            system_prompt=_SYSTEM,
            messages=[
                {"role": "user", "content": work_hours or "standard office hours"}
            ],
            output_model=_WorkMinutesByDay,
            max_tokens=128,
            max_retries=1,
        )
        return result.model_dump()
    except Exception:
        return dict(_WORK_MINUTES_FALLBACK)


# ─────────────────────────────────────────────────────────────────
# Quick-select option definitions
#
# Each option has a label (shown to user) and a value (sent as the
# message when selected). The last option with value=None is the
# "Specify" sentinel — the frontend opens a validated text input.
# zod_validator is a Zod schema string for the "Specify" input;
# it is only set on the Specify option.
# ─────────────────────────────────────────────────────────────────


class OnboardingOption(BaseModel):
    label: str
    value: Optional[str] = None  # None = "Specify" — opens free-text input
    zod_validator: Optional[str] = None  # Zod schema string for the Specify input
    input_type: Optional[str] = None  # "otp" signals the frontend OTP widget


# Per-step quick-select options. None means no quick options for that step.
_STEP_OPTIONS: dict[str, Optional[list[OnboardingOption]]] = {
    "name": [
        OnboardingOption(
            label="Specify",
            value=None,
            zod_validator='z.string().min(1, "Please enter your name").max(50, "Keep it under 50 characters")',
        ),
    ],
    "wake_time": [
        OnboardingOption(label="5:30 AM", value="05:30"),
        OnboardingOption(label="6 AM", value="06:00"),
        OnboardingOption(label="6:30 AM", value="06:30"),
        OnboardingOption(label="7 AM", value="07:00"),
        OnboardingOption(label="7:30 AM", value="07:30"),
        OnboardingOption(label="8 AM", value="08:00"),
        OnboardingOption(
            label="Specify",
            value=None,
            zod_validator=(
                "z.string().regex(/^(0?[1-9]|1[0-2]):[0-5][0-9]\\s?(AM|PM)$/i, "
                '"Enter a time like 7:30 AM")'
            ),
        ),
    ],
    "sleep_time": [
        OnboardingOption(label="9 PM", value="21:00"),
        OnboardingOption(label="10 PM", value="22:00"),
        OnboardingOption(label="10:30 PM", value="22:30"),
        OnboardingOption(label="11 PM", value="23:00"),
        OnboardingOption(label="11:30 PM", value="23:30"),
        OnboardingOption(label="12 AM (midnight)", value="00:00"),
        OnboardingOption(label="1 AM", value="01:00"),
        OnboardingOption(
            label="Specify",
            value=None,
            zod_validator=(
                "z.string().regex(/^(0?[1-9]|1[0-2]):[0-5][0-9]\\s?(AM|PM)$/i, "
                '"Enter a time like 11:30 PM")'
            ),
        ),
    ],
    "work_hours": [
        OnboardingOption(
            label="9 AM – 5 PM, Mon–Fri", value="9 AM to 5 PM, Monday to Friday"
        ),
        OnboardingOption(
            label="10 AM – 6 PM, Mon–Fri", value="10 AM to 6 PM, Monday to Friday"
        ),
        OnboardingOption(
            label="Flexible / remote", value="Flexible hours, mostly weekdays"
        ),
        OnboardingOption(
            label="I don't work set hours", value="I don't work set hours"
        ),
        OnboardingOption(
            label="Specify",
            value=None,
            zod_validator='z.string().min(3, "Please describe your work hours")',
        ),
    ],
    "chronotype": [
        OnboardingOption(label="Morning person", value="morning"),
        OnboardingOption(label="Night owl", value="evening"),
        OnboardingOption(label="Somewhere in between", value="neutral"),
    ],
    "phone_number": [
        OnboardingOption(
            label="Specify",
            value=None,
            zod_validator=(
                "z.string().regex(/^\\+[1-9]\\d{1,14}$/, "
                '"Enter your number in international format, e.g. +15551234567")'
            ),
        ),
        OnboardingOption(
            label="Skip — I'll set SMS/WhatsApp notifications up later",
            value="__skip_phone__",
        ),
    ],
    "whatsapp_opt_in": [
        OnboardingOption(label="Yes", value="Yes"),
        OnboardingOption(label="No", value="No"),
    ],
    "otp_verification": [
        OnboardingOption(
            label="Enter verification code",
            value=None,
            zod_validator='z.string().regex(/^\\d{6}$/, "Enter the 6-digit code from your SMS")',
            input_type="otp",
        ),
    ],
}

# ─────────────────────────────────────────────────────────────────
# Step definitions
#
# Each entry is (step_name, tracking_key).
# tracking_key is the key written to user_profile to mark the step done.
# 9.6.2 — Presence of tracking_key in profile means that step is answered.
# ─────────────────────────────────────────────────────────────────

_STEPS: list[tuple[str, str]] = [
    ("name", "name"),
    ("wake_time", "_wake_collected"),
    ("sleep_time", "_sleep_collected"),
    ("work_hours", "work_hours"),
    ("chronotype", "chronotype"),
    ("phone_number", "_phone_collected"),
    ("otp_verification", "_otp_done"),
    ("whatsapp_opt_in", "_whatsapp_answered"),
]

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────


def _current_step(profile: dict) -> Optional[str]:
    """Return the name of the first unanswered step, or None when all done."""
    for step, key in _STEPS:
        if key not in profile:
            return step
    return None


def _parse_time_to_24h(value: str) -> str:
    """
    Convert a time string to HH:MM 24-hour format.

    Quick-select values arrive already in HH:MM and pass through unchanged.
    Specify inputs match the zod regex: '7:30 AM', '11:30 PM', etc.
    """
    import re

    # Already HH:MM (quick-select)
    if len(value) <= 5 and ":" in value and value.replace(":", "").isdigit():
        return value

    m = re.match(
        r"^(0?[1-9]|1[0-2]):([0-5][0-9])\s?(AM|PM)$", value.strip(), re.IGNORECASE
    )
    if m:
        hour, minute, period = int(m.group(1)), int(m.group(2)), m.group(3).upper()
        if period == "AM":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12
        return f"{hour:02d}:{minute:02d}"

    return value  # Fallback — shouldn't happen given frontend validation


def _apply_extraction(profile: dict, step: str, value: Any) -> dict:
    """Merge the answer into the profile dict and set the tracking key."""
    p = dict(profile)
    if value is None:
        return p

    if step == "name":
        p["name"] = str(value)
    elif step == "wake_time":
        p["wake_time"] = _parse_time_to_24h(str(value))
        p["_wake_collected"] = True
    elif step == "sleep_time":
        p["sleep_time"] = _parse_time_to_24h(str(value))
        p["_sleep_collected"] = True
    elif step == "work_hours":
        p["work_hours"] = str(value)
    elif step == "chronotype":
        p["chronotype"] = str(value)
    elif step == "phone_number":
        if str(value) == "__skip_phone__":
            # User chose to skip phone setup — mark all three phone steps done
            p["_phone_collected"] = True
            p["_otp_done"] = True
            p["_whatsapp_answered"] = True
        else:
            p["phone_number"] = str(value)  # Already E.164 from frontend validation
            p["_phone_collected"] = True
            # Reset OTP attempt counter so a re-entered number gets a fresh 3 attempts
            p.pop("_otp_attempts", None)
    elif step == "otp_verification":
        # OTP result is set by onboarding_node after async confirm_otp call
        p["_otp_verified"] = True
        p["_otp_done"] = True
    elif step == "whatsapp_opt_in":
        p["whatsapp_opt_in"] = value == "Yes"
        p["_whatsapp_answered"] = True

    return p


def _build_final_profile(p: dict) -> dict:
    """
    9.6.5 — Produce the clean profile JSON to be written to users.profile.
    Internal underscore-prefixed tracking keys are stripped out.
    work_minutes_by_day is populated separately by _complete_onboarding.
    """
    return {
        "name": p.get("name", ""),
        "sleep_window": {
            "start": p.get("sleep_time", "23:00"),
            "end": p.get("wake_time", "07:00"),
        },
        "work_hours": p.get("work_hours") or "9 AM to 5 PM, Monday to Friday",
        "chronotype": p.get("chronotype", "neutral"),
        "timezone": p.get("timezone", "UTC"),
    }


def _build_final_notification_preferences(p: dict) -> dict:
    """
    9.6.5 — Produce the notification_preferences JSON from onboarding answers.
    """
    prefs: dict = {}
    if p.get("phone_number"):
        prefs["phone_number"] = p["phone_number"]
    if p.get("whatsapp_opt_in"):
        prefs["whatsapp_opted_in"] = True
    return prefs


async def _complete_onboarding(
    user_id: str, profile: dict, history: list[dict]
) -> dict:
    """
    Called when all onboarding steps have been answered.

    9.6.5 — Writes final profile + notification_preferences in a single query;
             sets onboarded=true, timezone, and whatsapp_opt_in_at if applicable.
    9.6.7 — Returns intent=None so the orchestrator handles the next user message
             (the user's first goal) through the normal routing path.
    """
    import json as _json

    final_profile = _build_final_profile(profile)
    # Parse work schedule into per-day minute map for the congestion check.
    work_minutes = await _parse_work_minutes_by_day(final_profile.get("work_hours", ""))
    final_profile["work_minutes_by_day"] = work_minutes
    notif_prefs = _build_final_notification_preferences(profile)
    timezone = profile.get("timezone", "UTC")
    name = final_profile.get("name", "")
    whatsapp_opted_in = profile.get("whatsapp_opt_in", False)

    await db.execute(
        """
        UPDATE users
        SET profile                  = $1::jsonb,
            notification_preferences = COALESCE(notification_preferences, '{}'::jsonb) || $2::jsonb,
            onboarded                = true,
            timezone                 = $3,
            whatsapp_opt_in_at       = CASE WHEN $4 THEN now() ELSE whatsapp_opt_in_at END,
            updated_at               = now()
        WHERE id = $5
        """,
        _json.dumps(final_profile),
        _json.dumps(notif_prefs),
        timezone,
        whatsapp_opted_in,
        user_id,
    )

    # Transition prompt: Q11 from §12 — "what's your first goal?"
    first_goal_prompt = (
        f"Great{', ' + name if name else ''}! You're all set. "
        "Now, what's the first thing you'd like to work on?"
    )

    # 9.6.7 — Clear intent so orchestrator handles the next message normally
    return {
        "conversation_history": history
        + [{"role": "assistant", "content": first_goal_prompt}],
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

    No LLM is used. Every answer comes in as a quick-select value or as a
    Zod-validated free-text string — the node applies it directly and advances.
    """
    user_id: str = state["user_id"]
    profile: dict = dict(state.get("user_profile") or {})
    history: list[dict] = list(state.get("conversation_history") or [])

    # 9.6.2 — Determine first unanswered step
    step = _current_step(profile)

    # All steps already complete (e.g. resumed after DB write but before onboarded
    # flag propagated); re-trigger completion write and show transition prompt.
    if step is None:
        return await _complete_onboarding(user_id, profile, history)

    last_role = history[-1]["role"] if history else "assistant"

    # ── Process user answer ───────────────────────────────────────────────────
    if history and last_role == "user":
        user_msg = history[-1]["content"]

        # OTP step: verify code before advancing. On failure, re-ask with error.
        if step == "otp_verification":
            import re as _re

            # If the user submitted a phone number instead of an OTP code, treat it
            # as "change number" — reset phone step and reprocess as a phone submission.
            if _re.match(r"^\+[1-9]\d{1,14}$", user_msg.strip()):
                profile.pop("_phone_collected", None)
                profile.pop("_otp_attempts", None)
                profile["phone_number"] = user_msg.strip()
                profile["_phone_collected"] = True
                # Fire OTP to the new number
                try:
                    from app.services.twilio_service import send_otp  # noqa: PLC0415

                    await send_otp(user_msg.strip())
                except Exception:
                    pass
                import json as _json

                await db.execute(
                    "UPDATE users SET profile = $1::jsonb, updated_at = now() WHERE id = $2",
                    _json.dumps(profile),
                    user_id,
                )
                otp_question = _get_question("otp_verification", profile)
                updated_history = history + [
                    {"role": "assistant", "content": otp_question}
                ]
                otp_options = _STEP_OPTIONS.get("otp_verification")
                return {
                    "conversation_history": updated_history,
                    "user_profile": profile,
                    "intent": "ONBOARDING",
                    "options": [o.model_dump() for o in otp_options]
                    if otp_options
                    else None,
                }

            phone = profile.get("phone_number", "")
            try:
                from app.services.twilio_service import confirm_otp  # noqa: PLC0415

                verified = await confirm_otp(phone, user_msg.strip())
            except Exception:
                verified = False

            if not verified:
                attempts = profile.get("_otp_attempts", 0) + 1
                profile["_otp_attempts"] = attempts
                if attempts >= 3:
                    # Exceeded max attempts — skip OTP step, continue onboarding
                    profile["_otp_skipped"] = True
                    profile["_otp_done"] = True  # marks step complete without verifying
                    next_step = _current_step(profile)
                    canned = (
                        "No worries — you can verify your number later in settings."
                    )
                    import json as _json

                    await db.execute(
                        "UPDATE users SET profile = $1::jsonb, updated_at = now() WHERE id = $2",
                        _json.dumps(profile),
                        user_id,
                    )
                    if next_step is not None:
                        next_question = _get_question(next_step, profile)
                        next_options = _STEP_OPTIONS.get(next_step)
                        updated_history = history + [
                            {
                                "role": "assistant",
                                "content": f"{canned} {next_question}",
                            }
                        ]
                        return {
                            "conversation_history": updated_history,
                            "user_profile": profile,
                            "intent": "ONBOARDING",
                            "options": [o.model_dump() for o in next_options]
                            if next_options
                            else None,
                        }
                    else:
                        updated_history = history + [
                            {"role": "assistant", "content": canned}
                        ]
                        return await _complete_onboarding(
                            user_id, profile, updated_history
                        )

                remaining = 3 - attempts
                error_msg = f"That code doesn't look right. You have {remaining} attempt{'s' if remaining != 1 else ''} left."
                options = _STEP_OPTIONS.get(step)
                updated_history = history + [
                    {"role": "assistant", "content": error_msg}
                ]
                import json as _json

                await db.execute(
                    "UPDATE users SET profile = $1::jsonb, updated_at = now() WHERE id = $2",
                    _json.dumps(profile),
                    user_id,
                )
                return {
                    "conversation_history": updated_history,
                    "user_profile": profile,
                    "intent": "ONBOARDING",
                    "options": [o.model_dump() for o in options] if options else None,
                }

            # Verified — mark phone_verified in DB
            await db.execute(
                "UPDATE users SET phone_verified = true WHERE id = $1",
                user_id,
            )

        profile = _apply_extraction(profile, step, user_msg)
        new_step = _current_step(profile)

        if new_step != step:
            # Step advanced — check if done
            if new_step is None:
                if step == "phone_number" and user_msg == "__skip_phone__":
                    canned = "No problem — you can enable SMS and WhatsApp reminders anytime from your profile settings."
                else:
                    canned = "Got it! Let me wrap things up."
                updated_history = history + [{"role": "assistant", "content": canned}]
                return await _complete_onboarding(user_id, profile, updated_history)

            # Persist partial profile to DB so send_message can reload it next turn
            import json as _json

            await db.execute(
                "UPDATE users SET profile = $1::jsonb, updated_at = now() WHERE id = $2",
                _json.dumps(profile),
                user_id,
            )

            # Fire OTP when advancing to the verification step
            if new_step == "otp_verification":
                phone = profile.get("phone_number", "")
                try:
                    from app.services.twilio_service import send_otp  # noqa: PLC0415

                    await send_otp(phone)
                except Exception:
                    pass  # User can verify via POST /account/phone/verify/send later

            # Ask the next question
            next_question = _get_question(new_step, profile)
            name = profile.get("name", "")
            name_part = f", {name}" if name else ""
            if step == "phone_number" and user_msg == "__skip_phone__":
                canned = f"No problem — you can enable SMS and WhatsApp reminders anytime from your profile settings. {next_question}"
            else:
                canned = f"Got it{name_part}! {next_question}"
            next_options = _STEP_OPTIONS.get(new_step)
            updated_history = history + [{"role": "assistant", "content": canned}]
            return {
                "conversation_history": updated_history,
                "user_profile": profile,
                "intent": "ONBOARDING",
                "options": [o.model_dump() for o in next_options]
                if next_options
                else None,
            }

        # Step did not advance — re-ask (shouldn't happen with validated frontend input)
        question = _get_question(step, profile)
        updated_history = history + [{"role": "assistant", "content": question}]
        options = _STEP_OPTIONS.get(step)
        return {
            "conversation_history": updated_history,
            "user_profile": profile,
            "intent": "ONBOARDING",
            "options": [o.model_dump() for o in options] if options else None,
        }

    # ── No user message yet — ask the current step question ──────────────────
    question = _get_question(step, profile)
    if not history:
        name = profile.get("name", "")
        greeting = f"Hey there, {name}! " if name else "Hey there! "
        content = (
            f"{greeting}I'm your Flux assistant and I'm here to help you reach your goals. "
            f"Let me start by getting to know you a little better.\n\n{question}"
        )
    else:
        content = question

    options = _STEP_OPTIONS.get(step)
    return {
        "conversation_history": history + [{"role": "assistant", "content": content}],
        "user_profile": profile,
        "intent": "ONBOARDING",
        "options": [o.model_dump() for o in options] if options else None,
    }


def _get_question(step: str, profile: dict) -> str:
    """Return the static question string for the given step."""
    _questions: dict[str, str] = {
        "name": "What should I call you?",
        "wake_time": "What time do you usually wake up?",
        "sleep_time": "And what time do you usually go to bed?",
        "work_hours": (
            "Do you work during the day? If so, roughly what hours and which days? "
            "(e.g., Mon–Fri 9 to 6)"
        ),
        "chronotype": "Are you more of a morning person or a night owl?",
        "phone_number": (
            "What's your phone number? I'll use it to send you reminders if you don't "
            "respond in the app. (Include country code, e.g., +15551234567)"
        ),
        "otp_verification": (
            "I just sent a 6-digit verification code to your phone. "
            "Enter it below to verify your number."
        ),
        "whatsapp_opt_in": "Can I also reach you on WhatsApp at this number?",
    }
    return _questions.get(step, "Let's continue with your setup.")

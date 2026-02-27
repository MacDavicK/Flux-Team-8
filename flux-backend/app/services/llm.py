import json
from typing import TYPE_CHECKING, Type, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.services.supabase import db

T = TypeVar("T", bound=BaseModel)

# ─────────────────────────────────────────────────────────────────
# 4.1 — LiteLLM global configuration
# ─────────────────────────────────────────────────────────────────

litellm.set_verbose = False
litellm.api_key = settings.openrouter_api_key
litellm.api_base = settings.openrouter_base_url
litellm.num_retries = 2
litellm.request_timeout = 30  # seconds

# ─────────────────────────────────────────────────────────────────
# 4.2 — Fallback configuration (3 model tiers)
# ─────────────────────────────────────────────────────────────────

litellm.fallbacks = [
    {"openrouter/openai/gpt-4o": ["openrouter/anthropic/claude-sonnet-4-20250514"]},
    {"openrouter/anthropic/claude-sonnet-4-20250514": ["openrouter/openai/gpt-4o"]},
    {"openrouter/openai/gpt-4o-mini": ["openrouter/anthropic/claude-haiku-4-5-20251001"]},
]


# ─────────────────────────────────────────────────────────────────
# 4.3 — Core LLM call
# ─────────────────────────────────────────────────────────────────

async def llm_call(
    model: str,
    system: str,
    messages: list[dict],
    max_tokens: int = 2048,
    user_id: str | None = None,
) -> str:
    """Unified async LLM call via LiteLLM → OpenRouter. Returns raw text."""
    full_messages = [{"role": "system", "content": system}] + messages

    response = await litellm.acompletion(
        model=model,
        messages=full_messages,
        max_tokens=max_tokens,
        extra_headers={
            "HTTP-Referer": settings.openrouter_app_url,
            "X-Title": settings.openrouter_app_name,
        },
    )

    # 4.6 — Track token usage when user_id present and usage data available
    if user_id and response.usage:
        await update_token_usage(
            user_id=user_id,
            provider="openrouter",
            tokens=response.usage.total_tokens,
        )

    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────
# 4.4 — Atomic token usage update
# ─────────────────────────────────────────────────────────────────

async def update_token_usage(user_id: str, provider: str, tokens: int) -> None:
    """Atomically increment per-provider and total monthly token usage."""
    await db.execute(
        """
        UPDATE users SET monthly_token_usage = jsonb_set(
            jsonb_set(
                monthly_token_usage,
                ARRAY[$1],
                (COALESCE((monthly_token_usage->$1)::int, 0) + $2)::text::jsonb
            ),
            ARRAY['total'],
            (COALESCE((monthly_token_usage->'total')::int, 0) + $2)::text::jsonb
        )
        WHERE id = $3
        """,
        provider,
        tokens,
        user_id,
    )


# ─────────────────────────────────────────────────────────────────
# 7.1 — Validated LLM call with Pydantic parsing + retry loop
# ─────────────────────────────────────────────────────────────────

async def validated_llm_call(
    model: str,
    system_prompt: str,
    messages: list[dict],
    output_model: Type[T],
    max_tokens: int = 2048,
    max_retries: int = 2,
    user_id: str | None = None,
) -> T:
    """
    Call the LLM and validate the JSON response against a Pydantic model.
    On parse/validation failure, re-prompts with the error message.
    Raises ValueError after max_retries exhausted.
    """
    conversation = list(messages)

    for attempt in range(max_retries + 1):
        raw = await llm_call(
            model=model,
            system=system_prompt,
            messages=conversation,
            max_tokens=max_tokens,
            user_id=user_id,
        )

        # Strip markdown code fences if the model wraps output in ```json ... ```
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(text)
            return output_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            if attempt >= max_retries:
                raise ValueError(
                    f"LLM failed to return valid {output_model.__name__} "
                    f"after {max_retries + 1} attempts. Last error: {exc}\n"
                    f"Last response: {raw}"
                ) from exc

            # Append the bad response + error as context and retry
            conversation = conversation + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"Your response could not be parsed. Error: {exc}\n"
                        f"Please respond with valid JSON that matches the required schema "
                        f"and nothing else."
                    ),
                },
            ]

    # Unreachable — loop always returns or raises
    raise ValueError("validated_llm_call: unexpected exit from retry loop")


# ─────────────────────────────────────────────────────────────────
# 4.5 — Token budget check
# ─────────────────────────────────────────────────────────────────

async def check_token_budget(user_id: str) -> str:
    """Returns 'ok' | 'soft_limit' | 'hard_limit'."""
    row = await db.fetchrow(
        "SELECT monthly_token_usage FROM users WHERE id = $1", user_id
    )
    if not row:
        return "ok"
    total = (row["monthly_token_usage"] or {}).get("total", 0)
    if total >= settings.monthly_token_hard_limit:
        return "hard_limit"
    if total >= settings.monthly_token_soft_limit:
        return "soft_limit"
    return "ok"

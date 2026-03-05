"""
21.1.5 — Unit tests for validated_llm_call.

Tests:
  - Retries on malformed JSON
  - Raises ValueError after max_retries exhausted
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel
from unittest.mock import AsyncMock, patch


class _Simple(BaseModel):
    value: str


@pytest.mark.asyncio
async def test_retry_on_malformed_json():
    """validated_llm_call retries when LLM returns non-JSON text."""
    call_count = 0

    async def _side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not valid json at all"
        return '{"value": "hello"}'

    with patch("app.services.llm.llm_call", side_effect=_side_effect):
        from app.services.llm import validated_llm_call
        result = await validated_llm_call(
            model="test-model",
            system_prompt="test",
            messages=[{"role": "user", "content": "hi"}],
            output_model=_Simple,
            max_retries=2,
        )
        assert result.value == "hello"
        assert call_count == 2


@pytest.mark.asyncio
async def test_raises_after_max_retries_exhausted():
    """validated_llm_call raises ValueError when all retries produce invalid JSON."""
    async def _always_bad(*args, **kwargs):
        return "still not json"

    with patch("app.services.llm.llm_call", side_effect=_always_bad):
        from app.services.llm import validated_llm_call
        with pytest.raises((ValueError, Exception)):
            await validated_llm_call(
                model="test-model",
                system_prompt="test",
                messages=[{"role": "user", "content": "hi"}],
                output_model=_Simple,
                max_retries=2,
            )

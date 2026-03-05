"""
21.1.8 — Unit tests for check_token_budget.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_returns_ok_below_soft_limit():
    with patch("app.services.llm.db") as mock_db, \
         patch("app.services.llm.settings") as mock_settings:
        mock_settings.monthly_token_soft_limit = 500_000
        mock_settings.monthly_token_hard_limit = 1_000_000
        mock_db.fetchval = AsyncMock(return_value=100_000)

        from app.services.llm import check_token_budget
        result = await check_token_budget("user-1")
        assert result == "ok"


@pytest.mark.asyncio
async def test_returns_soft_limit_between_thresholds():
    with patch("app.services.llm.db") as mock_db, \
         patch("app.services.llm.settings") as mock_settings:
        mock_settings.monthly_token_soft_limit = 500_000
        mock_settings.monthly_token_hard_limit = 1_000_000
        mock_db.fetchval = AsyncMock(return_value=600_000)

        from app.services.llm import check_token_budget
        result = await check_token_budget("user-1")
        assert result == "soft_limit"


@pytest.mark.asyncio
async def test_returns_hard_limit_above_hard_threshold():
    with patch("app.services.llm.db") as mock_db, \
         patch("app.services.llm.settings") as mock_settings:
        mock_settings.monthly_token_soft_limit = 500_000
        mock_settings.monthly_token_hard_limit = 1_000_000
        mock_db.fetchval = AsyncMock(return_value=1_200_000)

        from app.services.llm import check_token_budget
        result = await check_token_budget("user-1")
        assert result == "hard_limit"

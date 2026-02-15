"""Shared test fixtures for the Flux backend."""

import pytest


@pytest.fixture
def sample_user_data():
    """Sample user payload for testing."""
    return {
        "email": "testuser@flux.dev",
        "name": "Test User",
    }

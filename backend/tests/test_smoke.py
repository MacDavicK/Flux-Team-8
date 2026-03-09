"""Smoke tests — validates that the test infrastructure is functional.

These tests intentionally do not import any app modules because the
app/ directory has not been scaffolded yet. Once the FastAPI app
exists, replace these with real endpoint tests.
"""


def test_pytest_infrastructure():
    """Confirm pytest can discover and run tests."""
    assert True


def test_fixture_loading(sample_user_data):
    """Confirm fixtures from conftest.py load correctly."""
    assert sample_user_data["email"] == "testuser@flux.dev"
    assert "name" in sample_user_data


def test_python_version():
    """Confirm Python 3.11+ is available."""
    import sys

    assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version}"

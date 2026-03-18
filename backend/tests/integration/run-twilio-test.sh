#!/usr/bin/env bash
# Run the Twilio WhatsApp notification integration test.
# Requires: API running on localhost:8000, uv, and dev deps (uv sync --extra dev)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$BACKEND_ROOT"

# Ensure dev deps are installed
uv sync --extra dev --quiet 2>/dev/null || uv sync --extra dev

# Run the test with verbose output and live logs
uv run pytest tests/integration/test_twilio_notification.py -v -s "$@"

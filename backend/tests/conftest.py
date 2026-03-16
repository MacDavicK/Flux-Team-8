"""
Pytest configuration. Runs before any tests.
"""
from __future__ import annotations

import os
from pathlib import Path

# Fix host.docker.internal resolution when running tests from host (not in Docker).
# pydantic-settings reads .env but doesn't populate os.environ, so we load .env
# and set overrides before app.config is loaded.
def pytest_configure(config):
    env_path = Path(config.rootpath) / ".env"
    if not env_path.exists():
        return
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                env_vars[key] = val
    # Prefer MIGRATION_DATABASE_URL for DB when running from host
    if "MIGRATION_DATABASE_URL" in env_vars:
        os.environ["DATABASE_URL"] = env_vars["MIGRATION_DATABASE_URL"]
    # Replace host.docker.internal with 127.0.0.1 (Supabase, and DATABASE_URL if not overridden)
    for key in ("SUPABASE_URL", "DATABASE_URL"):
        if key == "DATABASE_URL" and "DATABASE_URL" in os.environ:
            continue  # Already set from MIGRATION_DATABASE_URL
        val = env_vars.get(key, "")
        if val and "host.docker.internal" in val:
            os.environ[key] = val.replace("host.docker.internal", "127.0.0.1")

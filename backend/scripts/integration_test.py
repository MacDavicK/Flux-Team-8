#!/usr/bin/env python3
"""
Flux Integration Test — Backend API
Run: cd backend && python scripts/integration_test.py

Requires:
  - Backend running at http://localhost:8000
  - SUPABASE_URL and SUPABASE_KEY in .env
  - A test user (auto-created if not exists)
"""

import os
import httpx
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"

# Test user creds (create this in Supabase dashboard if
# auto-signup is disabled)
TEST_EMAIL = os.environ.get("TEST_EMAIL", "flux-test@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "FluxTest123!")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9"
    ".CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)

results = []


def log(name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append((name, passed, detail))
    print(f"  {status} — {name}" + (f" ({detail})" if detail else ""))


async def run_tests():
    async with httpx.AsyncClient(timeout=30) as c:
        print("\n=== PHASE 1: Connectivity ===\n")

        # T1: Root health
        try:
            r = await c.get(f"{BASE}/health")
            log("GET /health", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            log("GET /health", False, str(e))

        # T2: API health
        try:
            r = await c.get(f"{API}/health")
            data = r.json()
            log(
                "GET /api/v1/health",
                r.status_code == 200 and "status" in data,
                f"status={r.status_code}, body={data}",
            )
        except Exception as e:
            log("GET /api/v1/health", False, str(e))

        print("\n=== PHASE 2: Auth ===\n")

        # Sign in via Supabase Auth REST API
        token = None
        user_id = None
        try:
            # Try sign in first
            r = await c.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
                headers={"apikey": SUPABASE_ANON_KEY},
            )
            if r.status_code != 200:
                # Try sign up
                r = await c.post(
                    f"{SUPABASE_URL}/auth/v1/signup",
                    json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
                    headers={"apikey": SUPABASE_ANON_KEY},
                )
            data = r.json()
            token = data.get("access_token")
            user_id = data.get("user", {}).get("id")
            log("Auth (sign in/up)", token is not None, f"user_id={user_id}")
        except Exception as e:
            log("Auth", False, str(e))
            print("\n⛔ Cannot continue without auth. Exiting.")
            return

        headers = {"Authorization": f"Bearer {token}"}

        print("\n=== PHASE 3: Account / Onboarding Status ===\n")

        # T3: Account me
        try:
            r = await c.get(f"{API}/account/me", headers=headers)
            data = r.json()
            has_onboarded = "onboarded" in data
            log(
                "GET /account/me",
                r.status_code == 200 and has_onboarded,
                f"onboarded={data.get('onboarded')}, keys={list(data.keys())[:5]}",
            )
            is_onboarded = data.get("onboarded", False)
        except Exception as e:
            log("GET /account/me", False, str(e))
            is_onboarded = False

        print("\n=== PHASE 4: Onboarding Chat (if not onboarded) ===\n")

        if not is_onboarded:
            onboarding_messages = [
                ("", "Should get greeting (resume/init)"),
                ("Alex", "Name → should ask wake time"),
                ("7am", "Wake time → should ask sleep time"),
                ("11pm", "Sleep time → should ask work schedule"),
                ("9 to 5 Monday to Friday", "Work → should ask chronotype"),
                ("morning person", "Chronotype → should ask commitments"),
                ("Gym on Tuesday evenings at 7pm", "Commitments → should complete"),
            ]
            for msg, desc in onboarding_messages:
                try:
                    r = await c.post(
                        f"{API}/chat/message", json={"message": msg}, headers=headers
                    )
                    data = r.json()
                    state = data.get("state", "?")
                    progress = data.get("progress", "?")
                    is_complete = data.get("is_complete", False)
                    has_sources = "sources" in data
                    log(
                        f"Onboarding: {desc}",
                        r.status_code == 200 and has_sources,
                        f"state={state}, progress={progress}, "
                        f"is_complete={is_complete}",
                    )
                    if is_complete:
                        break
                    # Small delay for rate limiting
                    await asyncio.sleep(0.5)
                except Exception as e:
                    log(f"Onboarding: {desc}", False, str(e))

            # Verify onboarded flag was set
            try:
                r = await c.get(f"{API}/account/me", headers=headers)
                data = r.json()
                log(
                    "Post-onboarding: onboarded=true",
                    data.get("onboarded"),
                    f"onboarded={data.get('onboarded')}",
                )
            except Exception as e:
                log("Post-onboarding check", False, str(e))
        else:
            print("  (User already onboarded — skipping)")

        print("\n=== PHASE 5: Goal Chat (onboarded user) ===\n")

        # T5a: Start a goal conversation
        try:
            r = await c.post(
                f"{API}/chat/message",
                json={"message": "I want to lose 5kg in 6 weeks"},
                headers=headers,
            )
            data = r.json()
            has_message = "message" in data and len(data["message"]) > 0
            has_sources = "sources" in data
            log(
                "Goal chat: start",
                r.status_code == 200 and has_message and has_sources,
                f"state={data.get('state')}, "
                f"sources_count={len(data.get('sources', []))}, "
                f"msg_preview={data.get('message', '')[:80]}...",
            )
        except Exception as e:
            log("Goal chat: start", False, str(e))

        # T5b: Reset conversation
        try:
            r = await c.post(
                f"{API}/chat/message", json={"message": "new goal"}, headers=headers
            )
            data = r.json()
            log(
                "Goal chat: reset",
                r.status_code == 200 and "sources" in data,
                f"msg={data.get('message', '')[:60]}",
            )
        except Exception as e:
            log("Goal chat: reset", False, str(e))

        print("\n=== PHASE 6: Tasks ===\n")

        # T6a: Today's tasks
        try:
            r = await c.get(f"{API}/tasks/today", headers=headers)
            data = r.json()
            # Might be empty for test user — that's OK
            log(
                "GET /tasks/today",
                r.status_code == 200,
                f"task_count={len(data) if isinstance(data, list) else data}",
            )
        except Exception as e:
            log("GET /tasks/today", False, str(e))

        print("\n=== PHASE 7: Scheduler ===\n")

        # T7: Scheduler suggest (will likely fail without a real
        # drifted task, but should return 400/404, not 500)
        try:
            r = await c.post(
                f"{API}/scheduler/suggest",
                json={"event_id": "00000000-0000-0000-0000-000000000000"},
                headers=headers,
            )
            # 400 or 404 is acceptable (no such task), 500 is a fail
            log(
                "POST /scheduler/suggest (fake id)",
                r.status_code != 500,
                f"status={r.status_code}",
            )
        except Exception as e:
            log("POST /scheduler/suggest", False, str(e))

        print("\n=== PHASE 8: Analytics ===\n")

        # T8a: Overview (includes heatmap)
        try:
            r = await c.get(f"{API}/analytics/overview", headers=headers)
            data = r.json()
            has_streak = "streak_days" in data
            has_heatmap = "heatmap" in data
            log(
                "GET /analytics/overview",
                r.status_code == 200 and has_streak,
                f"streak_days={data.get('streak_days')}, "
                f"has_heatmap={has_heatmap}, "
                f"heatmap_count={len(data.get('heatmap', []))}",
            )
        except Exception as e:
            log("GET /analytics/overview", False, str(e))

        # T8b: Weekly
        try:
            r = await c.get(f"{API}/analytics/weekly?weeks=12", headers=headers)
            data = r.json()
            log(
                "GET /analytics/weekly?weeks=12",
                r.status_code == 200,
                f"type={type(data).__name__}, "
                f"keys={list(data.keys()) if isinstance(data, dict) else 'list'}",
            )
        except Exception as e:
            log("GET /analytics/weekly", False, str(e))

        # T8c: Goals
        try:
            r = await c.get(f"{API}/analytics/goals", headers=headers)
            data = r.json()
            log(
                "GET /analytics/goals",
                r.status_code == 200,
                f"type={type(data).__name__}",
            )
        except Exception as e:
            log("GET /analytics/goals", False, str(e))

        # T8d: Missed by category
        try:
            r = await c.get(f"{API}/analytics/missed-by-category", headers=headers)
            data = r.json()
            log(
                "GET /analytics/missed-by-category",
                r.status_code == 200,
                f"type={type(data).__name__}",
            )
        except Exception as e:
            log("GET /analytics/missed-by-category", False, str(e))

        # T8e: Heatmap standalone (may not exist — that's OK)
        try:
            r = await c.get(f"{API}/analytics/heatmap", headers=headers)
            if r.status_code == 404:
                log(
                    "GET /analytics/heatmap",
                    True,
                    "404 — expected (heatmap is in /overview)",
                )
            else:
                log(
                    "GET /analytics/heatmap",
                    r.status_code == 200,
                    f"status={r.status_code}",
                )
        except Exception as e:
            log("GET /analytics/heatmap", False, str(e))

        print("\n=== PHASE 9: CORS Preflight ===\n")

        for origin in [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
        ]:
            try:
                r = await c.options(
                    f"{API}/health",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "GET",
                    },
                )
                allowed = r.headers.get("access-control-allow-origin", "")
                log(
                    f"CORS: {origin}",
                    origin in allowed or allowed == "*",
                    f"allowed={allowed}",
                )
            except Exception as e:
                log(f"CORS: {origin}", False, str(e))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    print(f"\n  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total:  {len(results)}")

    if failed > 0:
        print("\n  Failed tests:")
        for name, p, detail in results:
            if not p:
                print(f"    ❌ {name}: {detail}")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("FLUX INTEGRATION TEST")
    print(f"Target: {BASE}")
    print(f"Time:   {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    asyncio.run(run_tests())

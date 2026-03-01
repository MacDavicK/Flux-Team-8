# Pattern Observer Agent (SCRUM-50)

Background service that **learns from user behavioural history** to improve scheduling recommendations.

---

## Overview

| Property | Value |
|---|---|
| Jira Ticket | SCRUM-50 |
| Port | 8058 |
| LLM | GPT-4o-mini |
| Framework | FastAPI + Uvicorn |
| DAO Layer | `dao_service` (HTTP calls to port 8000) |

---

## Architecture

```
 Notifier Agent (SCRUM-57)
         |
   POST /api/pattern-observer/miss-signal
         |
    PatternService
     |         |
   DAO       PatternAnalyzer
  (tasks)    (GPT-4o-mini)
     |
  Pattern
  upsert
     |
  DAO /patterns
```

**Goal Planner / Scheduler** calls `POST /api/pattern-observer/consult` to get
structured behavioural hints before scheduling tasks.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/pattern-observer/health` | Liveness check |
| POST | `/api/pattern-observer/consult` | Get pattern summary for a user |
| POST | `/api/pattern-observer/miss-signal` | Report a missed task |
| GET | `/api/pattern-observer/patterns/{user_id}` | Admin: read stored patterns |

Full interactive docs at **`/docs`** (Swagger UI) and **`/redoc`** (ReDoc).

---

## Signals Tracked

- Task completion / miss history (by day of week, time of day)
- Category-level performance (e.g. Fitness 78%, Learning 42%)

---

## Avoidance Detection Logic

On each `miss-signal`, the service:

1. Fetches the user's missed tasks from `dao_service` for the past `AVOIDANCE_WEEK_SPAN * 7` days.
2. Filters tasks matching the same day-of-week and hour (`+/- SLOT_TOLERANCE_HOURS`).
3. Counts the number of **distinct ISO weeks** that had at least one miss in that slot.
4. If misses >= `AVOIDANCE_MISS_THRESHOLD` **and** week span >= `AVOIDANCE_WEEK_SPAN`, writes an `avoidance` Pattern record via `dao_service`.

---

## Cold-Start Strategy

For users with < `MIN_DATA_POINTS` tasks:
- Returns research-backed defaults (prefer 06:00-09:00; avoid Monday mornings)
- All patterns marked `low_confidence = true` until 2+ weeks of data are collected

---

## LLM System Prompt

Uses the exact prompt from SCRUM-50 spec. Returns JSON:

```json
{
  "best_times": ["07:00-09:00", "18:00-19:30"],
  "avoid_slots": [
    { "day": "Monday", "time_range": "07:00-09:00", "reason": "3 consecutive misses", "confidence": 0.85 }
  ],
  "category_performance": [
    { "category": "Fitness", "completion_rate": 0.78 }
  ],
  "general_notes": "User performs best on weekday mornings."
}
```

---

## Setup

```bash
cd backend/scrum_50_pattern_observer
cp .env.example .env
# fill in OPENAI_API_KEY and DATABASE_URL
pip install -r requirements.txt
python main.py
```

Or via Docker (uses the root docker-compose):

```bash
docker-compose up pattern-observer
```

---

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `PATTERN_OBSERVER_PORT` | 8058 | Service port |
| `OPENAI_API_KEY` | — | OpenAI key for GPT-4o-mini |
| `LLM_MODEL` | gpt-4o-mini | OpenAI model |
| `MIN_DATA_POINTS` | 3 | Min tasks required for LLM analysis |
| `AVOIDANCE_MISS_THRESHOLD` | 3 | Misses needed to flag avoidance |
| `AVOIDANCE_WEEK_SPAN` | 3 | Consecutive weeks required |
| `SLOT_TOLERANCE_HOURS` | 1 | +/- hour tolerance for slot matching |
| `LOW_CONFIDENCE_WEEKS` | 2 | Weeks before patterns are considered reliable |
| `TASK_HISTORY_DAYS` | 90 | Default lookback window |
| `LOG_LEVEL` | INFO | Logging verbosity |

---

## Tests

```bash
pip install pytest pytest-asyncio
pytest test_pattern_observer.py -v
```

---

## File Structure

```
scrum_50_pattern_observer/
  main.py             # FastAPI app + lifespan hooks
  routes.py           # API endpoints with Swagger annotations
  pattern_service.py  # Service layer: DAO calls + avoidance detection
  pattern_analyzer.py # LLM-powered pattern extraction
  models.py           # Pydantic request/response schemas
  config.py           # Settings from environment variables
  logger.py           # Structured logging helper
  requirements.txt
  .env.example
  test_pattern_observer.py
  README.md
```

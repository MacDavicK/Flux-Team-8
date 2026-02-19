# Flux API - Complete Usage Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Endpoints](#api-endpoints)
3. [Workflow Examples](#workflow-examples)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Install and Run

```powershell
# Run the setup script (automatically installs dependencies)
.\run.ps1
```

Or manually:

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
python main.py
```

The server will start at `http://localhost:8000`

### 2. Test the API

```powershell
# Run the test script
.\test_api.ps1
```

Or use the Python example:

```powershell
python example_usage.py
```

## API Endpoints

### Base URL

```
http://localhost:8000
```

### 1. Create a Goal

**Endpoint:** `POST /goals`

**Request Body:**

```json
{
  "title": "Learn Python",
  "description": "Master Python fundamentals and advanced concepts",
  "due_date": "2026-03-15T00:00:00",
  "user_id": "user123"
}
```

**Response:** `201 Created`

```json
{
  "id": 1,
  "user_id": "user123",
  "title": "Learn Python",
  "description": "Master Python fundamentals and advanced concepts",
  "due_date": "2026-03-15T00:00:00",
  "status": "pending",
  "created_at": "2026-02-12T10:00:00",
  "updated_at": "2026-02-12T10:00:00",
  "ai_analysis": null
}
```

**What Happens:**

- Goal is created in database
- AI agent analyzes the goal (background task)
- Goal is broken down into milestones and tasks
- Tasks are scheduled on the calendar
- Notifications are created for each task

### 2. List All Goals

**Endpoint:** `GET /goals?user_id=user123`

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "title": "Learn Python",
    "status": "in_progress",
    ...
  }
]
```

### 3. Get Goal Details

**Endpoint:** `GET /goals/{goal_id}`

**Response:** `200 OK`

```json
{
  "id": 1,
  "title": "Learn Python",
  "status": "in_progress",
  "ai_analysis": "This is a well-structured learning goal..."
}
```

### 4. Get Goal Breakdown

**Endpoint:** `GET /goals/{goal_id}/breakdown`

**Response:** `200 OK`

```json
{
  "goal": { ... },
  "milestones": [
    {
      "id": 1,
      "week_number": 1,
      "title": "Python Fundamentals",
      "description": "Learn basic syntax and data types",
      "target_date": "2026-02-19T00:00:00",
      "is_completed": false
    }
  ],
  "tasks": [
    {
      "id": 1,
      "title": "Learn Python variables and data types",
      "scheduled_date": "2026-02-13T09:00:00",
      "duration_minutes": 30,
      "status": "scheduled"
    }
  ],
  "total_weeks": 4,
  "total_tasks": 20
}
```

### 5. Get Calendar Events

**Endpoint:** `GET /calendar/events?start_date=2026-02-12T00:00:00&end_date=2026-02-19T00:00:00`

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "task_id": 1,
    "title": "Learn Python variables and data types",
    "start_time": "2026-02-13T09:00:00",
    "end_time": "2026-02-13T09:30:00",
    "is_task_related": true
  }
]
```

### 6. List Tasks

**Endpoint:** `GET /tasks?goal_id=1&status=scheduled`

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "goal_id": 1,
    "title": "Learn Python variables",
    "scheduled_date": "2026-02-13T09:00:00",
    "status": "scheduled",
    "reschedule_count": 0
  }
]
```

### 7. Acknowledge Notification

**Endpoint:** `POST /notifications/acknowledge`

**Request Body:**

```json
{
  "notification_id": 1,
  "acknowledged": true
}
```

**Response:** `200 OK`

```json
{
  "message": "Task started successfully",
  "success": true
}
```

**What Happens:**

- If `acknowledged: true`: Task status changes to "in_progress"
- If `acknowledged: false`: Task is rescheduled to next available slot

### 8. Complete Task

**Endpoint:** `POST /tasks/{task_id}/complete`

**Response:** `200 OK`

```json
{
  "message": "Task completed successfully",
  "success": true
}
```

## Workflow Examples

### Example 1: Complete Goal Creation Workflow

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# 1. Create a goal
response = requests.post(f"{BASE_URL}/goals", json={
    "title": "Learn Machine Learning",
    "description": "Master ML fundamentals and build projects",
    "due_date": (datetime.now() + timedelta(days=60)).isoformat(),
    "user_id": "user123"
})
goal = response.json()
goal_id = goal['id']

# 2. Wait for processing (or poll the goal endpoint)
import time
time.sleep(5)

# 3. Get the breakdown
response = requests.get(f"{BASE_URL}/goals/{goal_id}/breakdown")
breakdown = response.json()

print(f"Created {breakdown['total_tasks']} tasks across {breakdown['total_weeks']} weeks")

# 4. Check calendar
response = requests.get(f"{BASE_URL}/calendar/events")
events = response.json()
print(f"Scheduled {len(events)} calendar events")
```

### Example 2: Notification Handling

```python
# When you receive a notification (notification_id = 1)

# Option A: Acknowledge and start the task
response = requests.post(f"{BASE_URL}/notifications/acknowledge", json={
    "notification_id": 1,
    "acknowledged": True
})
# Task status becomes "in_progress"

# Option B: Dismiss and reschedule
response = requests.post(f"{BASE_URL}/notifications/acknowledge", json={
    "notification_id": 1,
    "acknowledged": False
})
# Task is automatically rescheduled
result = response.json()
print(f"Task rescheduled to {result.get('new_time')}")
```

### Example 3: Completing Tasks

```python
# When you finish working on a task
task_id = 1

response = requests.post(f"{BASE_URL}/tasks/{task_id}/complete")
result = response.json()
print(result['message'])  # "Task completed successfully"
```

## Testing

### Run Unit Tests

```powershell
# Run all tests
pytest test_main.py -v

# Run with coverage
pytest test_main.py --cov=. --cov-report=html

# Run specific test
pytest test_main.py::test_create_goal -v
```

### Manual API Testing

Use the provided scripts:

```powershell
# PowerShell script
.\test_api.ps1

# Python script
python example_usage.py
```

Or use curl:

```powershell
# Create a goal
curl -X POST "http://localhost:8000/goals" `
  -H "Content-Type: application/json" `
  -d '{\"title\":\"Learn Python\",\"description\":\"Master Python\",\"due_date\":\"2026-03-15T00:00:00\",\"user_id\":\"user123\"}'

# Get goals
curl "http://localhost:8000/goals?user_id=user123"
```

### Using Swagger UI

Navigate to `http://localhost:8000/docs` for an interactive API interface where you can:

- View all endpoints
- Try out API calls
- See request/response schemas
- Download OpenAPI specification

## Troubleshooting

### Common Issues

#### 1. Import Errors When Running

**Problem:** `Import "fastapi" could not be resolved`

**Solution:**

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

#### 2. OpenAI API Errors

**Problem:** `AuthenticationError: Invalid API key`

**Solution:**

- Check your `.env` file has correct `OPENAI_API_KEY`
- Verify the API key is valid at <https://platform.openai.com/api-keys>
- Make sure there are no extra spaces or quotes

#### 3. Database Errors

**Problem:** `OperationalError: no such table`

**Solution:**

- Delete `flux.db` if it exists
- Restart the server (it will recreate tables)

#### 4. Port Already in Use

**Problem:** `OSError: [Errno 98] Address already in use`

**Solution:**

```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use a different port
uvicorn main:app --port 8001
```

#### 5. Background Tasks Not Processing

**Problem:** Goal created but no milestones/tasks generated

**Solution:**

- Check server logs for errors
- Verify OpenAI API key is valid
- Check you have sufficient OpenAI credits
- Wait a few seconds and check `/goals/{id}/breakdown` again

### Debug Mode

Enable debug logging:

```python
# In config.py or .env
DEBUG=True
LOG_LEVEL=DEBUG
```

View detailed logs in the console.

### Getting Help

1. Check the logs in the terminal where the server is running
2. Visit `http://localhost:8000/docs` for API documentation
3. Review the error message in API responses
4. Check the `test_main.py` for example usage patterns

## Advanced Configuration

### Custom Working Hours

```env
# .env
DEFAULT_WORK_START_HOUR=8
DEFAULT_WORK_END_HOUR=20
```

### Task Duration

```env
# .env
DEFAULT_TASK_DURATION_MINUTES=45
```

### Notification Timing

```env
# .env
NOTIFICATION_CHECK_INTERVAL_MINUTES=30  # Notify 30 min before task
```

### Reschedule Strategy

```env
# .env
MISSED_TASK_RESCHEDULE_DAYS=2  # Reschedule 2 days out
```

## Performance Tips

1. **Use Background Tasks**: Goal processing happens asynchronously
2. **Batch Operations**: Create multiple goals at once
3. **Pagination**: Add `?limit=10&offset=0` for large datasets (future enhancement)
4. **Caching**: Consider caching calendar queries for frequent access

## Security Notes

- Currently uses a simple `user_id` for identification
- No authentication implemented (add JWT/OAuth for production)
- OpenAI API key is stored in `.env` (keep secure)
- SQLite database is for development (use PostgreSQL for production)

---

**For more information, visit the main README.md or open an issue on GitHub.**

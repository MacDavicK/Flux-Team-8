# Project Structure

```
Flux/
│
├── main.py                      # FastAPI application with all endpoints
├── config.py                    # Application configuration and settings
├── database.py                  # Database setup, session management
├── models.py                    # SQLAlchemy ORM models
├── schemas.py                   # Pydantic schemas for API validation
│
├── ai_agent.py                  # AI agent for goal analysis and breakdown
├── calendar_service.py          # Calendar and scheduling logic
├── notification_service.py      # Notification management service
│
├── test_main.py                 # Unit tests for API endpoints
├── example_usage.py             # Python example showing API usage
│
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment variables
├── .gitignore                   # Git ignore rules
├── LICENSE                      # MIT License
│
├── README.md                    # Main documentation
├── USAGE_GUIDE.md              # Comprehensive usage guide
├── PROJECT_STRUCTURE.md        # This file
│
├── run.ps1                     # PowerShell script to run the app
└── test_api.ps1                # PowerShell script to test API
```

## Core Components

### 1. FastAPI Application (`main.py`)

The main application file that defines all REST API endpoints:

- `POST /goals` - Create a new goal
- `GET /goals` - List all goals
- `GET /goals/{id}` - Get specific goal
- `GET /goals/{id}/breakdown` - Get goal breakdown
- `POST /notifications/acknowledge` - Acknowledge notifications
- `POST /tasks/{id}/complete` - Mark task as complete
- `GET /calendar/events` - Get calendar events
- `GET /tasks` - List tasks with filters

### 2. Configuration (`config.py`)

Manages application settings using Pydantic Settings:

- OpenAI API configuration
- Database connection string
- Working hours settings
- Notification preferences
- Task scheduling parameters

### 3. Database Layer (`database.py`, `models.py`)

**database.py:**

- SQLAlchemy engine setup
- Session management
- Database initialization

**models.py:**

- `Goal` - User goals with due dates
- `Milestone` - Weekly checkpoints
- `Task` - Daily actionable items
- `CalendarEvent` - Scheduled events
- `Notification` - Task reminders

### 4. API Schemas (`schemas.py`)

Pydantic models for request/response validation:

- `GoalCreate`, `GoalResponse`
- `MilestoneResponse`
- `TaskResponse`
- `CalendarEventResponse`
- `NotificationResponse`
- `GoalBreakdownResponse`

### 5. AI Agent (`ai_agent.py`)

Intelligent goal processing using LangChain and OpenAI:

- **analyze_goal()** - Provides empathetic analysis of goals
- **breakdown_goal()** - Breaks goals into milestones and tasks
- **suggest_reschedule_time()** - AI-powered rescheduling

### 6. Calendar Service (`calendar_service.py`)

Manages scheduling and calendar operations:

- **get_available_slots()** - Find free time slots
- **schedule_task()** - Place task on calendar
- **reschedule_task()** - Reschedule missed tasks
- **get_events()** - Query calendar events

### 7. Notification Service (`notification_service.py`)

Handles task reminders and acknowledgments:

- **create_notification()** - Create task reminder
- **send_notification()** - Send notification to user
- **acknowledge_notification()** - Handle user response
- **check_missed_tasks()** - Auto-reschedule missed tasks
- **complete_task()** - Mark task as done

## Data Flow

### Goal Creation Flow

```
User -> POST /goals -> FastAPI
                        |
                        v
                   Create Goal in DB
                        |
                        v
              Background Task Started
                        |
                        v
                   AI Agent Analysis
                        |
                        v
              Create Milestones & Tasks
                        |
                        v
              Schedule on Calendar
                        |
                        v
              Create Notifications
```

### Notification Flow

```
Scheduled Time -> Notification Service
                        |
                        v
                  Send Notification
                        |
                        v
                   User Response?
                   /           \
                  /             \
            Acknowledged    Not Acknowledged
                 |                 |
                 v                 v
         Start Task         Reschedule Task
                                   |
                                   v
                          Create New Notification
```

### Task Completion Flow

```
User -> POST /tasks/{id}/complete
              |
              v
       Update Task Status
              |
              v
   Mark Notifications as Complete
              |
              v
      Check Milestone Progress
              |
              v
       Update Goal Status
```

## Key Design Decisions

### 1. Async Background Processing

- Goal breakdown happens in background using FastAPI BackgroundTasks
- Allows immediate response to user while AI processes
- Prevents timeout issues with long-running AI calls

### 2. Calendar-First Scheduling

- All tasks must fit in available calendar slots
- Respects working hours (configurable)
- Automatically finds gaps between existing events

### 3. Intelligent Rescheduling

- Missed tasks automatically rescheduled
- AI can suggest optimal reschedule times
- Tracks reschedule history for analytics

### 4. Flexible Notification System

- Notifications created when task scheduled
- Configurable notification timing
- Supports acknowledgment or dismissal

### 5. Modular Service Architecture

- Separation of concerns (AI, Calendar, Notifications)
- Easy to test individual components
- Can be extended with new services

## Database Schema

```
Goal (1) ─────────────── (M) Milestone
  │                           │
  │                           │
  └─────────────────── (M) Task
                          │
                          ├── (1) CalendarEvent
                          └── (M) Notification
```

### Relationships

- One Goal has many Milestones
- One Goal has many Tasks
- One Milestone has many Tasks
- One Task has one CalendarEvent
- One Task has many Notifications

## Extension Points

### Adding New Features

1. **Custom AI Models**
   - Modify `ai_agent.py` to use different LLM providers
   - Swap OpenAI with Anthropic, Cohere, etc.

2. **External Calendar Integration**
   - Extend `calendar_service.py` to sync with Google Calendar
   - Add OAuth authentication

3. **Real Notifications**
   - Implement push notifications in `notification_service.py`
   - Add email/SMS providers

4. **User Authentication**
   - Add JWT/OAuth to `main.py`
   - Implement user management

5. **Analytics Dashboard**
   - Track completion rates
   - Visualize progress
   - Goal achievement insights

## Testing Strategy

### Unit Tests (`test_main.py`)

- Test each API endpoint independently
- Mock database and external services
- Verify request/response schemas

### Integration Tests

- Test complete workflows (create goal → breakdown → schedule)
- Verify service interactions
- Test error handling

### Manual Testing

- `test_api.ps1` - PowerShell script for quick testing
- `example_usage.py` - Python script demonstrating usage
- Swagger UI at `/docs` - Interactive testing

## Deployment Considerations

### Development

- SQLite database (single file)
- File-based logging
- Debug mode enabled

### Production

- PostgreSQL database (replace SQLite)
- Cloud logging (AWS CloudWatch, Azure Monitor)
- Environment-based configuration
- API rate limiting
- Authentication/Authorization
- HTTPS/SSL
- Containerization (Docker)
- Orchestration (Kubernetes)

## Performance Optimization

### Database

- Add indexes on frequently queried fields
- Use connection pooling
- Implement caching (Redis)

### API

- Add pagination for list endpoints
- Implement request throttling
- Use async database drivers

### AI

- Cache common goal breakdowns
- Batch AI requests
- Use streaming for long responses

## Security Considerations

1. **API Keys**
   - Store in environment variables
   - Never commit to version control
   - Rotate regularly

2. **User Data**
   - Encrypt sensitive information
   - Implement access controls
   - GDPR compliance for user data

3. **API Security**
   - Add authentication (JWT)
   - Rate limiting
   - Input validation
   - SQL injection prevention (SQLAlchemy handles this)

## Future Enhancements

See README.md for the full roadmap. Priority items:

1. User authentication
2. External calendar sync
3. Real-time notifications
4. Mobile apps
5. Team collaboration

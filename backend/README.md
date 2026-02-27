# Flux - Agentic AI Goal Achievement Platform

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Flux** is an Agentic AI system that transforms abstract goals into achievable daily actions. It acts as your AI partner, understanding your long-term aspirations, breaking them down into manageable routines, and guiding you with context-aware, empathetic support.

## 🌟 Features

- **AI-Powered Goal Breakdown**: Automatically breaks down long-term goals into weekly milestones and daily tasks
- **Smart Scheduling**: Integrates with your calendar to find optimal time slots for tasks
- **Intelligent Notifications**: Sends timely reminders when it's time to work on tasks
- **Adaptive Rescheduling**: Automatically reschedules missed tasks based on your availability
- **Context-Aware Support**: AI understands your goals and provides empathetic guidance
- **RESTful API**: Easy-to-use FastAPI endpoints for all operations

## 🏗️ Architecture

```
Flux/
├── main.py                    # FastAPI application & endpoints
├── config.py                  # Configuration and settings
├── database.py                # Database setup and session management
├── models.py                  # SQLAlchemy database models
├── schemas.py                 # Pydantic schemas for API
├── ai_agent.py                # AI agent for goal analysis
├── calendar_service.py        # Calendar and scheduling logic
├── notification_service.py    # Notification management
├── test_main.py              # Unit tests
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment variables
└── README.md                 # This file
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- OpenAI API key

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/flux.git
   cd flux
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   
   # On Windows
   .\venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your OpenAI API key
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. **Run the application**

   ```bash
   python main.py
   ```

   The API will be available at `http://localhost:8000`

6. **View API documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## 📖 API Usage

### Create a Goal

```bash
POST http://localhost:8000/goals
Content-Type: application/json

{
  "title": "Learn Machine Learning",
  "description": "Master ML fundamentals and build real-world projects",
  "due_date": "2026-03-15T00:00:00",
  "user_id": "user123"
}
```

**Response:**

```json
{
  "id": 1,
  "user_id": "user123",
  "title": "Learn Machine Learning",
  "description": "Master ML fundamentals and build real-world projects",
  "due_date": "2026-03-15T00:00:00",
  "status": "pending",
  "created_at": "2026-02-12T10:00:00",
  "updated_at": "2026-02-12T10:00:00",
  "ai_analysis": null
}
```

### Get Goal Breakdown

```bash
GET http://localhost:8000/goals/1/breakdown
```

**Response:**

```json
{
  "goal": { ... },
  "milestones": [
    {
      "id": 1,
      "goal_id": 1,
      "title": "Week 1: Python Basics",
      "description": "Learn Python fundamentals",
      "week_number": 1,
      "target_date": "2026-02-19T00:00:00",
      "is_completed": false
    }
  ],
  "tasks": [
    {
      "id": 1,
      "goal_id": 1,
      "milestone_id": 1,
      "title": "Learn Python syntax",
      "description": "Study variables, functions, and control flow",
      "scheduled_date": "2026-02-13T09:00:00",
      "duration_minutes": 30,
      "status": "scheduled"
    }
  ],
  "total_weeks": 4,
  "total_tasks": 20
}
```

### Acknowledge a Notification

```bash
POST http://localhost:8000/notifications/acknowledge
Content-Type: application/json

{
  "notification_id": 1,
  "acknowledged": true
}
```

### Complete a Task

```bash
POST http://localhost:8000/tasks/1/complete
```

### Get Calendar Events

```bash
GET http://localhost:8000/calendar/events?start_date=2026-02-12T00:00:00&end_date=2026-02-19T00:00:00
```

## 🧪 Testing

Run the test suite:

```bash
pytest test_main.py -v
```

Run with coverage:

```bash
pytest test_main.py --cov=. --cov-report=html
```

## 🔧 Configuration

Edit `.env` file to customize:

- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Model to use (default: gpt-4-turbo-preview)
- `DATABASE_URL`: Database connection string
- `DEFAULT_WORK_START_HOUR`: Working hours start (default: 9)
- `DEFAULT_WORK_END_HOUR`: Working hours end (default: 18)
- `DEFAULT_TASK_DURATION_MINUTES`: Default task duration (default: 30)
- `NOTIFICATION_CHECK_INTERVAL_MINUTES`: How early to notify (default: 15)
- `MISSED_TASK_RESCHEDULE_DAYS`: Days to reschedule missed tasks (default: 1)

## 🎯 How It Works

1. **Goal Creation**: User submits a goal with a due date
2. **AI Analysis**: AI agent analyzes the goal and provides insights
3. **Breakdown**: AI breaks the goal into weekly milestones and daily tasks
4. **Scheduling**: Calendar service schedules tasks in available time slots
5. **Notifications**: System sends reminders before each task
6. **Acknowledgment**: User acknowledges or dismisses notifications
7. **Rescheduling**: Missed tasks are automatically rescheduled
8. **Completion**: User marks tasks as complete, tracking progress

## 🔮 Future Enhancements

- [ ] Multi-user authentication and authorization
- [ ] Integration with Google Calendar, Outlook, etc.
- [ ] Push notifications (mobile, email, SMS)
- [ ] Progress visualization and analytics
- [ ] Habit tracking and streak monitoring
- [ ] Natural language input for goals
- [ ] Voice assistant integration
- [ ] Team collaboration features
- [ ] Mobile app (iOS/Android)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [OpenAI](https://openai.com/)
- LLM framework by [LangChain](https://langchain.com/)

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

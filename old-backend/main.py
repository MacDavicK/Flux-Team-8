from fastapi import FastAPI, HTTPException, BackgroundTasks
from datetime import datetime, timedelta
from typing import List, Optional

# Commented out for testing - will enable when implementing full functionality
# from fastapi import Depends
# from sqlalchemy.orm import Session
# from database import get_db, init_db
# from models import Goal, Milestone, Task, CalendarEvent, GoalStatus, TaskStatus
# from ai_agent import AIAgent
# from calendar_service import CalendarService
# from notification_service import NotificationService

from schemas import (
    GoalCreate, GoalResponse, GoalBreakdownResponse,
    MilestoneResponse, TaskResponse, CalendarEventResponse,
    NotificationAcknowledge, MessageResponse
)
from config import settings

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Agentic AI that transforms goals into achievable daily actions",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    # init_db()
    print(f"🚀 {settings.app_name} started successfully!")
    print("⚠️  Running in TEST MODE with hardcoded responses")


# Initialize AI Agent
# ai_agent = AIAgent()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "1.0.0",
        "endpoints": {
            "create_goal": "POST /goals",
            "list_goals": "GET /goals",
            "get_goal": "GET /goals/{goal_id}",
            "breakdown_goal": "GET /goals/{goal_id}/breakdown",
            "acknowledge_notification": "POST /notifications/acknowledge",
            "complete_task": "POST /tasks/{task_id}/complete",
            "calendar_events": "GET /calendar/events"
        }
    }


@app.post("/goals", status_code=201)
async def create_goal(
    goal: GoalCreate,
    background_tasks: BackgroundTasks
):
    """
    Create a new goal. The AI will analyze it and break it down into milestones and tasks.
    
    - **title**: Goal title (required)
    - **description**: Detailed description of the goal
    - **due_date**: When the goal should be completed
    - **user_id**: User identifier (for future multi-user support)
    """
    # Validate due date
    if goal.due_date <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Due date must be in the future"
        )
    
    # TODO: Implement database logic
    # # Create goal in database
    # db_goal = Goal(
    #     user_id=goal.user_id,
    #     title=goal.title,
    #     description=goal.description,
    #     due_date=goal.due_date,
    #     status=GoalStatus.PENDING
    # )
    # db.add(db_goal)
    # db.commit()
    # db.refresh(db_goal)
    
    # # Trigger background processing
    # background_tasks.add_task(
    #     process_goal_breakdown,
    #     db_goal.id,
    #     goal.title,
    #     goal.description,
    #     goal.due_date
    # )
    
    # Hardcoded response for testing
    return {
        "id": 1,
        "user_id": goal.user_id,
        "title": goal.title,
        "description": goal.description,
        "due_date": goal.due_date.isoformat(),
        "status": "pending",
        "ai_analysis": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


async def process_goal_breakdown(
    goal_id: int,
    title: str,
    description: str,
    due_date: datetime
):
    """Background task to process goal breakdown."""
    # TODO: Implement AI agent logic
    # # Create new database session for background task
    # from database import SessionLocal
    # db = SessionLocal()
    
    # try:
    #     # Get AI analysis
    #     ai_analysis = await ai_agent.analyze_goal(title, description, due_date)
    #     
    #     # Get goal breakdown
    #     breakdown = await ai_agent.breakdown_goal(title, description, due_date)
    #     
    #     # Update goal with AI analysis
    #     goal = db.query(Goal).filter(Goal.id == goal_id).first()
    #     goal.ai_analysis = ai_analysis
    #     goal.status = GoalStatus.IN_PROGRESS
    #     db.commit()
    #     
    #     # Create milestones
    #     milestone_map = {}
    #     for milestone_data in breakdown.get("milestones", []):
    #         week_number = milestone_data["week_number"]
    #         target_date = datetime.now() + timedelta(weeks=week_number)
    #         
    #         milestone = Milestone(
    #             goal_id=goal_id,
    #             title=milestone_data["title"],
    #             description=milestone_data.get("description"),
    #             week_number=week_number,
    #             target_date=target_date
    #         )
    #         db.add(milestone)
    #         db.commit()
    #         db.refresh(milestone)
    #         
    #         milestone_map[week_number] = milestone.id
    #     
    #     # Create tasks and schedule them
    #     calendar_service = CalendarService(db)
    #     notification_service = NotificationService(db)
    #     
    #     for task_data in breakdown.get("tasks", []):
    #         day_offset = task_data.get("day_offset", 0)
    #         scheduled_date = datetime.now() + timedelta(days=day_offset)
    #         
    #         # Get milestone ID
    #         milestone_week = task_data.get("milestone_week", 1)
    #         milestone_id = milestone_map.get(milestone_week)
    #         
    #         # Create task
    #         task = Task(
    #             goal_id=goal_id,
    #             milestone_id=milestone_id,
    #             title=task_data["title"],
    #             description=task_data.get("description"),
    #             scheduled_date=scheduled_date,
    #             duration_minutes=task_data.get("duration_minutes", 30),
    #             status=TaskStatus.SCHEDULED
    #         )
    #         db.add(task)
    #         db.commit()
    #         db.refresh(task)
    #         
    #         # Schedule on calendar
    #         calendar_service.schedule_task(task, scheduled_date)
    #         
    #         # Create notification
    #         notification_service.create_notification(task)
    #     
    #     db.commit()
    #     print(f"✅ Goal {goal_id} processed successfully")
    #     
    # except Exception as e:
    #     print(f"❌ Error processing goal {goal_id}: {str(e)}")
    #     db.rollback()
    # finally:
    #     db.close()
    
    print(f"⚠️  Background processing for goal {goal_id} is disabled in test mode")


@app.get("/goals")
async def list_goals(user_id: str = "default_user"):
    """List all goals for a user."""
    # TODO: Implement database query
    # goals = db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.created_at.desc()).all()
    # return goals
    
    # Hardcoded response for testing
    return [
        {
            "id": 1,
            "user_id": user_id,
            "title": "Learn Python Programming",
            "description": "Master Python programming from basics to advanced",
            "due_date": (datetime.now() + timedelta(days=90)).isoformat(),
            "status": "in_progress",
            "ai_analysis": "Goal requires consistent practice and project work",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        {
            "id": 2,
            "user_id": user_id,
            "title": "Build AI Project",
            "description": "Create an AI-powered application using LangChain",
            "due_date": (datetime.now() + timedelta(days=60)).isoformat(),
            "status": "pending",
            "ai_analysis": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    ]


@app.get("/goals/{goal_id}")
async def get_goal(goal_id: int):
    """Get a specific goal by ID."""
    # TODO: Implement database query
    # goal = db.query(Goal).filter(Goal.id == goal_id).first()
    # if not goal:
    #     raise HTTPException(status_code=404, detail="Goal not found")
    # return goal
    
    # Hardcoded response for testing
    return {
        "id": goal_id,
        "user_id": "default_user",
        "title": "Learn Python Programming",
        "description": "Master Python programming from basics to advanced",
        "due_date": (datetime.now() + timedelta(days=90)).isoformat(),
        "status": "in_progress",
        "ai_analysis": "Goal requires consistent practice and project work",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


@app.get("/goals/{goal_id}/breakdown")
async def get_goal_breakdown(goal_id: int):
    """Get complete breakdown of a goal with milestones and tasks."""
    # TODO: Implement database queries
    # goal = db.query(Goal).filter(Goal.id == goal_id).first()
    # if not goal:
    #     raise HTTPException(status_code=404, detail="Goal not found")
    # milestones = db.query(Milestone).filter(Milestone.goal_id == goal_id).order_by(Milestone.week_number).all()
    # tasks = db.query(Task).filter(Task.goal_id == goal_id).order_by(Task.scheduled_date).all()
    
    # Hardcoded response for testing
    now = datetime.now()
    return {
        "goal": {
            "id": goal_id,
            "user_id": "default_user",
            "title": "Learn Python Programming",
            "description": "Master Python programming from basics to advanced",
            "due_date": (now + timedelta(days=90)).isoformat(),
            "status": "in_progress",
            "ai_analysis": "Goal requires consistent practice and project work",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        "milestones": [
            {
                "id": 1,
                "goal_id": goal_id,
                "title": "Python Basics",
                "description": "Learn syntax, data types, and control flow",
                "week_number": 1,
                "target_date": (now + timedelta(weeks=1)).isoformat(),
                "completed": True,
                "created_at": now.isoformat()
            },
            {
                "id": 2,
                "goal_id": goal_id,
                "title": "OOP and Advanced Concepts",
                "description": "Master classes, inheritance, and decorators",
                "week_number": 4,
                "target_date": (now + timedelta(weeks=4)).isoformat(),
                "completed": False,
                "created_at": now.isoformat()
            }
        ],
        "tasks": [
            {
                "id": 1,
                "goal_id": goal_id,
                "milestone_id": 1,
                "title": "Complete Python basics tutorial",
                "description": "Watch tutorial videos and complete exercises",
                "scheduled_date": (now + timedelta(days=1)).isoformat(),
                "duration_minutes": 60,
                "status": "completed",
                "completed_at": now.isoformat(),
                "created_at": now.isoformat()
            },
            {
                "id": 2,
                "goal_id": goal_id,
                "milestone_id": 1,
                "title": "Build calculator app",
                "description": "Create a simple calculator using Python",
                "scheduled_date": (now + timedelta(days=3)).isoformat(),
                "duration_minutes": 90,
                "status": "scheduled",
                "completed_at": None,
                "created_at": now.isoformat()
            }
        ],
        "total_weeks": 2,
        "total_tasks": 2
    }


@app.post("/notifications/acknowledge")
async def acknowledge_notification(ack: NotificationAcknowledge):
    """
    Acknowledge or dismiss a notification.
    
    - **notification_id**: ID of the notification
    - **acknowledged**: True to accept and start task, False to dismiss and reschedule
    """
    # TODO: Implement notification service
    # notification_service = NotificationService(db)
    # result = notification_service.acknowledge_notification(
    #     ack.notification_id,
    #     ack.acknowledged
    # )
    # if not result["success"]:
    #     raise HTTPException(status_code=404, detail=result["message"])
    
    # Hardcoded response for testing
    return {
        "message": f"Notification {ack.notification_id} {'acknowledged' if ack.acknowledged else 'dismissed'} successfully",
        "success": True
    }


@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: int):
    """Mark a task as completed."""
    # TODO: Implement notification service
    # notification_service = NotificationService(db)
    # result = notification_service.complete_task(task_id)
    # if not result["success"]:
    #     raise HTTPException(status_code=404, detail=result["message"])
    
    # Hardcoded response for testing
    return {
        "message": f"Task {task_id} marked as completed successfully",
        "success": True
    }


@app.get("/calendar/events")
async def get_calendar_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get calendar events within a date range.
    
    - **start_date**: Start of date range (defaults to today)
    - **end_date**: End of date range (defaults to 7 days from start)
    """
    # TODO: Implement calendar service
    # if start_date is None:
    #     start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # if end_date is None:
    #     end_date = start_date + timedelta(days=7)
    # calendar_service = CalendarService(db)
    # events = calendar_service.get_events(start_date, end_date)
    # return events
    
    # Hardcoded response for testing
    now = datetime.now()
    return [
        {
            "id": 1,
            "task_id": 1,
            "event_id": "evt_001",
            "start_time": (now + timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=3)).isoformat(),
            "created_at": now.isoformat()
        },
        {
            "id": 2,
            "task_id": 2,
            "event_id": "evt_002",
            "start_time": (now + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=11, minutes=30)).isoformat(),
            "created_at": now.isoformat()
        }
    ]


@app.get("/tasks")
async def list_tasks(
    goal_id: Optional[int] = None,
    status: Optional[str] = None
):
    """
    List tasks with optional filters.
    
    - **goal_id**: Filter by goal ID
    - **status**: Filter by task status
    """
    # TODO: Implement database query
    # query = db.query(Task)
    # if goal_id:
    #     query = query.filter(Task.goal_id == goal_id)
    # if status:
    #     query = query.filter(Task.status == status)
    # tasks = query.order_by(Task.scheduled_date).all()
    # return tasks
    
    # Hardcoded response for testing
    now = datetime.now()
    all_tasks = [
        {
            "id": 1,
            "goal_id": 1,
            "milestone_id": 1,
            "title": "Complete Python basics tutorial",
            "description": "Watch tutorial videos and complete exercises",
            "scheduled_date": (now + timedelta(days=1)).isoformat(),
            "duration_minutes": 60,
            "status": "completed",
            "completed_at": now.isoformat(),
            "created_at": now.isoformat()
        },
        {
            "id": 2,
            "goal_id": 1,
            "milestone_id": 1,
            "title": "Build calculator app",
            "description": "Create a simple calculator using Python",
            "scheduled_date": (now + timedelta(days=3)).isoformat(),
            "duration_minutes": 90,
            "status": "scheduled",
            "completed_at": None,
            "created_at": now.isoformat()
        },
        {
            "id": 3,
            "goal_id": 2,
            "milestone_id": 2,
            "title": "Research AI frameworks",
            "description": "Compare different AI frameworks and tools",
            "scheduled_date": (now + timedelta(days=5)).isoformat(),
            "duration_minutes": 120,
            "status": "scheduled",
            "completed_at": None,
            "created_at": now.isoformat()
        }
    ]
    
    # Apply filters
    filtered_tasks = all_tasks
    if goal_id:
        filtered_tasks = [t for t in filtered_tasks if t["goal_id"] == goal_id]
    if status:
        filtered_tasks = [t for t in filtered_tasks if t["status"] == status]
    
    return filtered_tasks


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

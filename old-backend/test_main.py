import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
from models import Goal, Task, Notification

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_goal_data():
    """Sample goal data for testing."""
    return {
        "title": "Learn Python Programming",
        "description": "Master Python fundamentals and build real projects",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "user_id": "test_user"
    }


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_create_goal(client, sample_goal_data):
    """Test goal creation."""
    response = client.post("/goals", json=sample_goal_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_goal_data["title"]
    assert data["user_id"] == sample_goal_data["user_id"]
    assert "id" in data


def test_create_goal_invalid_date(client, sample_goal_data):
    """Test goal creation with past due date."""
    sample_goal_data["due_date"] = (datetime.now() - timedelta(days=1)).isoformat()
    response = client.post("/goals", json=sample_goal_data)
    assert response.status_code == 400


def test_list_goals(client, sample_goal_data):
    """Test listing goals."""
    # Create a goal first
    client.post("/goals", json=sample_goal_data)
    
    # List goals
    response = client.get("/goals?user_id=test_user")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == sample_goal_data["title"]


def test_get_goal(client, sample_goal_data):
    """Test getting a specific goal."""
    # Create a goal
    create_response = client.post("/goals", json=sample_goal_data)
    goal_id = create_response.json()["id"]
    
    # Get the goal
    response = client.get(f"/goals/{goal_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == goal_id
    assert data["title"] == sample_goal_data["title"]


def test_get_nonexistent_goal(client):
    """Test getting a goal that doesn't exist."""
    response = client.get("/goals/99999")
    assert response.status_code == 404


def test_get_calendar_events(client):
    """Test getting calendar events."""
    response = client.get("/calendar/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_tasks(client, sample_goal_data):
    """Test listing tasks."""
    # Create a goal first
    create_response = client.post("/goals", json=sample_goal_data)
    goal_id = create_response.json()["id"]
    
    # List tasks
    response = client.get(f"/tasks?goal_id={goal_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

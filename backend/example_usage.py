"""
Example usage of the Flux Agentic AI API
This script demonstrates how to use the Flux API to create goals and manage tasks.
"""

import requests
from datetime import datetime, timedelta
from time import sleep

# Base URL for the API
BASE_URL = "http://localhost:8000"


def create_goal(title: str, description: str, days_until_due: int):
    """Create a new goal."""
    print(f"\n📝 Creating goal: {title}")
    
    due_date = (datetime.now() + timedelta(days=days_until_due)).isoformat()
    
    response = requests.post(
        f"{BASE_URL}/goals",
        json={
            "title": title,
            "description": description,
            "due_date": due_date,
            "user_id": "example_user"
        }
    )
    
    if response.status_code == 201:
        goal = response.json()
        print(f"✓ Goal created with ID: {goal['id']}")
        return goal['id']
    else:
        print(f"✗ Failed to create goal: {response.text}")
        return None


def get_goal_breakdown(goal_id: int):
    """Get the breakdown of a goal."""
    print(f"\n📊 Fetching breakdown for goal {goal_id}...")
    
    # Wait a bit for AI processing
    print("⏳ Waiting for AI to process (5 seconds)...")
    sleep(5)
    
    response = requests.get(f"{BASE_URL}/goals/{goal_id}/breakdown")
    
    if response.status_code == 200:
        breakdown = response.json()
        
        print(f"\n✓ Goal: {breakdown['goal']['title']}")
        print(f"  Status: {breakdown['goal']['status']}")
        print(f"  AI Analysis: {breakdown['goal']['ai_analysis'][:200]}..." if breakdown['goal']['ai_analysis'] else "  (Processing...)")
        
        print(f"\n📅 Milestones ({breakdown['total_weeks']} weeks):")
        for milestone in breakdown['milestones']:
            status = "✓" if milestone['is_completed'] else "○"
            print(f"  {status} Week {milestone['week_number']}: {milestone['title']}")
        
        print(f"\n✓ Tasks ({breakdown['total_tasks']} total):")
        for i, task in enumerate(breakdown['tasks'][:5], 1):
            print(f"  {i}. [{task['status']}] {task['title']}")
            print(f"     Scheduled: {task['scheduled_date']}")
        
        if len(breakdown['tasks']) > 5:
            print(f"  ... and {len(breakdown['tasks']) - 5} more tasks")
        
        return breakdown
    else:
        print(f"✗ Failed to get breakdown: {response.text}")
        return None


def list_goals():
    """List all goals."""
    print("\n📋 Listing all goals...")
    
    response = requests.get(f"{BASE_URL}/goals?user_id=example_user")
    
    if response.status_code == 200:
        goals = response.json()
        print(f"\n✓ Found {len(goals)} goals:")
        for goal in goals:
            print(f"  • [{goal['status']}] {goal['title']} (Due: {goal['due_date'][:10]})")
        return goals
    else:
        print(f"✗ Failed to list goals: {response.text}")
        return []


def get_calendar_events():
    """Get calendar events."""
    print("\n📆 Fetching calendar events...")
    
    response = requests.get(f"{BASE_URL}/calendar/events")
    
    if response.status_code == 200:
        events = response.json()
        print(f"\n✓ Found {len(events)} calendar events:")
        for event in events[:5]:
            print(f"  • {event['title']}")
            print(f"    {event['start_time']} - {event['end_time']}")
        
        if len(events) > 5:
            print(f"  ... and {len(events) - 5} more events")
        return events
    else:
        print(f"✗ Failed to get events: {response.text}")
        return []


def main():
    """Main example workflow."""
    print("=" * 60)
    print("🚀 Flux Agentic AI - Example Usage")
    print("=" * 60)
    
    # Example 1: Learning goal
    goal_id_1 = create_goal(
        title="Learn Web Development",
        description="Master HTML, CSS, JavaScript, and React. Build 3 portfolio projects.",
        days_until_due=60
    )
    
    # Example 2: Fitness goal
    goal_id_2 = create_goal(
        title="Get Fit and Healthy",
        description="Exercise 4x per week, improve diet, lose 10 pounds",
        days_until_due=90
    )
    
    # Example 3: Career goal
    goal_id_3 = create_goal(
        title="Advance My Career",
        description="Learn new skills, build portfolio, apply to 20 jobs, get interviews",
        days_until_due=120
    )
    
    # List all goals
    list_goals()
    
    # Get breakdown for first goal
    if goal_id_1:
        breakdown = get_goal_breakdown(goal_id_1)
    
    # Get calendar events
    get_calendar_events()
    
    print("\n" + "=" * 60)
    print("✓ Example completed!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("  • View API docs: http://localhost:8000/docs")
    print("  • Acknowledge notifications when they arrive")
    print("  • Complete tasks as you work on them")
    print("  • Check your calendar regularly")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to Flux API")
        print("   Make sure the server is running: python main.py")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

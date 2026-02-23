"""
Simple API test script for Flux AI
Tests all endpoints with hardcoded responses
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("\n🔍 Testing GET /")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_create_goal():
    """Test create goal endpoint"""
    print("\n🔍 Testing POST /goals")
    goal_data = {
        "title": "Learn FastAPI",
        "description": "Master FastAPI framework for building APIs",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "user_id": "test_user"
    }
    response = requests.post(f"{BASE_URL}/goals", json=goal_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 201

def test_list_goals():
    """Test list goals endpoint"""
    print("\n🔍 Testing GET /goals")
    response = requests.get(f"{BASE_URL}/goals")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_get_goal():
    """Test get single goal endpoint"""
    print("\n🔍 Testing GET /goals/1")
    response = requests.get(f"{BASE_URL}/goals/1")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_goal_breakdown():
    """Test goal breakdown endpoint"""
    print("\n🔍 Testing GET /goals/1/breakdown")
    response = requests.get(f"{BASE_URL}/goals/1/breakdown")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_list_tasks():
    """Test list tasks endpoint"""
    print("\n🔍 Testing GET /tasks")
    response = requests.get(f"{BASE_URL}/tasks")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_list_tasks_filtered():
    """Test list tasks with filters"""
    print("\n🔍 Testing GET /tasks?goal_id=1&status=scheduled")
    response = requests.get(f"{BASE_URL}/tasks?goal_id=1&status=scheduled")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_calendar_events():
    """Test calendar events endpoint"""
    print("\n🔍 Testing GET /calendar/events")
    response = requests.get(f"{BASE_URL}/calendar/events")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_acknowledge_notification():
    """Test acknowledge notification endpoint"""
    print("\n🔍 Testing POST /notifications/acknowledge")
    data = {
        "notification_id": 1,
        "acknowledged": True
    }
    response = requests.post(f"{BASE_URL}/notifications/acknowledge", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_complete_task():
    """Test complete task endpoint"""
    print("\n🔍 Testing POST /tasks/1/complete")
    response = requests.post(f"{BASE_URL}/tasks/1/complete")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Flux AI API Tests")
    print("=" * 60)
    print("\n⚠️  Make sure the server is running: python main.py")
    print("Or: uvicorn main:app --reload")
    
    tests = [
        ("Root Endpoint", test_root),
        ("Create Goal", test_create_goal),
        ("List Goals", test_list_goals),
        ("Get Goal", test_get_goal),
        ("Goal Breakdown", test_goal_breakdown),
        ("List Tasks", test_list_tasks),
        ("List Tasks (Filtered)", test_list_tasks_filtered),
        ("Calendar Events", test_calendar_events),
        ("Acknowledge Notification", test_acknowledge_notification),
        ("Complete Task", test_complete_task),
    ]
    
    results = []
    
    try:
        for test_name, test_func in tests:
            try:
                success = test_func()
                results.append((test_name, success))
            except requests.exceptions.ConnectionError:
                print(f"\n❌ Connection Error: Cannot connect to {BASE_URL}")
                print("Make sure the server is running!")
                return
            except Exception as e:
                print(f"\n❌ Error in {test_name}: {str(e)}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status}: {test_name}")
        
        print(f"\n{passed}/{total} tests passed")
        print("=" * 60)
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")

if __name__ == "__main__":
    main()

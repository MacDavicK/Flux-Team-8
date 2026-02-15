# Getting Started with Flux

Welcome to **Flux** - your Agentic AI partner for achieving goals! This guide will walk you through setting up and using Flux for the first time.

## 📋 Prerequisites

Before you begin, ensure you have:

1. **Python 3.9 or higher** installed
   - Check: `python --version`
   - Download: <https://www.python.org/downloads/>

2. **OpenAI API Key**
   - Sign up at: <https://platform.openai.com/>
   - Get API key from: <https://platform.openai.com/api-keys>
   - You'll need this to use the AI features

3. **Git** (if you cloned the repository)
   - Check: `git --version`

## 🚀 Setup Steps

### Step 1: Open PowerShell in the Project Directory

```powershell
cd c:\project path..
```

### Step 2: Verify Setup

Run the verification script to check if everything is ready:

```powershell
python verify_setup.py
```

This will check:

- Python version
- Virtual environment
- Dependencies
- Configuration files
- Required project files

### Step 3: Quick Setup (Recommended)

Run the automated setup script:

```powershell
.\run.ps1
```

This script will:

1. Create a virtual environment (if needed)
2. Install all dependencies
3. Check for `.env` file and create from example
4. Prompt you to add your OpenAI API key
5. Start the server

**Important:** When prompted, you MUST add your OpenAI API key to the `.env` file!

### Step 4: Manual Setup (Alternative)

If you prefer to set up manually:

#### 4.1 Create Virtual Environment

```powershell
python -m venv venv
```

#### 4.2 Activate Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of your command prompt.

#### 4.3 Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install:

- FastAPI (web framework)
- SQLAlchemy (database)
- OpenAI & LangChain (AI)
- And other dependencies

#### 4.4 Configure Environment Variables

```powershell
# Copy the example file
Copy-Item .env.example .env

# Open .env in notepad
notepad .env
```

**Edit the `.env` file and add your OpenAI API key:**

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Keep other settings as default for now
DATABASE_URL=sqlite:///./flux.db
DEFAULT_WORK_START_HOUR=9
DEFAULT_WORK_END_HOUR=18
DEFAULT_TASK_DURATION_MINUTES=30
```

**Save and close the file.**

### Step 5: Start the Server

```powershell
python main.py
```

You should see:

```
🚀 Flux Agentic AI started successfully!
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal window open!** The server needs to run continuously.

### Step 6: Verify It's Working

Open a **new PowerShell window** and run:

```powershell
curl http://localhost:8000
```

Or open your browser and visit: <http://localhost:8000>

You should see a JSON response with the welcome message.

## 🎯 Your First Goal

Now let's create your first goal! Open a new PowerShell window.

### Method 1: Using the Example Script

```powershell
cd c:\Users\HKALIDI3\GitRepos\Flux
.\venv\Scripts\Activate.ps1
python example_usage.py
```

This will create 3 sample goals and show you the breakdowns.

### Method 2: Using the Test Script

```powershell
.\test_api.ps1
```

This will create a "Learn Python Machine Learning" goal and show all the details.

### Method 3: Manual API Call

```powershell
$body = @{
    title = "Get Fit in 30 Days"
    description = "Exercise 4x per week, improve diet, and feel great"
    due_date = (Get-Date).AddDays(30).ToString("yyyy-MM-ddTHH:mm:ss")
    user_id = "my_user"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/goals" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

## 📖 Explore the API

### Swagger UI (Interactive Documentation)

Visit: <http://localhost:8000/docs>

Here you can:

- See all available endpoints
- Try out API calls directly in your browser
- View request/response schemas
- Download API specification

### ReDoc (Clean Documentation)

Visit: <http://localhost:8000/redoc>

Alternative documentation format with a cleaner layout.

## 🧪 Testing

### Run Unit Tests

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run tests
pytest test_main.py -v
```

Expected output:

```
test_main.py::test_root_endpoint PASSED
test_main.py::test_create_goal PASSED
test_main.py::test_list_goals PASSED
...
========== 10 passed in 2.5s ==========
```

## 📚 Next Steps

1. **Read the Guides**
   - `QUICK_REFERENCE.md` - Quick command reference
   - `USAGE_GUIDE.md` - Comprehensive API guide
   - `PROJECT_STRUCTURE.md` - Technical deep dive

2. **Create Your Own Goals**
   - Use the Swagger UI to create goals interactively
   - Or use Python/PowerShell scripts
   - Or build your own client application

3. **Explore Features**
   - Create multiple goals with different timelines
   - Check the calendar to see scheduled tasks
   - Acknowledge notifications when they arrive
   - Complete tasks as you work on them

4. **Customize Settings**
   - Edit `.env` to match your schedule
   - Adjust working hours
   - Change task durations
   - Modify notification timing

## 🛠️ Common Issues

### Issue: "Import could not be resolved"

This is just a linting warning in VS Code. The code will run fine if dependencies are installed.

**Solution:** Ignore these warnings or install the Python extension for VS Code.

### Issue: "Address already in use"

Another instance of the server is running.

**Solution:**

```powershell
# Find process on port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

### Issue: "OpenAI API error"

Your API key might be invalid or you've run out of credits.

**Solution:**

1. Check your key at <https://platform.openai.com/api-keys>
2. Verify you have credits at <https://platform.openai.com/account/usage>
3. Make sure the key in `.env` has no extra spaces

### Issue: "No tasks created"

The background processing might still be running.

**Solution:**

1. Wait 5-10 seconds after creating a goal
2. Check `/goals/{id}/breakdown` endpoint
3. Look at server logs for errors

## 💡 Tips for Success

1. **Start Small**: Create a short-term goal (7-14 days) to test the system

2. **Realistic Goals**: The AI works best with clear, achievable goals

3. **Good Descriptions**: Provide detailed descriptions to help the AI understand your goal

4. **Check Logs**: The server terminal shows helpful debug information

5. **Use Docs**: The Swagger UI at `/docs` is your friend!

6. **Iterate**: Experiment with different goals and settings to find what works for you

## 🎓 Example Workflows

### Learning Workflow

```
1. Create goal: "Learn React in 8 weeks"
2. AI breaks it down:
   - Week 1-2: JavaScript fundamentals
   - Week 3-4: React basics
   - Week 5-6: Advanced React
   - Week 7-8: Build projects
3. Tasks scheduled automatically
4. Get notifications when it's time to learn
5. Complete tasks as you progress
```

### Fitness Workflow

```
1. Create goal: "Get fit in 12 weeks"
2. AI creates:
   - Weekly workout milestones
   - Daily exercise tasks
   - Nutrition planning tasks
   - Progress tracking tasks
3. Acknowledge notifications = start workout
4. Complete task = mark workout done
5. Miss notification = auto-reschedule
```

## 🤝 Getting Help

1. **Check Documentation**
   - Start with `QUICK_REFERENCE.md`
   - Deep dive in `USAGE_GUIDE.md`

2. **Server Logs**
   - Look at the terminal where you ran `python main.py`
   - Errors and debug info appear here

3. **Verification Script**
   - Run `python verify_setup.py` to diagnose issues

4. **GitHub Issues**
   - Open an issue if you find bugs
   - Share your use cases and feedback

## 🎉 You're Ready

You now have a fully functional Agentic AI system that will help you achieve your goals!

**Remember:**

- Keep the server running (`python main.py`)
- Check notifications regularly
- Complete tasks to track progress
- Create new goals as needed

**Start achieving your goals with AI today! 🚀**

---

Questions? Check the other documentation files or the Swagger UI at <http://localhost:8000/docs>

# Configuration

The voice agent is configured via two files + settings in `config.py`. Swap the files and you have a different voice agent — no code changes needed.

---

## Config Settings (`config.py`)

Add these to the existing `Settings` class:

```python
# Deepgram Voice Agent
deepgram_api_key: str = ""                          # Required — DEEPGRAM_API_KEY env var
deepgram_voice_model: str = "aura-2-thalia-en"      # Deepgram TTS voice
deepgram_listen_model: str = "nova-3"               # Deepgram STT model
deepgram_llm_model: str = "gpt-4o-mini"             # LLM model (via Deepgram)
deepgram_token_ttl: int = 3600                      # Temp token TTL in seconds (max 1hr)

# Voice session limits
voice_prompt_file: str = "config/voice_prompt.md"
voice_intents_file: str = "config/intents.yaml"
voice_daily_session_limit: int = 20
```

All loaded via Pydantic `BaseSettings` from environment variables.

The `deepgram_token_ttl` controls how long the temporary JWT is valid. The token only needs to be valid at WebSocket connection time — once the Deepgram WebSocket is open, it stays open regardless of token expiry.

---

## System Prompt — `config/voice_prompt.md`

The system prompt defines the agent's personality and behavior. Loaded by the backend at session creation and returned to the client as part of the session config. The client includes it in the Deepgram Settings message as the `agent.think.prompt` field.

```markdown
You are Flux, a warm and concise voice assistant for a personal goal and task management app.

Your ONLY job is to understand what the user wants to do and gather enough
information to submit their request. You do NOT create plans, schedule tasks,
or give detailed advice — you extract the intent through natural conversation.

## Intents:

GOAL — A multi-week aspiration ("I want to learn guitar", "I want to get fit")
  Required: goal_statement
  Optional: timeline, context_notes
  → Call submit_goal_intent

NEW_TASK — A discrete reminder ("Remind me to buy groceries tomorrow at 5pm")
  Required: title, trigger_type (time or location)
  If time-triggered: need a specific time or recurring schedule
  If location-triggered: need location condition ("when I leave home")
  → Call submit_new_task_intent

RESCHEDULE_TASK — Moving an existing task
  Required: task_id (from user context or identified from task list)
  Optional: preferred_new_time, reason
  → Call submit_reschedule_intent

## Rules:
1. Keep responses to 1-2 sentences. Be warm and concise.
2. Ask ONE clarifying question at a time.
3. NEVER call a tool until you have ALL required parameters.
4. Handle multiple intents one at a time — confirm each before the next.
5. If ambiguous, ask a focused question. Never guess.
6. Off-topic → redirect: "I'm here to help with goals and tasks."
7. "Never mind" → acknowledge, ask if anything else.
8. After success → confirm what was submitted, ask if anything else.
9. Nothing else → brief farewell.
10. Use the user's name if available.
11. If you can't understand the user → say: "Sorry, I didn't catch that. Could you say that again?"
12. If the user corrects you → acknowledge and proceed with corrected info.

## User context (injected at session start):
- Name, chronotype, work hours, sleep window
- Today's active tasks (for reschedule identification)
```

### Dynamic Context Injection

At session creation, the backend appends user-specific context to the prompt before returning it to the client:

```
<base prompt from file>

---
## Current User Context:
- Name: Krishna
- Today's tasks:
  - Gym at 6pm (id: abc-123)
  - Groceries at 5pm (id: def-456)
```

---

## Intent Registry — `config/intents.yaml`

Defines the function tools and how to route each intent.

```yaml
intents:
  - name: submit_goal_intent
    route: GOAL
    description: >
      Submit a fully extracted goal intent. Call this when the user has clearly
      expressed a multi-week aspiration and you have gathered the goal statement.
    parameters:
      - name: goal_statement
        type: string
        required: true
        description: "The user's goal in their own words"
      - name: timeline
        type: string
        required: false
        description: "Target date, event, or timeframe"
      - name: context_notes
        type: string
        required: false
        description: "Additional context for the Goal Planner"

  - name: submit_new_task_intent
    route: NEW_TASK
    description: >
      Submit a fully extracted task intent. Call this when the user wants a
      discrete reminder or one-time/recurring task and all required params are gathered.
    parameters:
      - name: title
        type: string
        required: true
        description: "Short task title"
      - name: trigger_type
        type: string
        required: true
        enum: ["time", "location"]
        description: "Whether the task is triggered by time or location"
      - name: scheduled_at
        type: string
        required: false
        description: "When the task should occur (natural language). Required if trigger_type is time."
      - name: recurrence_rule
        type: string
        required: false
        description: "Recurrence pattern (natural language). Omit for one-time tasks."
      - name: location_trigger
        type: string
        required: false
        description: "Location condition. Required if trigger_type is location."

  - name: submit_reschedule_intent
    route: RESCHEDULE_TASK
    description: >
      Submit a reschedule request for an existing task. Call this when the user
      wants to move a task and you have identified which task they mean.
    parameters:
      - name: task_id
        type: string
        required: true
        description: "UUID of the task to reschedule"
      - name: preferred_new_time
        type: string
        required: false
        description: "When the user wants to move the task to (natural language)"
      - name: reason
        type: string
        required: false
        description: "Why the user wants to reschedule"
```

---

## How the Registry is Converted to Deepgram Functions

The backend reads the YAML and converts each intent to Deepgram-compatible function definitions. These are returned to the client in the session creation response.

```python
# Input (from YAML):
{
  "name": "submit_goal_intent",
  "route": "GOAL",
  "description": "Submit a fully extracted goal intent...",
  "parameters": [
    {"name": "goal_statement", "type": "string", "required": True, "description": "..."},
    {"name": "timeline", "type": "string", "required": False, "description": "..."},
  ]
}

# Output (for Deepgram Settings — sent by the client):
{
  "name": "submit_goal_intent",
  "description": "Submit a fully extracted goal intent...",
  "parameters": {
    "type": "object",
    "properties": {
      "goal_statement": {"type": "string", "description": "..."},
      "timeline": {"type": "string", "description": "..."}
    },
    "required": ["goal_statement"]
  }
}
```

No `endpoint` field — functions are client-side (client receives `FunctionCallRequest` and processes via backend REST).

---

## How They Work Together

```
Session Start:
  1. Backend loads config/intents.yaml → list of Deepgram function definitions
  2. Backend loads config/voice_prompt.md → base prompt string
  3. Backend appends user context to prompt
  4. Backend mints Deepgram temp token
  5. Backend returns { token, config: { prompt, functions, models } } to client
  6. Client opens Deepgram WebSocket with token
  7. Client sends Settings message with config values

Function Call Received (at the client):
  1. Deepgram sends FunctionCallRequest to client with function_name + input
  2. Client calls POST /api/v1/voice/intents on backend
  3. Backend looks up intent by function_name
  4. Backend validates payload, routes to Orchestrator
  5. Backend returns result string
  6. Client sends FunctionCallResponse to Deepgram with result
```

---

## Greeting Configuration

The agent greeting is included in the session config and set in the Settings message:

```json
"greeting": "Hey! What can I help you with today?"
```

Deepgram automatically speaks this when the session starts. Configurable per deployment.

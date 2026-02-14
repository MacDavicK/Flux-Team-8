# 🎯 Flux Life Assistant

*"Transforming Goals into Daily Actions with Empathetic AI"*

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)
![Contributors](https://img.shields.io/badge/contributors-6-orange)

---

## About the Project

Most people fail at their goals not because they lack motivation, but because they struggle to bridge the **Goal-to-Action Gap** — the disconnect between setting an ambitious target and knowing exactly what to do today, tomorrow, and next week to achieve it. Traditional productivity tools track tasks but don't understand context, adapt to disruptions, or offer encouragement when plans fall apart.

**Flux** is an AI-powered life assistant that closes this gap. Through natural conversation, Flux decomposes high-level goals (like "lose 15 lbs before my wedding") into personalized daily schedules with concrete, time-blocked actions. It monitors progress in real time, detects when tasks drift, and proactively reschedules your day — all while maintaining an empathetic, supportive tone.

What sets Flux apart is its **Compassionate Drift & Shuffle** engine. Instead of punishing missed tasks with guilt or rigid failure states, Flux intelligently redistributes your schedule, factors in your energy levels and priorities, and sends encouraging nudges to get you back on track. Life happens — Flux adapts with you.

> 📹 **Demo Video:** [Coming Soon](#)

### Who is Flux for?

**Goal-Setters** — Individuals with aspirations who struggle to create and maintain actionable plans. Flux turns ambiguous intentions into concrete daily steps and keeps you accountable without pressure.

**Busy Professionals** — Knowledge workers juggling multiple responsibilities who need intelligent prioritization. Flux auto-resolves scheduling conflicts and surfaces only what matters right now.

**Neurodivergent Users** — People with ADHD or executive dysfunction who benefit from adaptive, shame-free task management. Flux never punishes a missed task — it adapts the plan and meets you where you are.

**Lifestyle Optimizers** — Anyone seeking a personal AI assistant that understands their patterns and adapts. Flux learns your rhythms over time and schedules around your energy, not just your calendar.

---

## Features

**Empathetic Goal Breakdown** — An AI dialogue that understands your "why" before creating a plan. Flux asks the right questions to build a schedule rooted in your personal motivation, not generic templates. Goals are decomposed through multi-turn conversation into weekly milestones with concrete recurring tasks.

**Context-Aware Reminders** — Smart notifications that factor in location, time of day, and behavior patterns. Flux knows when you're most productive and when a gentle nudge is more effective than an alarm. On-device sensors detect context like "just left work" to trigger relevant reminders at the right moment.

**Compassionate Drift & Shuffle** — Missed a task? Flux reschedules with encouragement, not guilt. The drift engine evaluates what can shift, what's critical, and how to keep your day balanced. Instead of a red "overdue" label, you get a negotiation: "Gym drifted — I can fit it at 5 PM or tomorrow at 7 AM."

**Multi-Channel Escalation** — Push notification → SMS → WhatsApp, escalating based on task priority and response history. Critical tasks don't get lost in notification noise. Must-not-miss items can escalate all the way to a VoIP call as a final safety net.

**Pattern Learning** — Over time, Flux learns your productive hours, preferred routines, and common disruption patterns to build increasingly accurate schedules. The Observer agent detects aversions (like consistently skipping Monday gym sessions) and suggests preference updates weekly.

**Demo Mode** — Time-warp controls and scenario simulation tools for showcasing the full lifecycle — goal creation, drift detection, recovery — in minutes instead of weeks. Pre-seeded data lets anyone experience Flux's failure-handling flows without waiting for real time to pass.

**Voice-First Interaction** — Speak naturally to create tasks, set goals, and manage your schedule. Flux uses Speech-to-Text and Text-to-Speech for a conversational experience that reduces form-filling friction.

---

## Why Flux?

| Competitor | Their Approach | Where They Fall Short |
|------------|----------------|----------------------|
| **Todoist** | Task lists with due dates and manual rescheduling | No understanding of *why* you missed; pure list management |
| **Reclaim.ai** | Auto-schedules around calendar meetings | Rigid time slots; no emotional intelligence; no pattern learning |
| **Motion** | AI auto-scheduler for teams | Enterprise-focused; no compassion layer; expensive |
| **Notion Calendar** | Unified workspace with drag-and-drop | Manual effort; no AI intervention when plans fail |
| **Google Calendar** | Universal calendar standard | Binary missed/done states; red "overdue" labels trigger shame |

**Flux fills the gap** with goal decomposition, context-aware nudging, compassionate rescheduling, and multi-channel escalation — capabilities none of the above offer together.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Framer Motion, React Router |
| Backend | FastAPI, Python 3.11+ |
| Database | PostgreSQL via Supabase |
| AI/ML | GPT-4o-mini, RAG (Pinecone/Chroma) |
| Deployment | Vercel (Frontend), Railway/Render (Backend) |

---

## Architecture

```mermaid
flowchart TD
    subgraph Client
        User["👤 User / PWA"]
    end

    subgraph Frontend
        FE["⚛️ React Frontend<br/>Vite + TypeScript + Framer Motion"]
    end

    subgraph Backend["FastAPI Backend"]
        API["🔌 API Gateway"]

        subgraph Agents["AI Agent Layer"]
            GP["🎯 Goal Planner<br/>Goal Breakdown & Plans"]
            SC["🗓️ Scheduler<br/>Core Orchestrator"]
            OB["🔍 Observer<br/>Pattern Learning"]
            SN["📍 Sensor<br/>Context Awareness"]
            EM["💚 Empath<br/>Sentiment Detection"]
        end

        LLM["🧠 GPT-4o-mini<br/>NL Understanding + Tool Use"]
    end

    subgraph Data
        DB[("🗄️ PostgreSQL<br/>Supabase")]
        RAG["📚 Vector DB<br/>Pinecone/Chroma"]
    end

    subgraph Notifications
        N["🔔 Notification Service"]
        Push["📱 Push"]
        WA["📲 WhatsApp"]
        Call["📞 VoIP Call"]
    end

    User --> FE
    FE --> API
    API --> GP
    API --> SC
    GP -->|"Structured plan"| SC
    OB -->|"User patterns"| SC
    SN -->|"Current context"| SC
    EM -->|"Emotional state"| SC
    SC <-->|"NL + Tool Calling"| LLM
    GP <--> LLM
    SC --> DB
    SC --> RAG
    SC --> N
    N --> Push
    N --> WA
    N --> Call
```

Flux uses a **multi-agent architecture** where five specialized AI agents work in concert. The **Goal Planner** decomposes user goals into weekly milestones and daily tasks through empathetic dialogue. The **Scheduler** is the core orchestrator — it manages time-blocking, conflict resolution, drift recovery, and coordinates inputs from all other agents. The **Observer** tracks behavioral patterns over time (e.g., "you always skip gym on Mondays") and feeds scheduling preferences back to the Scheduler. The **Sensor** infers real-time user context from device signals — location, phone state, calendar status — to adjust nudge timing. The **Empath** gauges emotional state from voice input to modulate tone and urgency. All agents share GPT-4o-mini as their language backbone, with a RAG-powered vector database providing personalized, history-aware context.

---

## AI Agents

| Agent | Purpose | Key Behavior |
|-------|---------|-------------|
| 🎯 **Goal Planner** | Transforms vague goals into structured plans | Multi-turn empathetic dialogue; weekly milestones; recurring task creation |
| 🗓️ **Scheduler** | Core orchestrator for all calendar operations | Conflict resolution; drift recovery; negotiation when no perfect slot exists |
| 🔍 **Observer** | Learns user behavior patterns over time | Detects aversions (e.g., Monday gym skips); suggests preference updates weekly |
| 📍 **Sensor** | Infers real-time context from device signals | GPS, phone state, calendar status; adjusts nudge timing; 100% on-device processing |
| 💚 **Empath** | Gauges emotional state from voice input | Stressed → reduce nudges; low energy → suggest lighter tasks; upbeat → tackle challenges |

---

## Getting Started

### Prerequisites

- **Node.js 18+** — [Install](https://nodejs.org)
- **Python 3.11+** — [Install](https://python.org)
- **Docker Desktop** — [Install for Mac](https://docs.docker.com/desktop/install/mac-install/) (must be running)
- **Supabase CLI** — Install via Homebrew:
  ```bash
  brew install supabase/tap/supabase
  ```

### Quick Start (Recommended)

```bash
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8

# 1. Install frontend & backend dependencies
bash scripts/setup.sh

# 2. Set up Supabase (Docker Desktop must be running)
bash scripts/supabase_setup.sh
```

> **Note:** The first Supabase run downloads ~2-3 GB of Docker images. Subsequent runs are fast.

After setup completes:

```bash
# Terminal 1 — Frontend
cd frontend && npm run dev

# Terminal 2 — Backend
cd backend && source venv/bin/activate && uvicorn main:app --reload
```

### Supabase Local Development

Supabase runs entirely in Docker on your machine. No cloud account needed for local dev.

| Service | URL |
|---------|-----|
| Studio (Dashboard) | http://127.0.0.1:54323 |
| API (Project URL) | http://127.0.0.1:54321 |
| Database | `postgresql://postgres:postgres@127.0.0.1:54322/postgres` |
| Email Testing (Mailpit) | http://127.0.0.1:54324 |

**Useful commands:**

```bash
supabase status    # Show local URLs and keys
supabase stop      # Stop all Supabase containers
supabase start     # Restart (fast after first run)
supabase db reset  # Reset database and re-apply all migrations
```

**Setting up the database with test data:**

After `supabase start` (or as part of initial setup), run:

```bash
# Apply migrations (creates all tables)
supabase db reset

# Load sample data for development
docker cp supabase/scripts/seed_test_data.sql supabase_db_Flux-Team-8:/tmp/seed_test_data.sql
docker exec supabase_db_Flux-Team-8 psql -U postgres -f /tmp/seed_test_data.sql
```

This seeds 3 users, 4 goals, 8 milestones, 7 tasks, 3 conversations, and demo flags — enough to exercise every feature locally.

**Other database utility scripts:**

| Script | Purpose | Command |
|--------|---------|---------|
| `truncate_tables.sql` | Delete all rows, keep schema | `docker cp supabase/scripts/truncate_tables.sql supabase_db_Flux-Team-8:/tmp/truncate_tables.sql && docker exec supabase_db_Flux-Team-8 psql -U postgres -f /tmp/truncate_tables.sql` |
| `drop_tables.sql` | Drop all tables and enums | `docker cp supabase/scripts/drop_tables.sql supabase_db_Flux-Team-8:/tmp/drop_tables.sql && docker exec supabase_db_Flux-Team-8 psql -U postgres -f /tmp/drop_tables.sql` |

> For full database schema details, enum definitions, and entity relationships, see [`supabase/README.md`](supabase/README.md).

### Manual Installation

If you prefer to set things up step by step:

```bash
# Clone the repository
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8

# Frontend
cd frontend
npm install
cp .env.example .env
cd ..

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd ..

# Supabase (Docker Desktop must be running)
supabase start
supabase db reset

# Seed test data (optional but recommended)
docker cp supabase/scripts/seed_test_data.sql supabase_db_Flux-Team-8:/tmp/seed_test_data.sql
docker exec supabase_db_Flux-Team-8 psql -U postgres -f /tmp/seed_test_data.sql
```

---

## Project Structure

```
flux/
├── frontend/          # React + Vite + TypeScript
│   ├── src/
│   │   ├── api/       # API integration layer
│   │   ├── components/# Reusable UI components
│   │   ├── hooks/     # Custom React hooks
│   │   ├── pages/     # Route pages
│   │   ├── styles/    # Global styles & theme
│   │   ├── types/     # TypeScript definitions
│   │   └── utils/     # Helper functions
│   ├── public/
│   └── package.json
├── backend/           # FastAPI + Python
│   ├── app/
│   │   ├── agents/    # AI agent modules
│   │   ├── api/       # Route handlers
│   │   ├── models/    # Database models
│   │   └── services/  # Business logic
│   ├── tests/
│   └── requirements.txt
├── docs/              # Documentation
└── README.md
```

---

## Development Workflow

- **Branches:** `feature/<name>`, `bugfix/<name>`, `hotfix/<name>`
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`)
- **PRs:** Require 1 review, must pass linting and type-check
- **Testing:** Unit tests for utilities, integration tests for API layer

---

## Roadmap

- [x] Week 1: Foundation — Project setup, routing, mock API (Feb 10–16)
- [ ] Week 2: Core Features — Calendar view, goal chat, task management (Feb 17–23)
- [ ] Week 3: AI Agents — Planner, scheduler, nudge agents (Feb 24–Mar 2)
- [ ] Week 4: Polish & Demo — Animations, edge cases, demo mode (Mar 3–9)

---

## Scope

| Capability | v1 (MVP Demo) | v2 (Post-Launch) |
|-----------|---------------|-----------------|
| **Goal Categories** | Health & Fitness only | Career, Personal, Finance, Learning, Relationships |
| **Goal Timeline** | Up to 6 months | Multi-year with quarterly reviews |
| **Plan Depth** | High-level weekly milestones | Deep plans (calories, specific workouts, curricula) |
| **Calendar Sync** | Internal Flux calendar only | Google Calendar two-way sync |
| **Pattern Learning** | Hard-coded demo scenarios | Lightweight RL model tracking accept/reject/miss rates |
| **Context Awareness** | Simulated via demo controls | On-device ML (TensorFlow Lite) for location and phone state |
| **Sentiment Detection** | Keyword-based tone adjustment | On-device speech emotion recognition |
| **Cold Storage** | Static parking lot view | Full chronic-avoidance detection with weekly review prompts |
| **Notification Channels** | Push + 1 WhatsApp + 1 call path | Email, rich WhatsApp quick replies, full VoIP |
| **External Integrations** | None | Apple Health, Fitbit, Strava, MyFitnessPal |

---

## Guardrails

**Tone Safety** — Flux never uses shaming language. If a task is missed, responses use neutral or supportive phrasing: *"Let's find a better time"* rather than *"You failed again."*

**Privacy by Design** — Context awareness (location, phone state) uses on-device processing only. No location data leaves the device. Voice interactions produce transcripts and emotion labels — raw audio is never stored.

**Explainability** — When suggesting a new time slot, Flux displays a brief rationale: *"Suggested 6 PM because you prefer evening workouts and 5 PM was blocked."*

**Consent & Control** — All sensor-based features require explicit opt-in with granular permissions. Users can disable any data signal at any time; the AI falls back to time-based heuristics.

---

## Demo Day

- **Date:** Early March 2026
- **Duration:** 15–20 minutes
- **Key flows:** Goal creation → schedule generation → drift handling → recovery

---

## Demo Mode

Flux includes an integrated sandbox that lets anyone experience its failure-handling flows without waiting for real time to pass.

**Activation:** Toggle "Demo Mode" in Settings → a floating control panel appears over the normal UI.

| Control | What It Does |
|---------|-------------|
| **Time Warp** | Slider to fast-forward 1–24 hours, triggering drift detection on passed tasks |
| **Force Miss** | Select any upcoming task → immediately mark as drifted → triggers ghost animation |
| **Simulate Leaving Home** | Fires context-aware reminder cascade (grocery nudge with hardcoded distance) |
| **Escalation Speed** | 1x / 5x / 10x multiplier for the push → WhatsApp → call notification ladder |
| **Reset State** | Returns to fresh demo with pre-seeded sample tasks and goals |

**Pre-seeded demo data:** One user with a "Lose weight for a wedding" goal, weekly milestones, recurring gym tasks, a grocery reminder, and one must-not-miss task for escalation demonstration.

### Sample Demo Flow

```mermaid
sequenceDiagram
    participant D as Demonstrator
    participant F as Flux App
    participant A as Audience

    Note over D,A: 1. Show Clean Dashboard
    D->>F: Calendar with 3–5 tasks visible
    F-->>A: Fluid UI with time-blocked tasks

    Note over D,A: 2. Force Miss a Task
    D->>F: Click "Force Miss" on Gym at 10 AM
    F-->>A: Task ghosts with fade animation

    Note over D,A: 3. AI Negotiation
    F->>D: "Gym drifted. I can do 5 PM or tomorrow 7 AM"
    D->>F: Selects "Tomorrow 7 AM"
    F-->>A: Task smoothly animates to tomorrow's slot

    Note over D,A: 4. Escalation Demo
    D->>F: Trigger escalation on must-not-miss task
    F-->>A: Push notification → WhatsApp message → Call UI
```

---

## Team

| Name | Role | GitHub |
|------|------|--------|
| Harshal Kale | Team Leader | [@harshalkale](https://github.com/harshalkale) |
| Session Mwamufiya | | [@placeholder](#) |
| Krishnan Iyer | | [@kiyer1974](https://github.com/kiyer1974) |
| Sathish Kulal | | [@placeholder](#) |
| Hima | | [@placeholder](#) |
| Kavish Jaiswal | | [@MacDavicK](https://github.com/MacDavicK) |

---

## Contributing

Contributions are welcome! Whether it's bug fixes, new features, or documentation improvements, we appreciate your help. Please read our [Contributing Guide](docs/CONTRIBUTING.md) for details on the development process, coding standards, and how to submit pull requests.

---

## License

MIT License © 2026 Flux Team. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **Outskill AI Engineering Fellowship** — Cohort 3
- **Mentor:** Ramanathan Rm
- Built with React, FastAPI, and Supabase

---

⭐ Star this repo if you find it helpful!

# USER_FLOWS.md

> **Purpose:** Complete user flow documentation for Flux — a goal/task management web app. This document is intended as a development reference for Claude Code.
> **Stack:** React + Vite (frontend), FastAPI + Supabase (backend).

---

## App Overview

Flux is a productivity web app that helps users set goals and manage daily tasks through a conversational chatbot interface. Users interact with a chatbot to define goals, which are broken down into structured plans and daily tasks. Notifications are delivered via push notifications, WhatsApp, and calls (IVR) using an escalation matrix.

---

## Screens

| Screen | Route | Description |
|---|---|---|
| **Splash** | N/A (overlays any route) | Full-screen splash shown on every initial app load, regardless of route. Auto-dismisses after session check completes. |
| **Login** | `/login` | Authentication screen. Shown to unauthenticated users after splash. |
| **Flow** | `/` | Home screen. Shows the current day's task list for the logged-in user. |
| **Chat** | `/chat` | Chat interface. Used for onboarding and ongoing goal/task management. |
| **Reflection** | `/reflection` | Profile/account dashboard. Displays user info, metrics, and activity progress widgets. |

---

## Layout Components

### Bottom Nav
- Floating navigation bar, fixed to viewport bottom.
- Links to **Flow** (`/`), **Chat** (`/chat`), and **Reflection** (`/reflection`).
- **Not rendered** on the Login screen or during active onboarding.
- Becomes visible once onboarding is marked complete.

---

## Authentication & Session States

| User State | Condition | Post-Splash Destination |
|---|---|---|
| Unauthenticated | No valid session | `/login` |
| Authenticated + Onboarding incomplete | Session exists, `onboarding_completed: false` | `/chat` (Onboarding mode, no Bottom Nav) |
| Authenticated + Onboarding complete | Session exists, `onboarding_completed: true` | `/` (Flow Screen) |

---

## Flows

### 1. First-Time Landing (New User)

**Trigger:** User visits the app with no existing session.

**Steps:**
1. Splash screen displays (auto-dismisses once session check completes).
2. User is redirected to `/login`.
3. Login screen presents three options: **Log In**, **Sign Up**, **Continue with Google**.
4. User completes authentication (email/password or Google OAuth).
5. On successful **new account creation**, user is redirected to `/chat` in **Onboarding mode**.
   - Bottom Nav is **not rendered**.
   - `/` and `/reflection` are **inaccessible** (route-guarded).

**Error States:**
- Invalid credentials → inline error displayed on the form.
- OAuth failure → error message shown with retry option.

---

### 2. Returning User Landing

**Trigger:** User visits the app with a valid, active session and `onboarding_completed: true`.

**Steps:**
1. Splash screen displays (auto-dismisses).
2. User is redirected to `/` (Flow Screen).
3. Bottom Nav is rendered and fully accessible.

---

### 3. Returning User with Incomplete Onboarding

**Trigger:** User previously signed up but closed the app before completing onboarding (`onboarding_completed: false`).

**Steps:**
1. Splash screen displays (auto-dismisses).
2. User is redirected to `/chat` in **Onboarding mode**.
3. Onboarding resumes — the chatbot picks up from where the conversation left off (chat history is preserved).
4. Bottom Nav remains hidden until onboarding is complete.

---

### 4. Onboarding

**Trigger:** Any authenticated session where `onboarding_completed: false`.

**Steps:**
1. User is on `/chat` in Onboarding mode.
2. The chatbot initiates the conversation with onboarding questions (e.g., name, focus areas, first goal intent).
3. The chatbot walks the user through setting up their **first goal** (see Goal Planning flow).
4. Once the first goal is accepted and saved:
   - `onboarding_completed` is set to `true` in the database.
   - User is transitioned to the **Flow Screen** (`/`).
   - Bottom Nav becomes visible.

**Constraints:**
- User cannot navigate away from `/chat` during onboarding (all other routes are guarded).
- No Bottom Nav during this phase.

---

### 5. Chat (General — Post-Onboarding)

**Trigger:** User navigates to `/chat` after onboarding is complete.

**Purpose:** The user can converse with the chatbot to:
- **Set a new goal** (triggers Goal Planning flow).
- **Create a standalone task** (a one-off task not linked to any goal).

**Chat Thread Model:**
- Each goal and each standalone task has its **own separate chat thread**.
- The Chat Screen displays threads; user can switch between them or start a new one.
- Chat history per thread is persisted in Supabase.

---

### 6. Goal Planning / Setting

**Trigger:** User expresses a goal intent in the Chat Screen (e.g., _"I want to learn Japanese"_).

**Steps:**
1. Chatbot identifies the goal intent and opens a **new chat thread** for this goal.
2. Bot asks clarifying questions to gather context (e.g., target timeline, current experience level, weekly availability).
3. Bot generates and presents a **suggested plan** — a structured breakdown of milestones and recurring tasks.
4. User **accepts the plan** by either:
   - Typing an affirmative reply (e.g., "Ok", "Looks good", "Yes"), or
   - Clicking the **"Accept" button** rendered inline in the chat.
5. On acceptance, the chatbot displays **inline status messages** reflecting background processing:
   - _"Creating your goal…"_
   - _"Scheduling your tasks…"_
   - _"All set! Your plan is live."_
6. Generated tasks are added to the user's **Flow Screen** task list.

**UI States during acceptance:**
- Loading/processing indicator in chat while backend processes.
- Success confirmation message from bot.
- Error state if goal creation fails, with a retry option.

---

### 7. Flow Screen — Task List

The Flow Screen (`/`) shows **two types of items** for the current day:

| Type | Description | Display Position |
|---|---|---|
| **Events (Time-based)** | Tasks with a specific scheduled time | Listed chronologically |
| **Todos** | Standalone tasks not tied to a specific time | Shown above events, as a todo list |

**Direct Interaction:**
- Users can interact with tasks directly on the Flow Screen (e.g., mark as done, reschedule).
- If a user manually marks a task as done or takes action on it directly in the app, **no notification is sent** for that task — the notification system only activates for tasks that haven't been interacted with.
- Task status changes made directly on the Flow Screen are immediately reflected in the database.

---

### 8. Task / Event Notifications

Flux uses a **notification escalation matrix** — if the user does not respond to a notification, it escalates to the next channel:

```
Push Notification → WhatsApp → Call (IVR)
```

Escalation timing is **system-wide** (not per-user configurable). Calls use IVR but **do not support rescheduling via IVR** — if the user needs to reschedule, they are directed to open the app.

There are **three notification categories:**

---

#### 8a. Upcoming Task/Event Notification

**Trigger:** Task/event is approaching its scheduled start time.

**Purpose:** Inform the user of an imminent task — no status change required, just acknowledgment.

| Channel | User Action |
|---|---|
| Push Notification | "Acknowledge" button |
| WhatsApp | "Ok" reply option |
| Call (IVR) | "Press 1 to acknowledge" |

**App Behavior (web):**
- Tapping the notification opens the app to the relevant task.
- Status update process indicator is shown while acknowledgment is recorded.
- On success, task is marked as **Acknowledged** in the DB.

---

#### 8b. Check-in Notification

**Trigger:** Sent after a configured duration from the task/event's **start time**, but **only if the task duration is greater than 30 minutes**. If the task duration is ≤ 30 minutes, this check-in is skipped and the system moves directly to the Past Task/Event notification (8c).

**Purpose:** Nudge the user to confirm they are actively working on the task.

| Channel | Options |
|---|---|
| Push Notification | "Doing it" or "Reschedule" |
| WhatsApp | "Doing it" or "Reschedule" reply options |
| Call (IVR) | IVR option to acknowledge; reschedule not available via IVR — user directed to open app |

**"Doing it" behavior:**
- Marks the task as **In Progress** in the DB.
- No further check-in notification sent.
- The system will still send a **Past Task/Event** notification (8c) once the task's completion time passes, if the user hasn't marked it done.

**"Reschedule" behavior:**
- User is taken to the **Chat Screen** (`/chat`).
- The relevant goal/task chat thread is opened.
- A reschedule message is **pre-filled** in the chat input: _"I want to reschedule [Task Name]"_.
- The chatbot assists the user in selecting a new time/date.
- On confirmation, the task is updated in the DB and reflected on the Flow Screen.

**App UI States (web):**
- Loading/processing state while status update is in progress.
- Success confirmation state once recorded.
- Error state with retry option if update fails.

---

#### 8c. Past Task/Event Notification (Missed Task Follow-up)

**Trigger:** Task/event completion time has passed and the user has **not** marked it as "Done" or "Reschedule" — either via notification or direct interaction on the Flow Screen.

**Behavior:**
- Notification is sent to verify task progress.
- Sent a **maximum of 3 times**, at **2-hour intervals**.
- If no response after all 3 attempts → task is automatically marked as **"Missed"** in the DB.

| Channel | Options |
|---|---|
| Push Notification | "Already Done" or "Reschedule" |
| WhatsApp | "Already Done" or "Reschedule" reply options |
| Call (IVR) | Acknowledge only; reschedule not available via IVR |

**"Already Done" behavior:**
- Task is marked as **Completed** in the DB.
- Success state shown in app.

**"Reschedule" behavior:**
- Same as 8b — user taken to `/chat`, relevant thread opened, reschedule message pre-filled.

**App UI States (web):**
- All in-app notification interactions show appropriate loading/processing states.
- Success and error states shown after each action.

---

## Routing & State Flow

```
App Load (any route)
  └── Splash Screen
        ├── [No Session]
        │     └── /login
        │           ├── Log In / Sign Up / Google OAuth
        │           ├── [Existing User] → / (Flow Screen)
        │           └── [New User] → /chat (Onboarding mode)
        │                 └── [Onboarding Complete] → / (Flow Screen + Bottom Nav)
        │
        └── [Active Session]
              ├── [onboarding_completed: false] → /chat (Onboarding mode, resume)
              └── [onboarding_completed: true]  → / (Flow Screen)
```

---

## Key Data Flags

| Flag | Location | Values | Purpose |
|---|---|---|---|
| `onboarding_completed` | User profile (Supabase) | `true` / `false` | Controls onboarding mode and Bottom Nav visibility |
| Task `status` | Task record (Supabase) | `pending`, `acknowledged`, `in_progress`, `completed`, `missed`, `rescheduled` | Drives notification logic and Flow Screen display |
| Task `duration_minutes` | Task record (Supabase) | Integer (minutes) | Determines whether check-in notification (8b) is sent (`> 30` = send check-in) |
| `notification_attempt_count` | Task/notification record | `0–3` | Tracks Past Task notification send count; auto-marks missed at 3 |

# Flux — Integration Test Checklist

**Purpose:** Verify full FE↔BE integration after backend and frontend are wired. Use after running the pre-flight script (`scripts/preflight.sh`) and the backend API integration test (`backend/scripts/integration_test.py`). This doc is the **manual frontend walkthrough**.

---

## Part 2: Frontend Manual Walkthrough

### Setup

```bash
# Terminal 1 — Backend
cd ~/Downloads/Flux/backend
source venv/bin/activate  # or .venv
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd ~/Downloads/Flux/frontend
npm run dev
```

Open the app in your browser at **http://localhost:3000** (or the port shown by `npm run dev`).

---

### Checklist

#### A. Connectivity

- [ ] Open DevTools → Console
- [ ] No "Backend unavailable" warning (useBackendReady passed)
- [ ] Network tab: GET /health or /api/v1/health returns 200

#### B. Onboarding (use incognito or new test account)

- [ ] App redirects to /onboarding (not /chat or /)
- [ ] Progress bar visible at top (starts at 0%)
- [ ] First AI message appears: "Hey! I'm Flux..."
- [ ] Input placeholder shows "Your name..."
- [ ] Type name → AI responds with wake time question
- [ ] Progress bar advances (~14%)
- [ ] Type "7am" → sleep time question
- [ ] Type "11pm" → work schedule question
- [ ] Type "9 to 5" → chronotype question
- [ ] Type "morning person" → commitments question
- [ ] Type "Gym on Tuesdays at 7pm" → completion message
- [ ] Celebration animation appears
- [ ] After ~2s, auto-navigates to home screen
- [ ] Refreshing does NOT re-trigger onboarding

#### C. Home Screen (post-onboarding)

- [ ] Task rail loads (may be empty for new user — that's OK)
- [ ] No console errors
- [ ] Loading skeleton appears briefly then resolves

#### D. Chat — Goal Planning

- [ ] Navigate to chat screen
- [ ] Type "I want to lose 5kg"
- [ ] AI responds with questions (context extraction)
- [ ] Continue conversation until plan is proposed
- [ ] Plan card renders with task list and days/times
- [ ] **Sources section visible** at bottom of plan card
  - [ ] Shows article titles with links
  - [ ] Links open in new tab
- [ ] If no RAG match: fallback banner appears ("I don't have expert guidance...")
- [ ] Accept plan → tasks created
- [ ] Navigate to home → new tasks appear in task rail

#### E. Task Actions

- [ ] Tap "Mark Done" on a task → status updates, UI refreshes
- [ ] (If "Mark Missed" exists) → status updates

#### F. Scheduler (if drifted task exists)

- [ ] Drifted task shows "Shuffle?" button
- [ ] Tap → modal opens → suggestions load from API
- [ ] Select option → task moves → modal closes
- [ ] "Skip Today" → task removed, next occurrence preserved

#### G. Analytics Dashboard

- [ ] Navigate to "Progress" tab in bottom nav
- [ ] Overview tab:
  - [ ] Streak card shows (may be 0 for new user)
  - [ ] Weekly chart renders (may be empty)
  - [ ] Activity heatmap renders (365-day grid)
  - [ ] Missed by category chart renders (may be empty)
- [ ] Goals tab:
  - [ ] Active goals listed with progress bars
  - [ ] Expand a goal → milestones/task count shown
- [ ] Patterns tab: "Coming soon" placeholder
- [ ] No console errors on any tab

#### H. Edge Cases

- [ ] Refresh on /analytics → still renders (not 404)
- [ ] Refresh on /chat mid-conversation → reconnects (or shows error)
- [ ] Kill backend → frontend shows "Backend unavailable" / mock mode
- [ ] Restart backend → frontend recovers on next action

---

## Part 3: Known Issues / Expected Failures

| Test | Expected Result | Why |
|------|-----------------|-----|
| Scheduler suggest with fake ID | 400 or 404 | No real drifted task exists |
| Analytics for new user | Empty charts, streak=0 | No task history yet |
| GET /analytics/heatmap | 404 | Heatmap lives inside /overview |
| Onboarding LLM parsing | May timeout if OpenRouter is slow | Add TEST_EMAIL user with pre-set profile as fallback |
| CORS preflight | May not return header on OPTIONS if FastAPI CORS isn't fully configured | Check middleware order in main.py |

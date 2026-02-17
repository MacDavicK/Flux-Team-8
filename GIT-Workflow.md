# 🎯 Flux — Git Workflow Guide

**Team 8 · Outskill AI Fellowship C3**

---

## How Our Repo Is Set Up

We have one main repository with these branches:

```
main             ← Protected. The stable version of Flux.
├── frontend     ← All frontend (React/Vite) work goes here.
├── backend      ← All backend (FastAPI) work goes here.
├── data_access  ← Database and data layer work.
└── feature/*    ← Short-lived branches for specific tasks.
```

**The `main` branch is protected.** No one can push directly to it or merge a PR into it without 3 contributors' approval. This is intentional — `main` always contains working, reviewed code.

All other branches (`frontend`, `backend`, `data_access`, and any feature branches) are open for merging without approval.

---

## Before You Start (One-Time Setup)

### 1. Accept Your Collaborator Invite

Check your email or go to [github.com/notifications](https://github.com/notifications). You should have a repository invitation — click **Accept**. You won't be able to push anything until you do this.

### 2. Authenticate Git on Your Machine

If you haven't already, install the GitHub CLI and log in:

```bash
# Install GitHub CLI (pick your OS)
# macOS:
brew install gh

# Windows:
winget install --id GitHub.cli

# Ubuntu/Debian:
sudo apt install gh
```

Then authenticate:

```bash
gh auth login
```

Choose **GitHub.com → HTTPS → Login with a web browser**, and follow the prompts.

### 3. Clone the Repo

```bash
git clone https://github.com/MacDavicK/Flux.git
cd Flux
```

If you already cloned it, make sure you're up to date:

```bash
git fetch --all
```

---

## Day-to-Day Workflow

### Step 1 — Start from the right branch

Before writing any code, make sure you're on the correct base branch for your work:

```bash
# Pull the latest changes first
git checkout backend       # or frontend, data_access, etc.
git pull origin backend
```

### Step 2 — Create a feature branch (recommended)

Working directly on `backend` or `frontend` is okay for small changes. For anything substantial, create a feature branch:

```bash
git checkout -b feature/your-task-name
```

**Naming convention:**
- `feature/add-login-page`
- `feature/scrum-45-phone-call-trigger`
- `fix/calendar-date-bug`

### Step 3 — Make your changes, commit often

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "feat: add phone call trigger API endpoint"
```

**Commit message format** — keep it short and descriptive:
- `feat: add user authentication flow`
- `fix: resolve date parsing error in scheduler`
- `docs: update API endpoint documentation`
- `refactor: simplify goal breakdown logic`

### Step 4 — Push your branch

```bash
git push origin feature/your-task-name
```

If it's your first push for this branch, Git may ask you to set the upstream:

```bash
git push --set-upstream origin feature/your-task-name
```

### Step 5 — Open a Pull Request

1. Go to the repo on GitHub — you'll usually see a yellow banner saying "Compare & pull request." Click it.
2. **Important: Check the base branch.** Make sure the PR targets the correct branch:
   - Working on frontend? Target → `frontend`
   - Working on backend? Target → `backend`
   - Working on data layer? Target → `data_access`
   - **Do NOT target `main`** unless specifically told to.
3. Write a short description of what you changed and why.
4. Click **Create pull request**.

### Step 6 — Request a Copilot Review (Optional but Recommended)

In the PR sidebar, click **Reviewers** → select **Copilot**. It will scan your code in about 30 seconds and leave comments if it spots issues. Address any feedback, push fixes, and you're good.

### Step 7 — Merge

For PRs into `frontend`, `backend`, or `data_access` — you can merge it yourself once you're satisfied. No approval needed.

For PRs into `main` — Kavish will review and merge. Don't merge into `main` on your own.

---

## Common Situations

### "I accidentally made my PR target `main`"

No worries — click **Edit** at the top-right of the PR, change the base branch to the correct one (e.g., `backend`), and save.

### "I need to update my branch with the latest changes from `backend`"

```bash
git checkout feature/your-task-name
git pull origin backend
```

If there are merge conflicts, Git will tell you which files to fix. Open them, resolve the conflicts (look for `<<<<<<<` markers), then:

```bash
git add .
git commit -m "merge: resolve conflicts with backend"
git push
```

### "I want to see what branches exist"

```bash
git branch -a
```

### "My push was rejected"

This usually means someone else pushed changes to the same branch. Pull first, then push:

```bash
git pull origin your-branch-name
git push
```

### "I'm getting authentication errors"

Re-authenticate with GitHub CLI:

```bash
gh auth login
```

Or check that your Personal Access Token hasn't expired if you're using HTTPS tokens.

---

## The Golden Rules

1. **Never push directly to `main`.** Always use a PR.
2. **Always check your PR's base branch** before submitting. Target `frontend`, `backend`, or `data_access` — not `main`.
3. **Pull before you push.** Run `git pull` before starting work to avoid conflicts.
4. **Commit often with clear messages.** Small, focused commits are easier to review and revert if needed.
5. **When in doubt, ask.** It's better to clarify than to accidentally overwrite someone else's work.

---

## Quick Reference Card

| I want to... | Command |
|---|---|
| Switch to a branch | `git checkout branch-name` |
| Create a new branch | `git checkout -b feature/my-task` |
| Pull latest changes | `git pull origin branch-name` |
| Stage all changes | `git add .` |
| Commit | `git commit -m "feat: description"` |
| Push | `git push origin branch-name` |
| See all branches | `git branch -a` |
| Check current branch | `git branch` |
| See what changed | `git status` |

---

*Last updated: 15th February 2026*

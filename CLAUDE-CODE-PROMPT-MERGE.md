# Claude Code CLI Prompt: Branch Integration Merge

## Context

You are working on the **Flux** project (AI-powered goal & task management app).  
Repo: `~/Downloads/Flux` (local) / `MacDavicK/Flux-Team-8` (GitHub)  
I am the repo owner with force-push access.

The repo has accumulated 10 branches. An audit has been completed. Your job is to execute a **safe, ordered merge** of all unmerged branches into an integration branch, then push it for PR into `main`.

---

## Branch Audit Summary (already verified — trust these facts)

### Already merged into `main` (0 commits ahead) — DELETE these after merge:
- `origin/frontend` — merged via PR #15
- `origin/SCRUM-43-Phone-Call-Trigger` — 0 ahead
- `origin/sessionWorkbench` — 0 ahead
- `origin/data_access_v2` — merged via PR #12
- `origin/data_access` — merged via earlier PR
- `origin/users/sathish/scrum24` — merged into data_access

### Unmerged branches (action required):

| Branch | Commits Ahead of main | Content |
|---|---|---|
| `origin/backend` (HEAD: `1909c31`) | 1 | Scheduler BE + FE (mixed), goal_planner fix, .gitignore |
| `origin/feature/scheduler-fe` (HEAD: `13f4c15`) | 1 | SCRUM-33+34: NegotiationModal + Voice (7 FE files) |
| `origin/conv_agent` (HEAD: `63aace4`) | 5 | Docs only: `docs/conv_agent/` + `docs/conversational_agent_design.md` + `.python-version` + `.gitignore` |
| `origin/feature/ci-automated-testing` (HEAD: `8688a26`) | 1 | CI workflows (.github/), test scaffolding, FE config changes |

### Known Conflict Zone

`origin/backend` and `origin/feature/scheduler-fe` BOTH modify these 5 files:
```
frontend/src/components/flow/v2/FlowTimeline.tsx
frontend/src/components/flow/v2/TimelineEvent.tsx
frontend/src/components/modals/RescheduleModal.tsx
frontend/src/routes/index.tsx
frontend/src/utils/api.ts
```

`origin/backend` (`1909c31`) is **newer** and contains the latest working version of these files.  
`origin/feature/scheduler-fe` (`13f4c15`) is **older** but has 2 unique files not in `backend`:
- `frontend/src/types/speech.d.ts`
- `frontend/src/utils/useVoiceNegotiation.ts`

**Resolution strategy:** For the 5 overlapping files, KEEP the `backend` branch version. Cherry-pick only the 2 unique voice files from `feature/scheduler-fe`.

---

## Execution Plan — Follow This Exact Order

### Step 0: Safety — Fetch and verify
```bash
cd ~/Downloads/Flux
git fetch --all
git status  # must be clean working tree
```
If working tree is dirty, stash or commit first. Do NOT proceed with uncommitted changes.

### Step 1: Create integration branch from main
```bash
git checkout origin/main -b integration/pre-release
```
Verify: `git log --oneline -1` should show `aa6e809 Merge pull request #14 from MacDavicK/backend`

### Step 2: Merge `conv_agent` (ZERO risk — docs only)
```bash
git merge origin/conv_agent --no-ff -m "merge: integrate conv_agent docs into pre-release"
```
- Expected: Clean auto-merge. Only adds files under `docs/conv_agent/`, `docs/conversational_agent_design.md`, `.python-version`, and `.gitignore` update.
- If `.gitignore` conflicts: accept BOTH sides (union merge). The conv_agent branch adds `.claude` to gitignore.
- **Verify:** `git diff HEAD~1 --stat` — should show only doc files + .gitignore + .python-version.

### Step 3: Merge `feature/ci-automated-testing` (LOW risk)
```bash
git merge origin/feature/ci-automated-testing --no-ff -m "merge: integrate CI workflows and test scaffolding"
```
- Expected: Mostly clean. Adds `.github/workflows/`, `backend/tests/`, `frontend/vitest.config.ts`, etc.
- **Likely conflict files:** `frontend/package.json`, `frontend/biome.json`, `frontend/src/components/flow/v2/FlowTimeline.tsx`, `frontend/src/routes/index.tsx`
- **Conflict resolution strategy:**
  - `frontend/package.json`: Accept the CI branch additions (test deps like vitest) ON TOP of main's existing deps. Ensure both sets of dependencies are present.
  - `frontend/biome.json`: Accept CI branch version (adds linting rules).
  - `FlowTimeline.tsx` and `index.tsx`: Accept main's version for now (backend branch in Step 4 has the latest).
  - All other files: Accept CI branch version (new files, no overlap).
- **Verify:** `git diff HEAD~1 --stat` — should show CI yaml files, test files, FE config updates.

### Step 4: Merge `backend` (MEDIUM risk — the big one)
```bash
git merge origin/backend --no-ff -m "merge: integrate scheduler agent BE+FE (SCRUM-30)"
```
- Expected: May conflict on FE files that CI branch also touched (`FlowTimeline.tsx`, `index.tsx`).
- **Conflict resolution strategy:**
  - For ALL 10 files in the `backend` branch commit: **ACCEPT the `backend` branch version**. This is the latest, tested version of the scheduler implementation.
  - Specifically: `frontend/src/components/flow/v2/FlowTimeline.tsx`, `frontend/src/components/flow/v2/TimelineEvent.tsx`, `frontend/src/components/modals/RescheduleModal.tsx`, `frontend/src/routes/index.tsx`, `frontend/src/utils/api.ts` — use backend's version.
  - `backend/app/agents/scheduler_agent.py`, `backend/app/routers/scheduler.py`, `backend/app/services/scheduler_service.py`, `backend/app/agents/goal_planner.py`, `.gitignore` — use backend's version (no conflict expected on these).
- **Verify:** `git diff HEAD~1 --stat` — should show ~10 files, 388 insertions.

### Step 5: Cherry-pick voice files from `feature/scheduler-fe`
Do NOT merge the full branch (it would conflict on all 5 shared files). Instead:
```bash
git checkout origin/feature/scheduler-fe -- frontend/src/types/speech.d.ts
git checkout origin/feature/scheduler-fe -- frontend/src/utils/useVoiceNegotiation.ts
git add frontend/src/types/speech.d.ts frontend/src/utils/useVoiceNegotiation.ts
git commit -m "feat(voice): add speech types and useVoiceNegotiation hook from SCRUM-34"
```
- These are NEW files that don't exist in any other branch — guaranteed no conflicts.
- **Verify:** `git show --stat HEAD` — should show exactly 2 files added.

### Step 6: Smoke Tests

**Backend check:**
```bash
cd ~/Downloads/Flux/backend
# Activate your venv if needed
python -c "from app.main import app; print('✅ Backend imports OK')"
python -c "from app.agents.scheduler_agent import SchedulerAgent; print('✅ SchedulerAgent imports OK')"
python -c "from app.services.rag_service import RAGService; print('✅ RAGService imports OK')"
```

**Frontend check:**
```bash
cd ~/Downloads/Flux/frontend
npx tsc --noEmit 2>&1 | head -20
# If clean: "✅ TypeScript OK"
# If errors: list them but do NOT fix — flag for Cursor review
```

**File existence checks:**
```bash
cd ~/Downloads/Flux
echo "=== Backend files ==="
ls -la backend/app/agents/scheduler_agent.py
ls -la backend/app/agents/goal_planner.py
ls -la backend/app/services/scheduler_service.py
ls -la backend/app/routers/scheduler.py
ls -la backend/app/services/rag_service.py

echo "=== Frontend files ==="
ls -la frontend/src/utils/api.ts
ls -la frontend/src/utils/useVoiceNegotiation.ts
ls -la frontend/src/types/speech.d.ts
ls -la frontend/src/components/modals/RescheduleModal.tsx
ls -la frontend/src/components/flow/v2/FlowTimeline.tsx
ls -la frontend/src/components/flow/v2/TimelineEvent.tsx

echo "=== CI files ==="
ls -la .github/workflows/backend-ci.yml
ls -la .github/workflows/frontend-ci.yml

echo "=== Docs ==="
ls -la docs/conv_agent/README.md
```

### Step 7: Push integration branch
```bash
git push origin integration/pre-release
```
Then create a PR from `integration/pre-release` → `main` on GitHub.

### Step 8: Delete stale remote branches (AFTER PR is merged)
Only run this AFTER the PR into main is merged and confirmed:
```bash
git push origin --delete frontend
git push origin --delete SCRUM-43-Phone-Call-Trigger
git push origin --delete sessionWorkbench
git push origin --delete data_access_v2
git push origin --delete data_access
git push origin --delete users/sathish/scrum24
git push origin --delete feature/scheduler-fe
# Keep conv_agent, backend, feature/ci-automated-testing until PR merged
```

---

## Rules

1. **NEVER force-push to `main`.** All changes go through the integration branch → PR.
2. **If ANY merge produces more than 5 conflict files**, STOP and report. Do not auto-resolve mass conflicts.
3. **If a smoke test fails**, report the error but do NOT attempt to fix code. Flag it for manual review.
4. **Commit messages** must follow the format: `merge: <description>` for merges, `feat(<scope>): <description>` for cherry-picks.
5. **After each merge step**, run `git log --oneline -5` and `git diff HEAD~1 --stat` to verify the merge looks correct before proceeding to the next step.
6. **Do NOT modify any source code.** This prompt is strictly for git operations. If conflicts require code changes beyond choosing one side, STOP and report.

# Flux — Automated Testing Prompt Suite

**Purpose:** Feed these prompts sequentially to Claude Code CLI from the repo root (`/path/to/Flux`).  
**Execution order:** Prompt 1 → Prompt 2 → Prompt 3 (each builds on the prior).  
**Branch:** Execute all three on a new branch: `feature/ci-automated-testing`, then open a PR into `main`.

---

## Prompt 1 of 3 — Frontend CI: Vitest + Biome Lint Workflow

```
You are working in the Flux monorepo. Your task is to set up frontend testing infrastructure and a GitHub Actions CI workflow.

CURRENT STATE (do NOT guess — this is ground truth):
- Frontend lives in: ./frontend/
- Package manager: npm (package-lock.json exists)
- Linter: Biome 2.3.15 (biome.json configured, scripts: "lint", "check" in package.json)
- Framework: React 19 + TanStack Start + Vite 7
- TypeScript: 5.9.3 with path alias ~/* → ./src/*
- Vite config uses: vite-tsconfig-paths plugin
- Test framework: NONE installed yet
- .github/workflows/ directory: DOES NOT EXIST yet

TASK — Execute these steps in exact order:

### Step 1: Install Vitest + Testing Library

cd into ./frontend/ and run:

npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitest/coverage-v8

### Step 2: Create ./frontend/vitest.config.ts

Create this file at ./frontend/vitest.config.ts (separate from vite.config.ts):

```ts
/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import tsConfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsConfigPaths()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/routeTree.gen.ts", "src/test/**"],
    },
  },
});
```

### Step 3: Create test setup file

Create ./frontend/src/test/setup.ts:

```ts
import "@testing-library/jest-dom/vitest";
```

### Step 4: Create a smoke test

Create ./frontend/src/test/smoke.test.ts:

```ts
import { describe, it, expect } from "vitest";

describe("Frontend smoke test", () => {
  it("should confirm test infrastructure is working", () => {
    expect(true).toBe(true);
  });

  it("should have access to jsdom environment", () => {
    const div = document.createElement("div");
    div.textContent = "Flux";
    expect(div.textContent).toBe("Flux");
  });
});
```

### Step 5: Add test scripts to package.json

Add these scripts to ./frontend/package.json (merge into existing "scripts" block, do NOT remove existing scripts):

"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage"

### Step 6: Add TypeScript types

In ./frontend/tsconfig.json, add "vitest/globals" to compilerOptions.types array. If "types" doesn't exist, create it:

"types": ["vitest/globals"]

### Step 7: Create the GitHub Actions workflow

Create ./.github/workflows/frontend-ci.yml (note: this is at the REPO ROOT, not inside ./frontend/):

```yaml
name: Frontend CI

on:
  pull_request:
    paths:
      - "frontend/**"
      - ".github/workflows/frontend-ci.yml"

defaults:
  run:
    working-directory: frontend

jobs:
  lint-typecheck-test:
    name: Lint → Type Check → Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Biome lint
        run: npx biome check .

      - name: TypeScript type check
        run: npx tsc --noEmit

      - name: Run tests
        run: npm test

      - name: Build check
        run: npm run build
```

### Step 8: Verify locally

Run these commands from ./frontend/ and confirm they all pass:

npx biome check .
npx tsc --noEmit
npm test

IMPORTANT RULES:
- Do NOT modify vite.config.ts. Vitest config is a separate file.
- Do NOT install Jest. We are using Vitest exclusively.
- Do NOT create any component tests yet — only the smoke test.
- The workflow YAML must use "npm ci" (not "npm install") for reproducible builds.
- The workflow must scope to paths: frontend/** so it doesn't trigger on backend changes.
- If any verification step fails, fix the issue before moving on.
```

---

## Prompt 2 of 3 — Backend CI: Pytest + Ruff + Black Workflow

```
You are working in the Flux monorepo. Your task is to set up backend testing infrastructure and a GitHub Actions CI workflow.

CURRENT STATE (do NOT guess — this is ground truth):
- Backend lives in: ./backend/
- Backend structure: only ./backend/scrum_43_phone_call_trigger/ exists (routes.py, service.py, models.py)
- There is NO ./backend/app/ directory yet
- There is NO root ./backend/requirements.txt yet (only ./backend/scrum_43_phone_call_trigger/requirements.txt)
- There is NO ./backend/tests/ directory yet
- There is a Makefile referencing pytest, black, ruff but deps are not installed
- Python version: target 3.11+
- .github/workflows/ directory may already exist from Prompt 1

TASK — Execute these steps in exact order:

### Step 1: Create ./backend/requirements.txt

Create the root requirements file at ./backend/requirements.txt:

```txt
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
pydantic>=2.0.0
httpx>=0.28.0

# Database
sqlalchemy>=2.0.0
alembic>=1.15.0
asyncpg>=0.30.0

# Auth
python-jose[cryptography]>=3.4.0
passlib[bcrypt]>=1.7.0

# Feature modules
twilio>=8.10.0

# Environment
python-dotenv>=1.1.0
```

### Step 2: Create ./backend/requirements-dev.txt

Create the dev requirements file at ./backend/requirements-dev.txt:

```txt
-r requirements.txt

# Testing
pytest>=8.0.0
pytest-asyncio>=0.25.0
pytest-cov>=6.0.0

# Linting & formatting
ruff>=0.9.0
black>=25.0.0

# HTTP testing
httpx>=0.28.0
```

### Step 3: Create ./backend/pyproject.toml

Create ./backend/pyproject.toml for tool configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.ruff]
target-version = "py311"
line-length = 88
src = ["app", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.black]
target-version = ["py311"]
line-length = 88
```

### Step 4: Create the tests directory with smoke tests

Create ./backend/tests/__init__.py (empty file):

```python
```

Create ./backend/tests/conftest.py:

```python
"""Shared test fixtures for the Flux backend."""

import pytest


@pytest.fixture
def sample_user_data():
    """Sample user payload for testing."""
    return {
        "email": "testuser@flux.dev",
        "name": "Test User",
    }
```

Create ./backend/tests/test_smoke.py:

```python
"""Smoke tests — validates that the test infrastructure is functional.

These tests intentionally do not import any app modules because the
app/ directory has not been scaffolded yet. Once the FastAPI app
exists, replace these with real endpoint tests.
"""


def test_pytest_infrastructure():
    """Confirm pytest can discover and run tests."""
    assert True


def test_fixture_loading(sample_user_data):
    """Confirm fixtures from conftest.py load correctly."""
    assert sample_user_data["email"] == "testuser@flux.dev"
    assert "name" in sample_user_data


def test_python_version():
    """Confirm Python 3.11+ is available."""
    import sys

    assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version}"
```

### Step 5: Create the GitHub Actions workflow

Create ./.github/workflows/backend-ci.yml (at REPO ROOT):

```yaml
name: Backend CI

on:
  pull_request:
    paths:
      - "backend/**"
      - ".github/workflows/backend-ci.yml"

defaults:
  run:
    working-directory: backend

jobs:
  lint-test:
    name: Lint → Format Check → Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: backend/requirements-dev.txt

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Ruff lint
        run: ruff check .

      - name: Black format check
        run: black . --check

      - name: Run tests
        run: pytest tests/ -v --tb=short
```

### Step 6: Verify locally

From ./backend/, create a venv and run:

python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
ruff check .
black . --check
pytest tests/ -v

Confirm all three pass. The pytest output should show 3 tests collected, 3 passed.

IMPORTANT RULES:
- Do NOT create an ./backend/app/ directory. It doesn't exist yet and that's expected.
- Do NOT modify the existing Makefile.
- Do NOT touch anything in ./backend/scrum_43_phone_call_trigger/.
- The smoke tests must NOT import from any app module — they only validate the test framework works.
- The workflow must scope to paths: backend/** so it doesn't trigger on frontend changes.
- Add .venv/ to ./backend/.gitignore if a .gitignore exists there, or note to the user that .venv/ is already covered by the root .gitignore.
- If any verification step fails, fix the issue before moving on.
```

---

## Prompt 3 of 3 — PR Safeguard Workflow (Branch Target Check)

```
You are working in the Flux monorepo. Your task is to create a lightweight GitHub Actions workflow that runs on ALL pull requests and warns if a feature branch is targeting the main branch directly.

CURRENT STATE:
- .github/workflows/ should already contain frontend-ci.yml and backend-ci.yml from previous prompts
- Branch strategy: main (protected), frontend, backend, data_access (unprotected integration branches)
- Team members should PR into frontend/backend/data_access, NOT into main directly
- PRs into main are allowed but require owner approval (branch protection ruleset)

TASK — Execute these steps:

### Step 1: Create ./.github/workflows/pr-safeguard.yml

```yaml
name: PR Safeguard

on:
  pull_request:
    types: [opened, edited, synchronize]

jobs:
  check-target-branch:
    name: Branch target check
    runs-on: ubuntu-latest

    steps:
      - name: Warn if PR targets main from a feature branch
        if: >
          github.event.pull_request.base.ref == 'main' &&
          !contains(fromJSON('["frontend", "backend", "data_access"]'), github.event.pull_request.head.ref)
        uses: actions/github-script@v7
        with:
          script: |
            const body = `⚠️ **Branch Target Warning**

            This PR targets \`main\` from \`${{ github.event.pull_request.head.ref }}\`.

            Our workflow is:
            1. Feature branches → PR into \`frontend\`, \`backend\`, or \`data_access\`
            2. Integration branches → PR into \`main\` (requires owner approval)

            **If this is intentional** (e.g., merging an integration branch into main), you can ignore this message. Kavish will review and merge.

            **If this was a mistake**, click **Edit** at the top-right of this PR and change the base branch to the correct integration branch.`;

            // Check if we already posted this warning to avoid duplicates
            const comments = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
            });

            const botWarning = comments.data.find(
              (c) => c.user.type === "Bot" && c.body.includes("Branch Target Warning")
            );

            if (!botWarning) {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.issue.number,
                body: body,
              });
            }

      - name: Log branch info
        run: |
          echo "PR: ${{ github.event.pull_request.head.ref }} → ${{ github.event.pull_request.base.ref }}"
          echo "Status: OK"
```

### Step 2: Verify the workflow YAML is valid

Run from the repo root:

cat .github/workflows/pr-safeguard.yml

Confirm the YAML is syntactically correct and the file exists at the right path.

IMPORTANT RULES:
- This workflow must trigger on ALL pull requests regardless of file paths changed.
- It should NOT block or fail the PR. It only posts a comment as a warning.
- The duplicate-check logic prevents spamming the PR with repeated warnings on each push.
- Do NOT modify the existing frontend-ci.yml or backend-ci.yml workflows.
- The integration branches list ["frontend", "backend", "data_access"] must be exact — these are the allowed direct-to-main merge sources.
```

---

## Post-Execution Checklist

After running all three prompts, verify from the repo root:

```bash
# Confirm all workflow files exist
ls -la .github/workflows/
# Expected: frontend-ci.yml, backend-ci.yml, pr-safeguard.yml

# Confirm frontend tests pass
cd frontend && npm test && cd ..

# Confirm backend tests pass
cd backend && source .venv/bin/activate && pytest tests/ -v && cd ..

# Stage, commit, and push
git checkout -b feature/ci-automated-testing
git add -A
git commit -m "feat: add CI workflows for frontend, backend, and PR safeguard"
git push origin feature/ci-automated-testing
```

Then open a PR from `feature/ci-automated-testing` → `main`.  
The PR itself will trigger all three workflows — confirming they work.

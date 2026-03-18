# Contributing to Flux

Thanks for your interest in contributing to Flux! This guide covers the workflow, conventions, and expectations for all contributors.

---

## Git Workflow

We follow a **fork-and-branch** model:

1. **Clone** the main branch locally.
2. **Create a branch** from `main` for your work.
3. **Commit** your changes following the conventions below.
4. **Push** your branch to your fork.
5. **Open a Pull Request** against `main` on the upstream repo.
6. **Address review feedback** — then it gets merged.

```bash
# Example workflow
git checkout main
git pull origin main
git checkout -b feature/calendar-view
# ... make changes ...
git add -A
git commit -m "feat: add weekly calendar view component"
git push origin feature/calendar-view
# Open PR on GitHub
```

---

## Branch Naming

Use a descriptive prefix separated by a slash:

| Prefix | Use case | Example |
|--------|----------|---------|
| `feature/` | New functionality | `feature/goal-chat` |
| `bugfix/` | Bug fixes | `bugfix/sidebar-overflow` |
| `hotfix/` | Urgent production fixes | `hotfix/auth-token-expiry` |
| `docs/` | Documentation changes | `docs/setup-guide` |

Keep branch names lowercase with hyphens. Avoid generic names like `fix-stuff` or `update`.

---

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) to keep the history readable and automate changelogs.

### Format

```
<type>: <short description>

[optional body with more detail]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or user-facing functionality |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Tooling, dependencies, config changes |
| `refactor` | Code restructuring with no behavior change |
| `test` | Adding or updating tests |
| `style` | Formatting, whitespace (no logic changes) |

### Examples

```
feat: add goal breakdown chat interface
fix: prevent sidebar from overlapping on mobile
docs: update setup guide with Docker instructions
chore: upgrade vite to v5.1
refactor: extract event card into reusable component
test: add unit tests for rescheduleEvent API function
```

Keep the first line under 72 characters. Use the body for context when the change isn't self-explanatory.

---

## Pull Request Requirements

Every PR should include:

1. **Title** — Clear, concise summary of the change.
2. **Description** — What changed and why. Link the related issue if one exists (e.g., `Closes #42`).
3. **Screenshots** — Required for any UI changes. Before/after comparisons are ideal.
4. **Approval** — At least 1 approving review from a team member.
5. **Passing checks** — Linting and type-check must pass before merge.

### PR Description Template

```markdown
## What
Brief description of the change.

## Why
Context on why this change is needed.

## How to Test
Steps to verify the change works correctly.

## Screenshots
(if applicable)
```

---

## Code Style

### Frontend (TypeScript / React)

- **Formatter:** Prettier (config in `.prettierrc`)
- **Linter:** ESLint (config in `.eslintrc.json`)
- **Components:** Function components with hooks only — no class components
- **Typing:** All props and return types must be explicitly typed; no `any`
- **CSS:** CSS Modules (`*.module.css`) — no global styles outside of `styles/global.css`
- **Imports:** Group by external → internal → styles, separated by blank lines

Run before committing:

```bash
cd frontend
npm run lint
npm run format
npm run type-check
```

### Backend (Python / FastAPI)

- **Formatter:** [Black](https://black.readthedocs.io/) (line length 88)
- **Linter:** [Ruff](https://docs.astral.sh/ruff/)
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all public functions and classes

Run before committing:

```bash
cd backend
source venv/bin/activate    # or .\venv\Scripts\Activate.ps1 on Windows
make lint    # Check formatting and linting (targets app/ and conv_agent/)
make format  # Auto-fix formatting
```

---

## Testing

### Frontend

- Write unit tests for utility functions and hooks.
- Write integration tests for API layer functions.
- Place test files next to the code they test with a `.test.ts` or `.test.tsx` suffix.

### Backend

- Write tests for all API endpoints and service functions.
- Core app tests go in `backend/tests/`.
- Conv-agent tests go in `backend/conv_agent/tests/`.
- Run the full suite with `pytest tests/ -v` (from `backend/` with venv active).
- Supabase must be running locally for integration tests (`supabase start`).

---

## Documentation

When you add or change a feature:

- Update the **README.md** if the change affects project setup, features, or architecture.
- Add **JSDoc comments** (frontend) or **docstrings** (backend) to new public functions.
- Update **docs/SETUP.md** if there are new environment variables, dependencies, or setup steps.

---

## Questions?

If you're unsure about anything, open a GitHub issue with the `question` label or ask in the team channel. We'd rather help you get started than have you stuck.

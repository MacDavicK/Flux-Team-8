# Goal Clarifier Multi-Select Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow clarifier questions to accept multiple selected options, serialized as a comma-separated string with optional custom text appended after a semicolon.

**Architecture:** Add a `multi_select: bool` flag to the backend schema and LLM prompt. The frontend type mirrors this flag. `GoalClarifierView` tracks pending selections per question and only calls `recordAnswer` on explicit confirm, joining selected options with `", "` and appending custom text with `"; "` if present.

**Tech Stack:** Python / Pydantic (backend schema), plain text prompt (LLM instructions), TypeScript / React / framer-motion (frontend component).

---

## File Map

| File | Change |
|------|--------|
| `backend/app/models/api_schemas.py` | Add `multi_select: bool = False` to `ClarifierQuestionSchema` |
| `backend/app/agents/prompts/goal_clarifier.txt` | Document `multi_select` field with rules and an example |
| `backend/tests/unit/test_clarifier_schema.py` | New — unit tests for `ClarifierQuestionSchema.multi_select` |
| `frontend/src/types/message.ts` | Add `multi_select: boolean` to `GoalClarifierQuestion` |
| `frontend/src/components/chat/GoalClarifierView.tsx` | Multi-select UI: toggle, pending state, confirm button, back-fill |

---

## Task 1: Backend schema — add `multi_select` field

**Files:**
- Modify: `backend/app/models/api_schemas.py:48-54`
- Test: `backend/tests/unit/test_clarifier_schema.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_clarifier_schema.py`:

```python
"""Unit tests for ClarifierQuestionSchema.multi_select field."""
from app.models.api_schemas import ClarifierQuestionSchema


def test_multi_select_defaults_to_false():
    q = ClarifierQuestionSchema(id="q1", question="Which days?", options=["Mon", "Tue"])
    assert q.multi_select is False


def test_multi_select_can_be_set_to_true():
    q = ClarifierQuestionSchema(
        id="q1", question="Which days?", options=["Mon", "Tue"], multi_select=True
    )
    assert q.multi_select is True


def test_multi_select_false_question_unchanged():
    """Existing questions without multi_select still parse correctly."""
    data = {"id": "q1", "question": "Fitness level?", "options": ["Beginner"]}
    q = ClarifierQuestionSchema(**data)
    assert q.multi_select is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/unit/test_clarifier_schema.py -v
```

Expected: `AttributeError` or `ValidationError` — `multi_select` does not exist yet.

- [ ] **Step 3: Add `multi_select` to `ClarifierQuestionSchema`**

In `backend/app/models/api_schemas.py`, the schema currently reads:

```python
class ClarifierQuestionSchema(BaseModel):
    id: str
    question: str
    options: list[str] = []
    allows_custom: bool = True
    zod_validator: Optional[str] = None
    required: bool = True
```

Add the new field after `allows_custom`:

```python
class ClarifierQuestionSchema(BaseModel):
    id: str
    question: str
    options: list[str] = []
    allows_custom: bool = True
    multi_select: bool = False
    zod_validator: Optional[str] = None
    required: bool = True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/unit/test_clarifier_schema.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/api_schemas.py backend/tests/unit/test_clarifier_schema.py
git commit -m "feat: add multi_select field to ClarifierQuestionSchema"
```

---

## Task 2: Update LLM prompt to document `multi_select`

**Files:**
- Modify: `backend/app/agents/prompts/goal_clarifier.txt`

No automated test — this is prompt content. Verify by inspection.

- [ ] **Step 1: Add `multi_select` docs to the Question Design Rules section**

In `backend/app/agents/prompts/goal_clarifier.txt`, the current rules block ends at line 25:

```
- Set `allows_custom: false` only if the options are exhaustive (e.g. Yes / No)
```

Add two lines immediately after:

```
- Set `multi_select: true` when the user could reasonably pick more than one option (e.g. "Which days can you train?", "What equipment do you have access to?")
- Set `multi_select: false` (default) for all other questions, including those with a single definitive answer
```

- [ ] **Step 2: Add `multi_select` to the Output Format schema comment and example**

The schema comment block currently shows fields without `multi_select`. Update the first example question to include the field:

```json
{
  "id": "current_fitness_level",
  "question": "What's your current fitness level?",
  "options": ["Complete beginner", "I exercise occasionally", "I exercise regularly", "I'm quite fit"],
  "allows_custom": false,
  "multi_select": false,
  "zod_validator": null,
  "required": true
}
```

Add a new example question after the existing ones that demonstrates `multi_select: true`:

```json
{
  "id": "available_days",
  "question": "Which days of the week can you train?",
  "options": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
  "allows_custom": false,
  "multi_select": true,
  "zod_validator": null,
  "required": true
}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/prompts/goal_clarifier.txt
git commit -m "feat: document multi_select in goal_clarifier LLM prompt"
```

---

## Task 3: Frontend type — add `multi_select` to `GoalClarifierQuestion`

**Files:**
- Modify: `frontend/src/types/message.ts:170-177`

No frontend test framework exists in this project — verify by TypeScript compilation.

- [ ] **Step 1: Add `multi_select` to the interface**

In `frontend/src/types/message.ts`, the current interface reads:

```typescript
export interface GoalClarifierQuestion {
  id: string;
  question: string;
  options: string[]; // pre-defined choices (empty = open-ended)
  allows_custom: boolean; // true if user can type a custom answer
  zod_validator: string | null; // Zod schema string for validating custom input
  required: boolean;
}
```

Add the field after `allows_custom`:

```typescript
export interface GoalClarifierQuestion {
  id: string;
  question: string;
  options: string[]; // pre-defined choices (empty = open-ended)
  allows_custom: boolean; // true if user can type a custom answer
  multi_select: boolean; // true if user may pick more than one option
  zod_validator: string | null; // Zod schema string for validating custom input
  required: boolean;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors related to `GoalClarifierQuestion`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/message.ts
git commit -m "feat: add multi_select to GoalClarifierQuestion type"
```

---

## Task 4: Frontend component — multi-select UI in `GoalClarifierView`

**Files:**
- Modify: `frontend/src/components/chat/GoalClarifierView.tsx`

No frontend test framework — verify manually or via TypeScript compilation.

The component currently:
- Calls `recordAnswer(opt)` immediately on option click → auto-advances
- Has no concept of pending selections

### What changes

1. Add `pendingSelections: string[]` state (reset when `currentIndex` changes).
2. When `current.multi_select` is true: option click toggles `pendingSelections`; no auto-advance.
3. When `current.multi_select` is false: option click calls `recordAnswer(opt)` immediately (existing behavior unchanged).
4. The confirm button ("Next" / "Done") for multi-select: joins `pendingSelections` with `", "`, appends `customValue.trim()` with `"; "` if non-empty, calls `recordAnswer`.
5. On back-navigation: pre-fill `pendingSelections` by parsing the stored answer (split on `"; "`, take first part, split on `", "`).
6. `isSelected` for multi-select checks `pendingSelections.includes(opt)`; for single-select remains the existing check.

- [ ] **Step 1: Add `pendingSelections` state and reset effect**

Inside the component (after the existing `useState` declarations), add:

```tsx
const [pendingSelections, setPendingSelections] = useState<string[]>([]);
```

Then update `handleBack` to also restore `pendingSelections` for the previous question:

```tsx
function handleBack() {
  if (!canGoBack) return;
  setDirection(-1);
  const prevIndex = currentIndex - 1;
  setCurrentIndex(prevIndex);
  const prevQ = questions[prevIndex];
  const prevAnswer = answers.find((a) => a.question_id === prevQ.id);
  setCustomError(null);
  if (prevQ.multi_select && prevAnswer) {
    const [optionsPart, customPart] = prevAnswer.answer.split("; ");
    setPendingSelections(optionsPart ? optionsPart.split(", ").filter(Boolean) : []);
    setCustomValue(customPart ?? ""); // restore only the custom-text portion, not the full answer
  } else {
    setPendingSelections([]);
    setCustomValue(prevAnswer?.answer ?? "");
  }
}
```

And update the forward-navigation inside `recordAnswer` (the `!isLast` branch) to also reset `pendingSelections` (and pre-fill from existing answer for next question if multi-select):

```tsx
if (!isLast) {
  setAnswers(updatedAnswers);
  setDirection(1);
  setCurrentIndex(currentIndex + 1);
  const nextQ = questions[currentIndex + 1];
  const nextAnswer = updatedAnswers.find((a) => a.question_id === nextQ.id);
  setCustomError(null);
  if (nextQ.multi_select && nextAnswer) {
    const [optionsPart, customPart] = nextAnswer.answer.split("; ");
    setPendingSelections(optionsPart ? optionsPart.split(", ").filter(Boolean) : []);
    setCustomValue(customPart ?? ""); // restore only the custom-text portion
  } else {
    setPendingSelections([]);
    setCustomValue(nextAnswer?.answer ?? "");
  }
}
```

- [ ] **Step 2: Update option button click handler and `isSelected`**

Replace the options rendering block (the `{current.options.map(…)}` section):

```tsx
{current.options.map((opt) => {
  const isSelected = current.multi_select
    ? pendingSelections.includes(opt)
    : answers.find((a) => a.question_id === current.id)?.answer === opt;
  return (
    <motion.button
      key={opt}
      type="button"
      onClick={() => {
        if (disabled) return;
        if (current.multi_select) {
          setPendingSelections((prev) =>
            prev.includes(opt) ? prev.filter((s) => s !== opt) : [...prev, opt]
          );
        } else {
          recordAnswer(opt);
        }
      }}
      disabled={disabled}
      whileTap={{ scale: 0.96 }}
      className={cn(
        "px-4 py-2 rounded-full text-sm font-medium border transition-colors",
        isSelected
          ? "bg-sage text-white border-sage"
          : "bg-white border-charcoal/20 text-charcoal hover:bg-sage/10 hover:border-sage active:bg-sage/20",
        "disabled:opacity-40 disabled:cursor-not-allowed",
      )}
    >
      {opt}
    </motion.button>
  );
})}
```

- [ ] **Step 3: Add multi-select confirm button and hide the custom input's inline button for multi-select**

For multi-select questions, one confirm button handles everything (options + optional custom text). The existing inline "Next/Done" button inside the custom input row must be hidden to avoid two competing submit paths.

After the options `</div>` closing tag and before the custom input block, add the standalone confirm button. It calls `handleCustomSubmit` (updated in Step 4) which handles joining selections and appending custom text:

```tsx
{current.multi_select && current.options.length > 0 && (
  <button
    type="button"
    onClick={handleCustomSubmit}
    disabled={disabled || (pendingSelections.length === 0 && !customValue.trim())}
    className={cn(
      "w-full px-4 py-2.5 rounded-xl text-sm font-medium transition-colors",
      "bg-sage text-white",
      "hover:bg-sage/90 disabled:opacity-40 disabled:cursor-not-allowed",
    )}
  >
    {isLast ? "Done" : "Next"}
  </button>
)}
```

Then, inside the custom input row (the `<div className="flex gap-2 items-center">` block), hide the existing inline "Next/Done" button when `current.multi_select` is true — the standalone button above already covers confirmation. Add `!current.multi_select &&` guard:

```tsx
{!current.multi_select && (
  <button
    type="button"
    onClick={handleCustomSubmit}
    disabled={disabled || !customValue.trim()}
    className={cn(
      "px-4 py-2.5 rounded-xl text-sm font-medium transition-colors",
      "bg-sage text-white",
      "hover:bg-sage/90 disabled:opacity-40 disabled:cursor-not-allowed",
    )}
  >
    {isLast ? "Done" : "Next"}
  </button>
)}
```

- [ ] **Step 4: Update `handleCustomSubmit` to handle multi-select answer serialization**

```tsx
function handleCustomSubmit() {
  const trimmed = customValue.trim();
  if (current.multi_select) {
    // For multi-select: need at least one option selected OR custom text
    if (pendingSelections.length === 0 && !trimmed) {
      setCustomError("Please select an option or enter a value");
      return;
    }
    const answer = trimmed
      ? pendingSelections.length > 0
        ? `${pendingSelections.join(", ")}; ${trimmed}`
        : trimmed
      : pendingSelections.join(", ");
    recordAnswer(answer);
  } else {
    if (!trimmed) {
      setCustomError("Please enter a value");
      return;
    }
    recordAnswer(trimmed);
  }
}
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chat/GoalClarifierView.tsx
git commit -m "feat: multi-select support in GoalClarifierView"
```

---

## Manual Smoke Test

After all tasks are complete, start the dev servers and trigger the goal clarifier flow with a goal like "I want to build strength". Verify:

1. Single-select questions: clicking an option still auto-advances (unchanged).
2. Multi-select questions: clicking options toggles highlight; no auto-advance; "Next/Done" button appears and is disabled until at least one option is selected.
3. Typing custom text on a multi-select question and hitting "Next/Done" produces `"OptionA, OptionB; custom text"` (or just `"custom text"` if no options selected).
4. Navigating back to a multi-select question restores previously selected options.

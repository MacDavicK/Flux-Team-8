# Goal Clarifier Multi-Select Design

**Date:** 2026-03-22

## Problem

`GoalClarifierView` only supports single-select answers. Clicking an option immediately records it and advances to the next question. There is no way for users to select multiple options.

## Design

Add a `multi_select: bool` flag to clarifier questions. When true, the UI toggles selections instead of auto-advancing, and requires an explicit "Next / Done" confirm button.

### Answer serialization

Multi-select answers are joined as a comma-separated string to keep `GoalClarifierAnswer.answer: string` unchanged:

- Options only: `"Morning, Evening"`
- Options + custom text: `"Morning, Evening; Also early afternoons"`

The semicolon delimiter distinguishes custom text from selected options (commas are already used as the option separator).

## Changes

### Backend

1. **`backend/app/models/api_schemas.py`** — add `multi_select: bool = False` to `ClarifierQuestionSchema`
2. **`backend/app/agents/prompts/goal_clarifier.txt`** — add `multi_select` field docs and an example question where multiple answers are valid (e.g. "Which days can you train?")

### Frontend

3. **`frontend/src/types/message.ts`** — add `multi_select: boolean` to `GoalClarifierQuestion`
4. **`frontend/src/components/chat/GoalClarifierView.tsx`**:
   - Track `pendingSelections: string[]` in local state (reset when question changes)
   - On option click: toggle in/out of `pendingSelections` instead of calling `recordAnswer`
   - Show "Next" / "Done" confirm button for multi-select questions (same button already exists for custom input)
   - On confirm: join `pendingSelections` with `", "`, append `customValue` with `"; "` if non-empty, call `recordAnswer`
   - On back navigation: pre-fill `pendingSelections` from the stored answer (split on `", "` up to the first `"; "`)
   - Single-select behavior unchanged

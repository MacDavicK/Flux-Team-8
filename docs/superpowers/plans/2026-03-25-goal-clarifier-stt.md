# Goal Clarifier STT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add push-to-talk STT to the `GoalClarifierView` bottom sheet so users can speak their free-text answers, which auto-submit on transcript arrival.

**Architecture:** `GoalClarifierView` owns its own `useVoice()` instance. A `pendingSelectionsRef` mirrors `pendingSelections` state to give the `useEffect` stale-closure-safe access. A single `useEffect` on `voice.transcript` auto-submits via `recordAnswer` — directly for single-select, or with combined-answer construction for multi-select. The component's early-return guard (`if questions.length === 0`) must move to after all hooks to satisfy React's Rules of Hooks.

**Tech Stack:** React 18, `useVoice` hook (Deepgram WebSocket STT), `MicButton` component, Vitest + @testing-library/react

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/vitest.config.ts` | **Create** | Vitest config with jsdom environment |
| `frontend/src/test/setup.ts` | **Create** | jest-dom matchers setup |
| `frontend/src/components/chat/__tests__/GoalClarifierView.voice.test.tsx` | **Create** | Tests for voice behavior |
| `frontend/src/components/chat/GoalClarifierView.tsx` | **Modify** | Add voice hook, ref, effect, MicButton; move early return |

---

## Task 1: Set up Vitest

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`

- [ ] **Step 1: Create vitest config**

Create `frontend/vitest.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
});
```

- [ ] **Step 2: Create test setup file**

Create `frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 3: Verify vitest runs with zero tests**

```bash
cd frontend && npm test
```

Expected output: `No test files found` or `0 tests`. Must not error on config.

- [ ] **Step 4: Commit**

```bash
git add frontend/vitest.config.ts frontend/src/test/setup.ts
git commit -m "test: add vitest config with jsdom"
```

---

## Task 2: Write Failing Tests

**Files:**
- Create: `frontend/src/components/chat/__tests__/GoalClarifierView.voice.test.tsx`

`GoalClarifierQuestion` (from `~/types/message`) has these fields: `id`, `question`, `options`, `allows_custom`, `multi_select`, `zod_validator: string | null`, `required: boolean`.

- [ ] **Step 1: Create the test file**

Create `frontend/src/components/chat/__tests__/GoalClarifierView.voice.test.tsx`:

```tsx
import { render, screen, act, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type React from "react";
import { GoalClarifierView } from "../GoalClarifierView";
import type { UseVoiceReturn } from "~/hooks/useVoice";
import type {
  GoalClarifierAnswer,
  GoalClarifierQuestion,
} from "~/types/message";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("framer-motion", () => ({
  motion: {
    div: ({
      children,
      className,
      initial: _i,
      animate: _a,
      exit: _e,
      transition: _t,
      custom: _c,
      ...rest
    }: React.HTMLAttributes<HTMLDivElement> & Record<string, unknown>) => (
      <div className={className} {...rest}>
        {children}
      </div>
    ),
    button: ({
      children,
      className,
      onClick,
      disabled,
      type,
      whileTap: _w,
      initial: _i,
      animate: _a,
      exit: _e,
      ...rest
    }: React.ButtonHTMLAttributes<HTMLButtonElement> & Record<string, unknown>) => (
      <button className={className} onClick={onClick} disabled={disabled} type={type} {...rest}>
        {children}
      </button>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("~/components/chat/MicButton", () => ({
  MicButton: ({
    onClick,
    isRecording,
    isProcessing,
    disabled,
  }: {
    onClick: () => void;
    isRecording: boolean;
    isProcessing: boolean;
    disabled?: boolean;
  }) => (
    <button
      data-testid="mic-button"
      onClick={onClick}
      disabled={disabled || isProcessing}
      data-recording={String(isRecording)}
    >
      Mic
    </button>
  ),
}));

const mockUseVoice = vi.fn();
vi.mock("~/hooks/useVoice", () => ({
  useVoice: () => mockUseVoice(),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeVoice(overrides: Partial<UseVoiceReturn> = {}): UseVoiceReturn {
  return {
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    playTTS: vi.fn(),
    transcript: null,
    isConnecting: false,
    isRecording: false,
    isProcessing: false,
    error: null,
    reset: vi.fn(),
    stream: null,
    ...overrides,
  };
}

function makeQuestion(overrides: Partial<GoalClarifierQuestion> = {}): GoalClarifierQuestion {
  return {
    id: "q1",
    question: "What is your goal?",
    options: [],
    allows_custom: false,
    multi_select: false,
    zod_validator: null,
    required: true,
    ...overrides,
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("GoalClarifierView — voice STT", () => {
  beforeEach(() => {
    mockUseVoice.mockReturnValue(makeVoice());
  });

  it("shows mic button on free-text-only question (no options)", () => {
    render(
      <GoalClarifierView
        questions={[makeQuestion({ options: [], allows_custom: false })]}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByTestId("mic-button")).toBeInTheDocument();
  });

  it("shows mic button on allows_custom question (has options + allows custom)", () => {
    render(
      <GoalClarifierView
        questions={[makeQuestion({ options: ["Option A"], allows_custom: true })]}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByTestId("mic-button")).toBeInTheDocument();
  });

  it("hides mic button on options-only question (!allows_custom, has options)", () => {
    render(
      <GoalClarifierView
        questions={[makeQuestion({ options: ["Option A", "Option B"], allows_custom: false })]}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("mic-button")).not.toBeInTheDocument();
  });

  it("auto-submits when transcript arrives on single free-text question", () => {
    const onSubmit = vi.fn();
    const reset = vi.fn();
    mockUseVoice.mockReturnValue(makeVoice({ transcript: null, reset }));

    const question = makeQuestion();
    const { rerender } = render(
      <GoalClarifierView questions={[question]} onSubmit={onSubmit} />,
    );

    expect(onSubmit).not.toHaveBeenCalled();

    mockUseVoice.mockReturnValue(makeVoice({ transcript: "Run a marathon", reset }));
    act(() => {
      rerender(<GoalClarifierView questions={[question]} onSubmit={onSubmit} />);
    });

    expect(onSubmit).toHaveBeenCalledWith([
      { question_id: "q1", question: "What is your goal?", answer: "Run a marathon" },
    ]);
    expect(reset).toHaveBeenCalled();
  });

  it("does not submit on whitespace-only transcript", () => {
    const onSubmit = vi.fn();
    const reset = vi.fn();
    mockUseVoice.mockReturnValue(makeVoice({ transcript: null, reset }));

    const question = makeQuestion();
    const { rerender } = render(
      <GoalClarifierView questions={[question]} onSubmit={onSubmit} />,
    );

    // Use the same reset ref so the assertion is unambiguous
    mockUseVoice.mockReturnValue(makeVoice({ transcript: "   ", reset }));
    act(() => {
      rerender(<GoalClarifierView questions={[question]} onSubmit={onSubmit} />);
    });

    expect(onSubmit).not.toHaveBeenCalled();
    expect(reset).not.toHaveBeenCalled();
  });

  it("combines tapped options with spoken transcript on multi-select", () => {
    const onSubmit = vi.fn();
    const reset = vi.fn();
    mockUseVoice.mockReturnValue(makeVoice({ transcript: null, reset }));

    const question = makeQuestion({
      id: "q1",
      options: ["Running", "Cycling"],
      allows_custom: true,
      multi_select: true,
    });

    const { rerender } = render(
      <GoalClarifierView questions={[question]} onSubmit={onSubmit} />,
    );

    // Tap "Running" to add it to pendingSelections
    fireEvent.click(screen.getByText("Running"));

    // Transcript arrives
    mockUseVoice.mockReturnValue(makeVoice({ transcript: "and swimming", reset }));
    act(() => {
      rerender(<GoalClarifierView questions={[question]} onSubmit={onSubmit} />);
    });

    expect(onSubmit).toHaveBeenCalledWith([
      {
        question_id: "q1",
        question: question.question,
        answer: "Running; and swimming",
      },
    ]);
    expect(reset).toHaveBeenCalled();
  });

  it("submits transcript alone on multi-select with no tapped options", () => {
    const onSubmit = vi.fn();
    const reset = vi.fn();
    mockUseVoice.mockReturnValue(makeVoice({ transcript: null, reset }));

    const question = makeQuestion({
      options: ["Running", "Cycling"],
      allows_custom: true,
      multi_select: true,
    });

    const { rerender } = render(
      <GoalClarifierView questions={[question]} onSubmit={onSubmit} />,
    );

    mockUseVoice.mockReturnValue(makeVoice({ transcript: "Swimming", reset }));
    act(() => {
      rerender(<GoalClarifierView questions={[question]} onSubmit={onSubmit} />);
    });

    expect(onSubmit).toHaveBeenCalledWith([
      expect.objectContaining({ answer: "Swimming" }),
    ]);
  });

  it("disables mic button when disabled prop is true", () => {
    render(
      <GoalClarifierView
        questions={[makeQuestion()]}
        onSubmit={vi.fn()}
        disabled
      />,
    );
    expect(screen.getByTestId("mic-button")).toBeDisabled();
  });

  it("disables mic button when voice is connecting", () => {
    mockUseVoice.mockReturnValue(makeVoice({ isConnecting: true }));
    render(
      <GoalClarifierView questions={[makeQuestion()]} onSubmit={vi.fn()} />,
    );
    expect(screen.getByTestId("mic-button")).toBeDisabled();
  });

  it("calls startRecording when mic button clicked while idle", () => {
    const startRecording = vi.fn();
    mockUseVoice.mockReturnValue(makeVoice({ startRecording, isRecording: false }));

    render(
      <GoalClarifierView questions={[makeQuestion()]} onSubmit={vi.fn()} />,
    );

    fireEvent.click(screen.getByTestId("mic-button"));
    expect(startRecording).toHaveBeenCalled();
  });

  it("calls stopRecording when mic button clicked while recording", () => {
    const stopRecording = vi.fn();
    mockUseVoice.mockReturnValue(makeVoice({ stopRecording, isRecording: true }));

    render(
      <GoalClarifierView questions={[makeQuestion()]} onSubmit={vi.fn()} />,
    );

    fireEvent.click(screen.getByTestId("mic-button"));
    expect(stopRecording).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests — verify they all FAIL**

```bash
cd frontend && npm test -- GoalClarifierView.voice
```

Expected: tests fail because `GoalClarifierView` does not yet import `useVoice` or render `MicButton`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add frontend/src/components/chat/__tests__/GoalClarifierView.voice.test.tsx
git commit -m "test: add failing voice STT tests for GoalClarifierView"
```

---

## Task 3: Implement GoalClarifierView Changes

**Files:**
- Modify: `frontend/src/components/chat/GoalClarifierView.tsx`

Read the full file before editing (`frontend/src/components/chat/GoalClarifierView.tsx`, 334 lines). Key landmarks:
- Line 3: `import { useState } from "react";`
- Line 25–30: five `useState` calls
- Line 32: `if (questions.length === 0) return null;` ← **must move; see Step 3**
- Line 34: `const current = questions[currentIndex];`
- Line 38–91: `function recordAnswer(...)`
- Line 93–127: `function handleBack()`
- Line 235: option button `setPendingSelections` inside `onClick`
- Line 283: `<div className="flex gap-2 items-center">` — the custom input row

- [ ] **Step 1: Add imports**

Replace the import block at the top:

```tsx
// Before:
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft } from "lucide-react";
import { useState } from "react";
import type {
  GoalClarifierAnswer,
  GoalClarifierQuestion,
} from "~/types/message";
import { cn } from "~/utils/cn";

// After:
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type {
  GoalClarifierAnswer,
  GoalClarifierQuestion,
} from "~/types/message";
import { MicButton } from "~/components/chat/MicButton";
import { useVoice } from "~/hooks/useVoice";
import { cn } from "~/utils/cn";
```

- [ ] **Step 2: Add pendingSelectionsRef and voice after the useState calls**

After the last `useState` call on line 30 (`const [pendingSelections, ...]`), add:

```tsx
const pendingSelectionsRef = useRef<string[]>([]);
const voice = useVoice();
```

- [ ] **Step 3: Move the early return guard and add the useEffect**

**Why:** The `useEffect` must be placed before any `return` statement (Rules of Hooks). The current early return at line 32 is before `current` and `recordAnswer` are defined. Moving the early return to a guard _inside_ the `useEffect` — and keeping the early JSX return at the bottom of the hook block — is the correct fix.

Replace line 32 (`if (questions.length === 0) return null;`) with nothing — delete it.

Then, after the `voice` declaration (and before `const current = questions[currentIndex];`), insert the `useEffect`:

```tsx
useEffect(() => {
  if (questions.length === 0) return;
  const trimmed = voice.transcript?.trim();
  if (!trimmed) return;

  const current = questions[currentIndex];
  if (!current) return;

  if (current.multi_select) {
    // Build the combined answer directly — do NOT call setCustomValue then
    // handleCustomSubmit, as React state setters are async and handleCustomSubmit
    // would read stale customValue. pendingSelectionsRef holds the live value.
    const sels = pendingSelectionsRef.current;
    const combined = sels.length > 0 ? `${sels.join(", ")}; ${trimmed}` : trimmed;
    recordAnswer(combined);
  } else {
    recordAnswer(trimmed);
  }

  // Reset AFTER recordAnswer — reset() sets transcript to null immediately,
  // which would prevent this effect from running if called first.
  voice.reset();
  // voice.transcript is the only trigger dep. recordAnswer, currentIndex,
  // and questions are captured at the render where transcript changed — that
  // render has the correct up-to-date values for all of them.
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [voice.transcript]);
```

> **Note on the early return:** After deleting line 32, move `if (questions.length === 0) return null;` to just before the `return (` JSX block at the bottom of the component function (around line 155 in the original). This preserves the rendering guard while satisfying the Rules of Hooks.

- [ ] **Step 4: Update all setPendingSelections call sites to also update the ref**

There are **9** `setPendingSelections` call sites — **4 in `recordAnswer`**, **4 in `handleBack`**, and **1 in the option button `onClick`**. Every one must be accompanied by `pendingSelectionsRef.current = <new value>`.

**In `recordAnswer`** (the forward-navigation function):

```tsx
// Site 1 — inside "if (semicolonIdx !== -1)" branch:
// Before:
setPendingSelections(
  optionsPart ? optionsPart.split(", ").filter(Boolean) : [],
);
// After:
const nextPendingFromSemi = optionsPart ? optionsPart.split(", ").filter(Boolean) : [];
pendingSelectionsRef.current = nextPendingFromSemi;
setPendingSelections(nextPendingFromSemi);

// Site 2 — inside "else" branch, allAreOptions = true:
// Before:
setPendingSelections(parts);
// After:
pendingSelectionsRef.current = parts;
setPendingSelections(parts);

// Site 3 — inside "else" branch, allAreOptions = false:
// Before:
setPendingSelections([]);
// After:
pendingSelectionsRef.current = [];
setPendingSelections([]);

// Site 4 — the outer else (no existing answer for next question):
// Before:
setPendingSelections([]);
// After:
pendingSelectionsRef.current = [];
setPendingSelections([]);
```

**In `handleBack`** (the backward-navigation function — same 4-site pattern, 3 actually used):

```tsx
// Site 1 — inside "if (semicolonIdx !== -1)" branch:
// Before:
setPendingSelections(
  optionsPart ? optionsPart.split(", ").filter(Boolean) : [],
);
// After:
const nextPendingFromSemiBack = optionsPart ? optionsPart.split(", ").filter(Boolean) : [];
pendingSelectionsRef.current = nextPendingFromSemiBack;
setPendingSelections(nextPendingFromSemiBack);

// Site 2 — inside "else" branch, allAreOptions = true:
// Before:
setPendingSelections(parts);
// After:
pendingSelectionsRef.current = parts;
setPendingSelections(parts);

// Site 3 — inside "else" branch, allAreOptions = false:
// Before:
setPendingSelections([]);
// After:
pendingSelectionsRef.current = [];
setPendingSelections([]);

// Site 4 — the outer else (no prev answer):
// Before:
setPendingSelections([]);
// After:
pendingSelectionsRef.current = [];
setPendingSelections([]);
```

**In the option button `onClick`:**

```tsx
// Before:
if (current.multi_select) {
  setPendingSelections((prev) =>
    prev.includes(opt)
      ? prev.filter((s) => s !== opt)
      : [...prev, opt],
  );
}
// After:
if (current.multi_select) {
  setPendingSelections((prev) => {
    const next = prev.includes(opt)
      ? prev.filter((s) => s !== opt)
      : [...prev, opt];
    pendingSelectionsRef.current = next;
    return next;
  });
}
```

- [ ] **Step 5: Add MicButton to the custom input row**

Inside `{/* Custom input */}`, in the `<div className="flex gap-2 items-center">`, add `MicButton` as the last child (after the conditional submit button):

```tsx
<div className="flex gap-2 items-center">
  <input ... />         {/* unchanged */}
  {!current.multi_select && (
    <button ...>        {/* unchanged */}
      {isLast ? "Done" : "Next"}
    </button>
  )}
  <MicButton
    onClick={() =>
      voice.isRecording ? voice.stopRecording() : voice.startRecording()
    }
    isRecording={voice.isRecording}
    isProcessing={voice.isProcessing}
    disabled={disabled || voice.isConnecting}
  />
</div>
```

> For multi-select questions, `{!current.multi_select && ...}` renders nothing, so `MicButton` sits next to the `<input>` alone. This is correct — the multi-select Done/Next button is rendered above this row.

- [ ] **Step 6: Verify no TypeScript errors**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

---

## Task 4: Verify and Commit

- [ ] **Step 1: Run all tests**

```bash
cd frontend && npm test -- GoalClarifierView.voice
```

Expected: all 10 tests pass.

- [ ] **Step 2: If any test fails, diagnose before fixing**

Common failure modes:
- Framer-motion mock missing a prop (`whileTap`, `custom`, etc.) → add to the destructure in the mock
- `pendingSelectionsRef` not updated in `handleBack` site → count all 4 `setPendingSelections` calls in `handleBack` and confirm each has a matching ref update
- Wrong combined string for multi-select → verify the `sels.length > 0` branch matches `handleCustomSubmit` lines 137–141 in the original file
- `recordAnswer` reads stale `currentIndex` in the `useEffect` → confirm the effect's `useEffect` captures `currentIndex` and `questions` from the render where `voice.transcript` changed (it does, by React's closure semantics)

Do NOT change test expectations to match wrong behavior — fix the implementation.

- [ ] **Step 3: Manual smoke test**

Start the dev server and trigger a goal clarification flow:

```bash
cd frontend && npm run dev
```

Verify:
1. Mic button appears next to the text input on free-text questions
2. Mic button absent on option-only questions (no custom allowed)
3. Speaking an answer auto-advances the sheet to the next question
4. On a multi-select question: tap one option, then speak a custom addition — verify the combined answer is submitted

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/GoalClarifierView.tsx
git commit -m "feat: add push-to-talk STT to GoalClarifierView free-text answers"
```

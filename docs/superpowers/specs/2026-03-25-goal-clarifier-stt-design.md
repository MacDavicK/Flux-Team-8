# Goal Clarifier STT Design

**Date:** 2026-03-25

## Summary

Add push-to-talk speech-to-text (STT) to the `GoalClarifierView` bottom sheet. The mic button appears only on free-text input questions and auto-submits the transcript when recording stops.

## Scope

- **In scope:** STT for free-text answers in `GoalClarifierView`
- **Out of scope:** TTS for reading questions aloud; voice on option-button or date-picker questions

## Architecture

`GoalClarifierView` owns its own `useVoice()` instance. This avoids prop drilling and any conflict with the main chat voice instance. The two hooks never run simultaneously (clarifier sheet is modal). Cleanup on unmount is handled automatically by `useVoice`'s existing `useEffect`.

## Component Changes

**`GoalClarifierView.tsx`** — only file modified (~20-25 lines added):

1. Call `useVoice()` at the top of the component.
2. Add a `useEffect` watching `voice.transcript`:
   - Guard: only fire when `voice.transcript` is non-null **and** `voice.transcript.trim()` is non-empty (mirrors `handleCustomSubmit`'s own guard).
   - **Non-multi-select free-text questions**: call `recordAnswer(voice.transcript.trim())` directly, then `voice.reset()`. Call `recordAnswer` before `voice.reset()` — `reset()` sets `transcript` to null which would prevent any re-triggering.
   - **Multi-select questions**: do NOT call `setCustomValue` then `handleCustomSubmit()` — React state updates are async so `handleCustomSubmit` would read stale `customValue`. Instead, construct the combined answer directly in the `useEffect`: build the string from the current `pendingSelections` and the transcript string (same logic as `handleCustomSubmit` lines 137-141), then call `recordAnswer(combined)`, then `voice.reset()`.
   - **Stale closure**: `pendingSelections` is React state; a `useEffect` triggered by `voice.transcript` alone will read a stale copy. Mirror `pendingSelections` into a `pendingSelectionsRef` (a `useRef<string[]>` updated alongside every `setPendingSelections` call) and read `pendingSelectionsRef.current` inside the effect. This avoids adding `pendingSelections` to the dependency array as a trigger.
3. Render `MicButton` inside the `flex gap-2` custom input row (the `div` at the start of the custom input block), only when the text input is visible (`allows_custom || options.length === 0`).
   - For non-multi-select questions this places `MicButton` next to the submit button in the row.
   - For multi-select questions no submit button is rendered in that row (it is above), so `MicButton` sits next to the text input alone.
   - `onClick`: a toggle handler — `voice.isRecording ? voice.stopRecording() : voice.startRecording()`
   - `isRecording`: `voice.isRecording`
   - `isProcessing`: `voice.isProcessing`
   - `disabled`: `disabled || voice.isConnecting` — the caller is only responsible for the `isConnecting` guard; `MicButton` already applies `|| isProcessing` internally to the native disabled attribute

No changes to `MicButton.tsx`, `useVoice.ts`, backend, or any other file.

## Data Flow

```
User taps MicButton → startRecording()
  → Deepgram WS streams audio
User taps MicButton again → stopRecording()
  → Deepgram finalises transcript → voice.transcript set
useEffect fires → recordAnswer(transcript) → answer submitted
  → voice.reset() clears transcript
```

## Edge Cases

| Case | Behaviour |
|---|---|
| Deepgram returns empty transcript | `voice.transcript` stays null (set only when `accumulatedRef` is truthy); `useEffect` guard also checks `trim()` non-empty as a belt-and-suspenders safety |
| Sheet closes while recording | `useVoice` unmount cleanup stops mic + WS |
| Multi-select question with custom input | Combined answer is built directly in the `useEffect` from current `pendingSelections` + transcript (avoids React state timing bug from `setCustomValue` + `handleCustomSubmit` in the same sync block) |
| `disabled=true` (backend thinking) | Mic button disabled; recording cannot start |
| Token fetch in flight (`isConnecting`) | Mic button disabled via `voice.isConnecting`; prevents double-tap confusion |
| User taps stop before token fetch completes | `pendingStopRef` in `useVoice` handles this; aborts cleanly |

## No Backend Changes

The existing `/api/v1/voice/token` endpoint and Deepgram WebSocket plumbing are reused as-is.

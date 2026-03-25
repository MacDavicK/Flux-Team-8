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

**`GoalClarifierView.tsx`** — only file modified (~15 lines added):

1. Call `useVoice()` at the top of the component.
2. Add a `useEffect` watching `voice.transcript`:
   - When non-null: call `recordAnswer(voice.transcript.trim())` then `voice.reset()`.
3. Render `MicButton` next to the free-text submit button, only when the text input is visible (`allows_custom || options.length === 0`).
   - `onClick`: toggle `startRecording` / `stopRecording`
   - `isRecording`: `voice.isRecording`
   - `isProcessing`: `voice.isProcessing`
   - `disabled`: same `disabled` prop as the submit button, also disabled while `voice.isProcessing`

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
| Deepgram returns empty transcript | `voice.transcript` stays null; sheet stays open |
| Sheet closes while recording | `useVoice` unmount cleanup stops mic + WS |
| Multi-select question with custom input | Transcript passed to `recordAnswer()` which combines with any tapped options using existing logic |
| `disabled=true` (backend thinking) | Mic button disabled; recording cannot start |
| User taps stop before token fetch completes | `pendingStopRef` in `useVoice` handles this; aborts cleanly |

## No Backend Changes

The existing `/api/v1/voice/token` endpoint and Deepgram WebSocket plumbing are reused as-is.
